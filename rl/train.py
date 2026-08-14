"""
rl/train.py — PPO fine-tuning on top of the imitation-learned policy

Loads the weights from imitation_model.pth and transfers them into a PPO
policy network, then trains via self-play against a rotating pool of all
51 heuristic agents. This lets the RL agent go beyond what the heuristics
can do, while starting from a sensible policy instead of random noise.

Architecture match:
    FarmNet (imitation):    Linear(741,256) → Linear(256,256) → Linear(256,128) → Linear(128,35)
    SB3 MlpPolicy net_arch: [256, 256, 128] with separate pi/vf heads
    We copy FarmNet weights into SB3's policy layers before training starts.

Output:
    ppo_final.zip  — the trained PPO model, loadable by agent.py for submission

Run on Kaggle after imitation.py:
    python rl/train.py
"""

import os
import sys
import random
import importlib
import numpy as np
import torch
import torch.nn as nn

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback, EvalCallback
from stable_baselines3.common.vec_env import SubprocVecEnv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.env import KaggricultureEnv, OBS_SIZE, N_ACTIONS
from rl.imitation import FarmNet

# --- Config ---

WORKING_DIR   = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working")
MODEL_PATH    = os.path.join(WORKING_DIR, "imitation_model.pth")
OUTPUT_PATH   = os.path.join(WORKING_DIR, "ppo_final")
LOG_DIR       = os.path.join(WORKING_DIR, "logs")
CHECKPOINT_DIR = os.path.join(WORKING_DIR, "checkpoints")

TOTAL_STEPS   = 2_000_000   # increase to 5M+ on Kaggle GPU for best results
N_ENVS        = 4           # parallel environments
N_STEPS       = 720         # one full episode per rollout per env
BATCH_SIZE    = 360         # must divide N_STEPS * N_ENVS
N_EPOCHS      = 10
LR            = 3e-4
GAMMA         = 0.99
ENT_COEF      = 0.01        # entropy bonus — keeps exploration alive
HIDDEN        = 256


# --- Load all heuristic agents as opponent pool ---

def load_opponent_pool():
    """
    Dynamically import every agent_XX_*.py from agents/.
    Returns a list of callable agent functions.
    """
    agents_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents"
    )
    pool = []

    for fname in sorted(os.listdir(agents_dir)):
        if not fname.startswith("agent_") or not fname.endswith(".py"):
            continue
        if "test" in fname:
            continue

        module_name = fname[:-3]
        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(agents_dir, fname)
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            continue

        for attr in dir(mod):
            if attr.startswith("_"):
                continue
            obj = getattr(mod, attr)
            if callable(obj) and not isinstance(obj, type):
                pool.append(obj)
                break

    print(f"Opponent pool: {len(pool)} agents")
    return pool


OPPONENT_POOL = load_opponent_pool()


# --- Environment factory ---

def make_env(opponent_pool):
    """
    Returns a callable that creates one KaggricultureEnv with a randomly
    selected opponent from the pool each time reset() is called.
    This gives the agent diverse opponents = better generalisation.
    """
    class RandomOpponentEnv(KaggricultureEnv):
        def reset(self, seed=None, options=None):
            self.opponent_fn = random.choice(opponent_pool)
            return super().reset(seed=seed, options=options)

    def _init():
        return RandomOpponentEnv(opponent_fn=random.choice(opponent_pool))

    return _init


# --- Weight transfer: imitation → PPO policy ---

