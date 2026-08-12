"""
rl/collect.py — Training data collection for imitation learning

Runs all 50 heuristic agents vs all 50 agents × 5 seeds = 12,500 games.
For each game, records (observation, farmer_action_int) for every turn.
Only saves data from episodes where the agent scored above SCORE_THRESHOLD
— we only want to imitate good play.

Output (saved to OUTPUT_DIR):
    obs.npy        float16 array of shape (N, 510) — encoded observations
    actions.npy    int8 array of shape (N,)        — farmer action indices
    scores.npy     float32 array of shape (N,)     — final score for that episode step

Run on Kaggle: output goes to /kaggle/working/data/
"""

import os
import sys
import importlib
import numpy as np
from kaggle_environments import make

# Add parent dir so we can import agents and rl.env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.env import encode_obs, FARMER_ACTIONS

# --- Config ---

# Only keep episodes from agents scoring above this (filters out bad strategies)
SCORE_THRESHOLD = 18_000

# Games per agent pair
N_SEEDS = 5

# Where to save data (works locally and on Kaggle)
OUTPUT_DIR = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working") + "/data"

# Save a checkpoint to disk every this many episodes (avoids OOM on large runs)
CHECKPOINT_EVERY = 500

# --- Action mapping ---

# Map a heuristic farmer action list back to our discrete action index.
# Actions not in our space (e.g. PLANT STRAWBERRY) map to PASS (0).
_ACTION_TO_INT = {tuple(a): i for i, a in enumerate(FARMER_ACTIONS)}

def farmer_action_to_int(farmer_action):
    return _ACTION_TO_INT.get(tuple(farmer_action), 0)


# --- Agent loader ---

def load_agents():
    """
    Dynamically import all agent_XX_*.py files from the agents/ directory.
    Returns list of (name, callable) tuples.
    """
    agents_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
    agents = []

    for fname in sorted(os.listdir(agents_dir)):
        if not fname.startswith("agent_") or not fname.endswith(".py"):
            continue
        # Skip test agent — it's our benchmark, not a training agent
        if "test" in fname:
            continue

        module_name = fname[:-3]  # strip .py
        spec = importlib.util.spec_from_file_location(
            module_name, os.path.join(agents_dir, fname)
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"  [skip] {fname}: {e}")
            continue

        # Find the agent function — it's the one public function that isn't a helper
        fn = None
        for attr in dir(mod):
            if attr.startswith("_"):
                continue
            obj = getattr(mod, attr)
            if callable(obj) and not isinstance(obj, type):
                fn = obj
                break

        if fn is not None:
            agents.append((module_name, mod, fn))
        else:
            print(f"  [skip] {fname}: no callable found")

    print(f"Loaded {len(agents)} agents")
    return agents


def reset_agent_state(mod):
    """Clear the module-level _state dict so each game starts fresh."""
    if hasattr(mod, "_state"):
        mod._state.clear()


# --- Data collection ---

def run_game(fn0, mod0, fn1, mod1, seed):
    """
    Play one full game between fn0 (player 0) and fn1 (player 1).
    Returns:
        ep_obs0:     list of encoded obs arrays for player 0
        ep_actions0: list of farmer action ints for player 0
        ep_obs1:     list of encoded obs arrays for player 1
        ep_actions1: list of farmer action ints for player 1
        score0:      final money for player 0
        score1:      final money for player 1
    """
    reset_agent_state(mod0)
    reset_agent_state(mod1)

    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720},
        debug=False,
    )
    env.reset()

    ep_obs0, ep_actions0 = [], []
    ep_obs1, ep_actions1 = [], []
    last_money0, last_money1 = 3000, 3000

    while True:
        state0 = env.state[0]
        state1 = env.state[1]

        if state0.status not in ("ACTIVE",):
            break

        obs0 = state0.observation
        obs1 = state1.observation

        # Track money each turn — final state observation can be None on Kaggle
        try:
            last_money0 = obs0["farms"][obs0["player"]].get("money", last_money0)
        except Exception:
            pass
        try:
            last_money1 = obs1["farms"][obs1["player"]].get("money", last_money1)
        except Exception:
            pass

        # Get actions from both agents
        try:
            a0 = fn0(obs0)
        except Exception:
            a0 = {"farmer": ["PASS"], "hands": [], "market": []}
        try:
            a1 = fn1(obs1)
        except Exception:
            a1 = {"farmer": ["PASS"], "hands": [], "market": []}

        # Record before stepping
        ep_obs0.append(encode_obs(obs0).astype(np.float16))
        ep_actions0.append(farmer_action_to_int(a0.get("farmer", ["PASS"])))
        ep_obs1.append(encode_obs(obs1).astype(np.float16))
        ep_actions1.append(farmer_action_to_int(a1.get("farmer", ["PASS"])))

        env.step([a0, a1])

    return ep_obs0, ep_actions0, ep_obs1, ep_actions1, last_money0, last_money1


