"""
rl/agent.py — Submittable RL agent

Loads the trained PPO policy network and wraps it in the same function
signature as the heuristic agents: takes an obs dict, returns an action dict.

Two modes:
  1. Local benchmarking — import rl_agent from this file, add to tournament
  2. Kaggle submission  — copy this file to agents/ and upload model weights
                          as a Kaggle dataset, update MODEL_PATH accordingly

The policy network is loaded as raw PyTorch (not SB3) so it works in any
environment without needing stable-baselines3 installed.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Model path ---
# Local: looks in /kaggle/working/ by default
# Kaggle submission: update this to /kaggle/input/<your-dataset-name>/ppo_policy.pth
WORKING_DIR = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working")
MODEL_PATH  = os.path.join(WORKING_DIR, "ppo_policy.pth")


# --- Inline network definition ---
# Copied here so agent.py is self-contained for Kaggle submission.
# Must match the architecture in imitation.py / train.py exactly.

import torch
import torch.nn as nn

OBS_SIZE  = 510
N_ACTIONS = 10
HIDDEN    = 256

class _FarmNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(OBS_SIZE, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN),  nn.ReLU(),
            nn.Linear(HIDDEN, 128),     nn.ReLU(),
            nn.Linear(128, N_ACTIONS),
        )
    def forward(self, x):
        return self.net(x)


FARMER_ACTIONS = [
    ["PASS"],
    ["NORTH"], ["SOUTH"], ["EAST"], ["WEST"],
    ["WATER"],
    ["HARVEST"],
    ["PLANT", "WHEAT"],
    ["PLANT", "MELON"],
    ["DIG"],
]

# --- Load model once at import time ---

_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model

    net = _FarmNet()
    if os.path.exists(MODEL_PATH):
        state = torch.load(MODEL_PATH, map_location="cpu")
        # Handle both raw state_dict and checkpoint dict from train.py
        if "policy_state" in state:
            net.load_state_dict(state["policy_state"])
        else:
            net.load_state_dict(state)
        print(f"[rl_agent] Loaded model from {MODEL_PATH}")
    else:
        print(f"[rl_agent] WARNING: no model at {MODEL_PATH}, using random weights")

    net.eval()
    _model = net
    return _model


# --- Rule-based helpers (same as env.py, inlined for self-containment) ---

def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None


def _heuristic_market(obs):
    player = obs["player"]
    farm   = obs["farms"][player]
    seeds  = obs["private"]["seeds"]
    shed   = obs["private"]["shed"]
    day    = obs["day"]
    prices = obs["market"]["prices"]

    tiles     = farm["tiles"]
    all_tiles = [(x, y, t) for y, row in enumerate(tiles) for x, t in enumerate(row)]
    melon_ct  = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
    wheat_ct  = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

    actions = []
    if seeds.get("MELON", 0) + melon_ct < 8:
        need = 8 - melon_ct - seeds.get("MELON", 0)
        if need > 0: actions.append(["BUY_SEED", "MELON", need])
    if seeds.get("WHEAT", 0) + wheat_ct < 4:
        need = 4 - wheat_ct - seeds.get("WHEAT", 0)
        if need > 0: actions.append(["BUY_SEED", "WHEAT", need])
    if shed.get("WHEAT", 0) > 0:
        actions.append(["SELL", "WHEAT", shed["WHEAT"]])
    melon_shed = shed.get("MELON", 0)
    if melon_shed > 0:
        if day >= 27:
            actions.append(["SELL", "MELON", melon_shed])
        elif prices.get("MELON", 150) >= 120:
            actions.append(["SELL", "MELON", min(4, melon_shed)])
    return actions


def _hand_action(hx, hy, tiles_2d, seeds, day):
    all_t   = [(x, y, t) for y, row in enumerate(tiles_2d) for x, t in enumerate(row)]
    water   = [(x, y, t) for x, y, t in all_t
               if isinstance(t, dict) and t.get("kind") == "PLANT"
               and not t.get("watered_today", False)]
    harvest = [(x, y, t) for x, y, t in all_t
               if isinstance(t, dict) and t.get("kind") == "PLANT"
               and t.get("yield_units", 0) > 0
               and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    empty   = [(x, y) for x, y, t in all_t if t is None]

    if water:
        tx, ty, _ = min(water, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if harvest:
        tx, ty, _ = min(harvest, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["HARVEST"]
        return [_step_toward(hx, hy, tx, ty)]
    for crop in ["MELON", "WHEAT"]:
        if seeds.get(crop, 0) > 0 and empty:
            tx, ty = min(empty, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
            if tx == hx and ty == hy: return ["PLANT", crop]
            return [_step_toward(hx, hy, tx, ty)]
    return ["PASS"]


# --- Observation encoder (same as env.py, inlined) ---

CROPS = ["WHEAT", "MELON", "STRAWBERRY", "TOMATO", "CARROT"]
CROP_TO_ID = {c: i+1 for i, c in enumerate(CROPS)}

def _encode_obs(obs):
    player = obs["player"]
    farm   = obs["farms"][player]
    seeds  = obs["private"]["seeds"]
    shed   = obs["private"]["shed"]
    day    = obs["day"]
    prices = obs["market"]["prices"]

    vec = np.zeros(OBS_SIZE, dtype=np.float32)
    idx = 0
    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                vec[idx + 4] = 1.0
            elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop_id = CROP_TO_ID.get(tile.get("crop", ""), 0)
                planted_day = tile.get("planted_day", day)
                vec[idx]     = crop_id / 5.0
                vec[idx + 1] = min(tile.get("yield_units", 0) / 20.0, 1.0)
                vec[idx + 2] = float(tile.get("watered_today", False))
                vec[idx + 3] = min((day - planted_day) / 30.0, 1.0)
            idx += 5

    fx, fy = farm["farmer"]
    vec[idx]     = fx / 9.0
    vec[idx + 1] = fy / 9.0
    vec[idx + 2] = min(seeds.get("WHEAT", 0) / 20.0, 1.0)
    vec[idx + 3] = min(seeds.get("MELON", 0) / 20.0, 1.0)
    vec[idx + 4] = min(shed.get("WHEAT", 0) / 20.0, 1.0)
    vec[idx + 5] = min(shed.get("MELON", 0) / 20.0, 1.0)
    vec[idx + 6] = min(farm.get("money", 3000) / 50000.0, 1.0)
    vec[idx + 7] = day / 30.0
    vec[idx + 8] = min(prices.get("WHEAT", 50) / 200.0, 1.0)
    vec[idx + 9] = min(prices.get("MELON", 150) / 400.0, 1.0)
    return vec


# --- Agent function ---

def rl_agent(obs):
    """
    The submittable agent function.
    Signature matches all heuristic agents: takes obs dict, returns action dict.
    """
    try:
        model  = _load_model()
        player = obs["player"]
        farm   = obs["farms"][player]
        seeds  = obs["private"]["seeds"]
        day    = obs["day"]

        # Encode observation and run through policy network
        obs_vec = _encode_obs(obs)
        with torch.no_grad():
            obs_tensor = torch.tensor(obs_vec, dtype=torch.float32).unsqueeze(0)
            logits     = model(obs_tensor)
            action_int = logits.argmax(dim=1).item()

        farmer_action = FARMER_ACTIONS[action_int]
        hand_actions  = [_hand_action(hx, hy, farm["tiles"], seeds, day)
                         for hx, hy in farm.get("hands", [])]
        market_actions = _heuristic_market(obs)

        return {
            "farmer": farmer_action,
            "hands":  hand_actions,
            "market": market_actions,
        }

    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
