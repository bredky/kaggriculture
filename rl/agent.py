"""
rl/agent.py — Submittable RL agent

Loads the trained PPO policy and wraps it as a standard agent function.
35-action space covering all actions used by heuristic agents.

To submit:
  1. Upload ppo_policy.pth as a Kaggle dataset
  2. Update MODEL_PATH to /kaggle/input/<dataset>/ppo_policy.pth
  3. Copy this file to main.py (function is already named `agent`)
"""

import os
import sys
import numpy as np
import torch
import torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rl.env import encode_obs, N_ACTIONS, OBS_SIZE, ANIMALS

# --- Model path ---
WORKING_DIR = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working")
MODEL_PATH  = os.path.join(WORKING_DIR, "ppo_policy.pth")

HIDDEN = 256

class _FarmNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(OBS_SIZE, HIDDEN), nn.ReLU(),
            nn.Linear(HIDDEN, HIDDEN),   nn.ReLU(),
            nn.Linear(HIDDEN, 128),      nn.ReLU(),
            nn.Linear(128, N_ACTIONS),
        )
    def forward(self, x):
        return self.net(x)

# --- Load model once at import time ---
_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
    net = _FarmNet()
    if os.path.exists(MODEL_PATH):
        state = torch.load(MODEL_PATH, map_location="cpu")
        net.load_state_dict(state.get("policy_state", state))
        print(f"[rl_agent] Loaded model from {MODEL_PATH}")
    else:
        print(f"[rl_agent] WARNING: no model at {MODEL_PATH}, using random weights")
    net.eval()
    _model = net
    return _model


# --- Helpers ---

def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None

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

def _melon_seed_market(obs):
    """Auto-restock melon seeds (same as env.py heuristic)."""
    player = obs["player"]
    farm   = obs["farms"][player]
    seeds  = obs["private"]["seeds"]
    tiles  = farm["tiles"]
    all_tiles = [(x, y, t) for y, row in enumerate(tiles) for x, t in enumerate(row)]
    melon_ct  = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
    unlocked  = set(farm.get("unlocked_quadrants", []))
    melon_target = 18 if "SW" in unlocked else (14 if "NE" in unlocked else 8)
    actions = []
    need = melon_target - melon_ct - seeds.get("MELON", 0)
    if need > 0:
        actions.append(["BUY_SEED", "MELON", need])
    return actions


# --- Agent function ---

def agent(obs):
    try:
        model  = _load_model()
        player = obs["player"]
        farm   = obs["farms"][player]
        seeds  = obs["private"]["seeds"]
        shed   = obs["private"]["shed"]
        inventories = obs.get("private", {}).get("inventories", [{}])
        inventory   = inventories[0] if inventories else {}
        day    = obs["day"]

        obs_vec = encode_obs(obs)
        with torch.no_grad():
            logits     = model(torch.tensor(obs_vec, dtype=torch.float32).unsqueeze(0))
            action_int = logits.argmax(dim=1).item()

        market = _melon_seed_market(obs)

        # Farmer actions 0-19
        if action_int <= 9:
            farmer_action = [["PASS"],["NORTH"],["SOUTH"],["EAST"],["WEST"],
                             ["WATER"],["HARVEST"],["PLANT","WHEAT"],["PLANT","MELON"],["DIG"]][action_int]
        elif action_int == 10: farmer_action = ["PLANT", "TOMATO"]
        elif action_int == 11: farmer_action = ["PLANT", "CARROT"]
        elif action_int == 12: farmer_action = ["PLANT", "STRAWBERRY"]
        elif action_int == 13: farmer_action = ["BUILD_COOP"]
        elif action_int == 14: farmer_action = ["BUILD_PASTURE"]
        elif action_int == 15:
            farmer_action = ["PASS"]
            for animal in ANIMALS:
                if shed.get(animal, 0) > 0:
                    farmer_action = ["PICKUP", animal, 1]; break
        elif action_int == 16:
            w = shed.get("WHEAT", 0)
            farmer_action = ["PICKUP", "WHEAT", min(2, w)] if w > 0 else ["PASS"]
        elif action_int == 17:
            farmer_action = ["PASS"]
            for animal in ANIMALS:
                if inventory.get(animal, 0) > 0:
                    farmer_action = ["PLACE", animal]; break
        elif action_int == 18: farmer_action = ["CARE"]
        elif action_int == 19: farmer_action = ["COLLECT_FERTILIZER"]

        # Market actions 20-34
        elif action_int == 20: farmer_action = ["PASS"]; market.append(["HIRE"])
        elif action_int == 21: farmer_action = ["PASS"]; market.append(["BUY_LAND"])
        elif action_int == 22:
            farmer_action = ["PASS"]
            if shed.get("MELON", 0) > 0: market.append(["SELL", "MELON", shed["MELON"]])
        elif action_int == 23:
            farmer_action = ["PASS"]
            if shed.get("WHEAT", 0) > 0: market.append(["SELL", "WHEAT", shed["WHEAT"]])
        elif action_int == 24:
            farmer_action = ["PASS"]
            if shed.get("TOMATO", 0) > 0: market.append(["SELL", "TOMATO", shed["TOMATO"]])
        elif action_int == 25:
            farmer_action = ["PASS"]
            if shed.get("CARROT", 0) > 0: market.append(["SELL", "CARROT", shed["CARROT"]])
        elif action_int == 26:
            farmer_action = ["PASS"]
            if shed.get("STRAWBERRY", 0) > 0: market.append(["SELL", "STRAWBERRY", shed["STRAWBERRY"]])
        elif action_int == 27:
            farmer_action = ["PASS"]
            if shed.get("FERTILIZER", 0) > 0: market.append(["SELL", "FERTILIZER", shed["FERTILIZER"]])
        elif action_int == 28: farmer_action = ["PASS"]; market.append(["BUY_ANIMAL", "GOOSE", 1])
        elif action_int == 29: farmer_action = ["PASS"]; market.append(["BUY_ANIMAL", "COW", 1])
        elif action_int == 30: farmer_action = ["PASS"]; market.append(["BUY_ANIMAL", "SHEEP", 1])
        elif action_int == 31: farmer_action = ["PASS"]; market.append(["BUY_SEED", "WHEAT", 5])
        elif action_int == 32: farmer_action = ["PASS"]; market.append(["BUY_SEED", "TOMATO", 5])
        elif action_int == 33: farmer_action = ["PASS"]; market.append(["BUY_SEED", "CARROT", 5])
        elif action_int == 34: farmer_action = ["PASS"]; market.append(["BUY_SEED", "STRAWBERRY", 5])
        else: farmer_action = ["PASS"]

        return {
            "farmer": farmer_action,
            "hands":  [_hand_action(hx, hy, farm["tiles"], seeds, day)
                       for hx, hy in farm.get("hands", [])],
            "market": market,
        }

    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
