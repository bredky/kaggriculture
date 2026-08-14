"""
rl/imitation.py — Imitation learning from collected heuristic agent data

Loads the (obs, action, score) dataset produced by collect.py and trains
a small MLP to predict what a good agent would do given a farm state.

Key idea: each training example is weighted by the episode's final score,
so turns from $27k agents teach the network more than turns from $18k agents.

Output:
    imitation_model.pth  — saved network weights, loaded by train.py to
                           initialise the PPO policy instead of random weights

Run on Kaggle after collect.py has finished:
    python rl/imitation.py
"""

import os
import sys
import glob
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.env import OBS_SIZE, N_ACTIONS

# --- Config ---

DATA_DIR    = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working") + "/data"
OUTPUT_DIR  = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working")
MODEL_PATH  = os.path.join(OUTPUT_DIR, "imitation_model.pth")

EPOCHS      = 20
BATCH_SIZE  = 512
LR          = 1e-3
HIDDEN      = 256       # units per hidden layer
DEVICE      = "cuda" if torch.cuda.is_available() else "cpu"


# --- Network ---

class FarmNet(nn.Module):
    """
    Small MLP: 510 inputs → 3 hidden layers → 10 action logits.
    Shared architecture used by both imitation learning and PPO.
    """
    def __init__(self, obs_size=OBS_SIZE, n_actions=N_ACTIONS, hidden=HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_size, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 128),
            nn.ReLU(),
            nn.Linear(128, n_actions),
        )

    def forward(self, x):
        return self.net(x)  # returns raw logits (not softmaxed)


# --- Dataset ---

class ImitationDataset(Dataset):
    """
    Loads all checkpoint .npz files from DATA_DIR and concatenates them
    into a single in-memory dataset.

    Each item: (obs_tensor, action_int, weight)
    Weight = normalised final score so high-scoring episodes teach more.
    """

    def __init__(self, data_dir):
        files = sorted(glob.glob(os.path.join(data_dir, "checkpoint_*.npz")))
        if not files:
            raise FileNotFoundError(f"No checkpoint files found in {data_dir}")

        print(f"Loading {len(files)} checkpoint files from {data_dir}...")

        all_obs     = []
        all_actions = []
        all_scores  = []

        for path in files:
            data = np.load(path)
            all_obs.append(data["obs"].astype(np.float32))
            all_actions.append(data["actions"].astype(np.int64))
            all_scores.append(data["scores"].astype(np.float32))

        obs     = np.concatenate(all_obs,     axis=0)
        actions = np.concatenate(all_actions, axis=0)
        scores  = np.concatenate(all_scores,  axis=0)

        print(f"Total steps: {len(obs):,} | Actions shape: {actions.shape}")

        # Normalise scores to [0, 1] range so they work as loss weights.
        # Clip negatives to 0 so broken agents don't contribute negative weight.
        scores = np.clip(scores, 0, None)
        score_range = scores.max() - scores.min()
        if score_range > 0:
            weights = (scores - scores.min()) / score_range
        else:
            weights = np.ones_like(scores)
        # Add small floor so even lower-scoring episodes contribute a little
        weights = weights * 0.9 + 0.1

        self.obs     = torch.tensor(obs,     dtype=torch.float32)
        self.actions = torch.tensor(actions, dtype=torch.long)
        self.weights = torch.tensor(weights, dtype=torch.float32)

        # Print action distribution so we can spot imbalances
        unique, counts = np.unique(actions, return_counts=True)
        print("Action distribution:")
        action_names = [
            "PASS","NORTH","SOUTH","EAST","WEST","WATER","HARVEST","PLANT_WHEAT","PLANT_MELON","DIG",
            "PLANT_TOMATO","PLANT_CARROT","PLANT_STRAWBERRY","BUILD_COOP","BUILD_PASTURE",
            "PICKUP_ANIMAL","PICKUP_WHEAT","PLACE_ANIMAL","CARE","COLLECT_FERT",
            "HIRE","BUY_LAND","SELL_MELON","SELL_WHEAT","SELL_TOMATO","SELL_CARROT",
            "SELL_STRAWBERRY","SELL_FERT","BUY_GOOSE","BUY_COW","BUY_SHEEP",
            "BUY_SEED_WHEAT","BUY_SEED_TOMATO","BUY_SEED_CARROT","BUY_SEED_STRAW",
        ]
        for a, c in zip(unique, counts):
            name = action_names[a] if a < len(action_names) else str(a)
            print(f"  {name:<10} {c:>8,}  ({100*c/len(actions):.1f}%)")

    def __len__(self):
        return len(self.obs)

    def __getitem__(self, idx):
        return self.obs[idx], self.actions[idx], self.weights[idx]


# --- Training ---

def train():
    print(f"=== Imitation Learning ===")
    print(f"Device: {DEVICE} | Epochs: {EPOCHS} | Batch: {BATCH_SIZE} | LR: {LR}")

    dataset    = ImitationDataset(DATA_DIR)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2)

    model     = FarmNet().to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_acc = 0.0

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss    = 0.0
        total_correct = 0
        total_samples = 0

        for obs_batch, action_batch, weight_batch in dataloader:
            obs_batch    = obs_batch.to(DEVICE)
            action_batch = action_batch.to(DEVICE)
            weight_batch = weight_batch.to(DEVICE)

            logits = model(obs_batch)

            # Weighted cross-entropy: multiply per-sample loss by episode weight
            loss_per_sample = nn.functional.cross_entropy(
                logits, action_batch, reduction="none"
            )
            loss = (loss_per_sample * weight_batch).mean()

            optimizer.zero_grad()
            loss.backward()
            # Gradient clipping — keeps training stable
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            preds = logits.argmax(dim=1)
            total_correct += (preds == action_batch).sum().item()
            total_samples += len(action_batch)
            total_loss    += loss.item() * len(action_batch)

        scheduler.step()

        avg_loss = total_loss / total_samples
        accuracy = 100.0 * total_correct / total_samples

        print(f"Epoch {epoch:>2}/{EPOCHS}  loss={avg_loss:.4f}  acc={accuracy:.1f}%")

        # Save best model
        if accuracy > best_acc:
            best_acc = accuracy
            torch.save({
                "epoch":      epoch,
                "model_state": model.state_dict(),
                "obs_size":   OBS_SIZE,
                "n_actions":  N_ACTIONS,
                "hidden":     HIDDEN,
                "accuracy":   accuracy,
            }, MODEL_PATH)
            print(f"  ✓ Saved best model (acc={accuracy:.1f}%)")

    print(f"\nDone. Best accuracy: {best_acc:.1f}%")
    print(f"Model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    train()