def transfer_imitation_weights(ppo_model, imitation_path):
    """
    Load FarmNet weights from imitation_model.pth and copy them into
    the corresponding layers of SB3's MlpPolicy.

    SB3 MlpPolicy layer mapping (with net_arch=[256, 256, 128]):
        mlp_extractor.policy_net[0]  ←  FarmNet net[0]   Linear(741, 256)
        mlp_extractor.policy_net[2]  ←  FarmNet net[2]   Linear(256, 256)
        mlp_extractor.policy_net[4]  ←  FarmNet net[4]   Linear(256, 128)
        action_net                   ←  FarmNet net[6]   Linear(128, 35)

    The value head (vf) is left randomly initialised — it has nothing to
    imitate from the heuristic data and will learn from PPO rewards.
    """
    if not os.path.exists(imitation_path):
        print(f"[warn] No imitation model found at {imitation_path}, starting from random weights")
        return

    checkpoint = torch.load(imitation_path, map_location="cpu")
    farm_net_state = checkpoint["model_state"]

    policy = ppo_model.policy

    # Map FarmNet layer indices to SB3 policy layers
    layer_map = [
        (farm_net_state["net.0.weight"], farm_net_state["net.0.bias"],
         policy.mlp_extractor.policy_net[0]),
        (farm_net_state["net.2.weight"], farm_net_state["net.2.bias"],
         policy.mlp_extractor.policy_net[2]),
        (farm_net_state["net.4.weight"], farm_net_state["net.4.bias"],
         policy.mlp_extractor.policy_net[4]),
        (farm_net_state["net.6.weight"], farm_net_state["net.6.bias"],
         policy.action_net),
    ]

    with torch.no_grad():
        for w, b, layer in layer_map:
            layer.weight.copy_(w)
            layer.bias.copy_(b)

    print(f"Transferred imitation weights from {imitation_path}")
    if "accuracy" in checkpoint:
        print(f"  Imitation accuracy was: {checkpoint['accuracy']:.1f}%")


# --- Main training ---

def train():
    print("=== PPO Fine-Tuning ===")
    print(f"Total steps: {TOTAL_STEPS:,} | Envs: {N_ENVS} | Device: {'cuda' if torch.cuda.is_available() else 'cpu'}")

    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # Build vectorised environment with random opponents
    env_fns = [make_env(OPPONENT_POOL) for _ in range(N_ENVS)]
    vec_env = SubprocVecEnv(env_fns)

    # PPO with matching network architecture to FarmNet
    # net_arch defines [shared layers for pi, shared layers for vf]
    model = PPO(
        policy="MlpPolicy",
        env=vec_env,
        verbose=1,
        n_steps=N_STEPS,
        batch_size=BATCH_SIZE,
        n_epochs=N_EPOCHS,
        learning_rate=LR,
        gamma=GAMMA,
        ent_coef=ENT_COEF,
        gae_lambda=0.95,
        clip_range=0.2,
        tensorboard_log=LOG_DIR,
        policy_kwargs=dict(
            net_arch=dict(pi=[HIDDEN, HIDDEN, 128], vf=[HIDDEN, HIDDEN, 128]),
            activation_fn=nn.ReLU,
        ),
    )

    # Transfer imitation weights before any RL training
    transfer_imitation_weights(model, MODEL_PATH)

    # Checkpoint every 200k steps so we don't lose progress
    checkpoint_cb = CheckpointCallback(
        save_freq=200_000 // N_ENVS,
        save_path=CHECKPOINT_DIR,
        name_prefix="ppo",
        verbose=1,
    )

    print("Starting PPO training...")
    model.learn(
        total_timesteps=TOTAL_STEPS,
        callback=checkpoint_cb,
        progress_bar=True,
        reset_num_timesteps=True,
    )

    model.save(OUTPUT_PATH)
    print(f"\nSaved final model to {OUTPUT_PATH}.zip")

    # Also save just the policy weights as a raw FarmNet state dict.
    # agent.py loads this format — no SB3 dependency needed at submission time.
    policy = model.policy
    farm_net_state = {
        "net.0.weight": policy.mlp_extractor.policy_net[0].weight.data,
        "net.0.bias":   policy.mlp_extractor.policy_net[0].bias.data,
        "net.2.weight": policy.mlp_extractor.policy_net[2].weight.data,
        "net.2.bias":   policy.mlp_extractor.policy_net[2].bias.data,
        "net.4.weight": policy.mlp_extractor.policy_net[4].weight.data,
        "net.4.bias":   policy.mlp_extractor.policy_net[4].bias.data,
        "net.6.weight": policy.action_net.weight.data,
        "net.6.bias":   policy.action_net.bias.data,
    }
    policy_path = os.path.join(WORKING_DIR, "ppo_policy.pth")
    torch.save(farm_net_state, policy_path)
    print(f"Saved submittable policy weights to {policy_path}")


if __name__ == "__main__":
    train()