def save_checkpoint(all_obs, all_actions, all_scores, checkpoint_idx):
    """Save accumulated data to disk and clear buffers."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, f"checkpoint_{checkpoint_idx:04d}.npz")
    np.savez_compressed(
        path,
        obs=np.array(all_obs, dtype=np.float16),
        actions=np.array(all_actions, dtype=np.int8),
        scores=np.array(all_scores, dtype=np.float32),
    )
    n_steps = len(all_obs)
    print(f"  Saved checkpoint {checkpoint_idx}: {n_steps:,} steps → {path}")
    return [], [], []  # return cleared buffers


def collect():
    import time
    print("=== Kaggriculture Data Collection ===")
    print(f"Threshold: ${SCORE_THRESHOLD:,} | Seeds: {N_SEEDS} | Output: {OUTPUT_DIR}")

    agents = load_agents()
    n = len(agents)
    total_games = n * n * N_SEEDS
    print(f"Total games: {n} × {n} × {N_SEEDS} = {total_games:,}\n")

    all_obs, all_actions, all_scores = [], [], []
    checkpoint_idx = 0
    games_done = 0
    episodes_kept = 0
    start_time = time.time()

    for i, (name0, mod0, fn0) in enumerate(agents):
        for j, (name1, mod1, fn1) in enumerate(agents):
            for seed in range(N_SEEDS):
                games_done += 1
                t0 = time.time()

                try:
                    obs0, act0, obs1, act1, score0, score1 = run_game(
                        fn0, mod0, fn1, mod1, seed
                    )
                except Exception as e:
                    print(f"  [ERROR] {name0} vs {name1} seed={seed}: {e}")
                    continue

                kept = []
                if score0 >= SCORE_THRESHOLD:
                    all_obs.extend(obs0)
                    all_actions.extend(act0)
                    all_scores.extend([score0] * len(obs0))
                    episodes_kept += 1
                    kept.append(f"P0 ${score0:.0f}")

                if score1 >= SCORE_THRESHOLD:
                    all_obs.extend(obs1)
                    all_actions.extend(act1)
                    all_scores.extend([score1] * len(obs1))
                    episodes_kept += 1
                    kept.append(f"P1 ${score1:.0f}")

                elapsed = time.time() - t0
                pct = 100 * games_done / total_games
                total_elapsed = time.time() - start_time
                eta = (total_elapsed / games_done) * (total_games - games_done)
                eta_str = f"{int(eta//60)}m{int(eta%60):02d}s"
                kept_str = f"  ✓ kept {', '.join(kept)}" if kept else ""

                short0 = name0.replace("agent_", "")
                short1 = name1.replace("agent_", "")
                print(f"[{pct:5.1f}% | {games_done:>5}/{total_games} | ETA {eta_str}] "
                      f"{short0} vs {short1} s{seed} → "
                      f"${score0:.0f} / ${score1:.0f} ({elapsed:.1f}s){kept_str}")

                # Checkpoint to disk periodically
                if len(all_obs) >= CHECKPOINT_EVERY * 720:
                    all_obs, all_actions, all_scores = save_checkpoint(
                        all_obs, all_actions, all_scores, checkpoint_idx
                    )
                    checkpoint_idx += 1

        # Summary after each agent finishes all matchups
        total_elapsed = time.time() - start_time
        print(f"\n── Agent {i+1}/{n} ({name0}) done | "
              f"{episodes_kept} episodes kept | "
              f"buffer {len(all_obs):,} steps | "
              f"{int(total_elapsed//60)}m elapsed ──\n")

    # Save remaining data
    if all_obs:
        save_checkpoint(all_obs, all_actions, all_scores, checkpoint_idx)

    total_elapsed = time.time() - start_time
    print(f"\nDone in {int(total_elapsed//60)}m{int(total_elapsed%60):02d}s.")
    print(f"{games_done:,} games | {episodes_kept} episodes kept | checkpoints in {OUTPUT_DIR}")


if __name__ == "__main__":
    collect()
