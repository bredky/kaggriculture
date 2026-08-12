"""
rl/env.py — Gymnasium wrapper for Kaggriculture

The RL agent controls the FARMER only (10 discrete actions).
Market buying/selling and hired hands are handled by rule-based logic
(same strategy as the top heuristic agents) to keep the action space small.

Observation: ~510 floats encoding the full game state
Action:       Discrete(10) — farmer movement + field actions
Reward:       Money gained per turn (dense), normalized by /1000
Opponent:     Any callable agent function (defaults to PASS)
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from kaggle_environments import make

# --- Constants ---

CROPS = ["WHEAT", "MELON", "STRAWBERRY", "TOMATO", "CARROT"]
CROP_TO_ID = {c: i + 1 for i, c in enumerate(CROPS)}  # 0 = empty

# 10 discrete farmer actions the RL agent can choose from
FARMER_ACTIONS = [
    ["PASS"],
    ["NORTH"],
    ["SOUTH"],
    ["EAST"],
    ["WEST"],
    ["WATER"],
    ["HARVEST"],
    ["PLANT", "WHEAT"],
    ["PLANT", "MELON"],
    ["DIG"],
]
N_ACTIONS = len(FARMER_ACTIONS)

# Observation vector size: 100 tiles × 5 features + 10 scalar features
TILE_FEATURES = 5
N_TILES = 100
SCALAR_FEATURES = 10  # farmer xy, seeds×2, shed×2, money, day, prices×2
OBS_SIZE = N_TILES * TILE_FEATURES + SCALAR_FEATURES  # = 510


# --- Observation encoder ---

def encode_obs(obs):
    """Flatten the kaggle obs dict into a fixed-size float32 vector."""
    player = obs["player"]
    farm = obs["farms"][player]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    day = obs["day"]
    prices = obs["market"]["prices"]

    vec = np.zeros(OBS_SIZE, dtype=np.float32)
    idx = 0

    # Grid: 100 tiles, each encoded as 5 floats
    # [crop_id/5, yield/20, watered, age/30, is_empty]
    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                vec[idx + 4] = 1.0  # is_empty = 1
            elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop_id = CROP_TO_ID.get(tile.get("crop", ""), 0)
                planted_day = tile.get("planted_day", day)
                vec[idx]     = crop_id / 5.0
                vec[idx + 1] = min(tile.get("yield_units", 0) / 20.0, 1.0)
                vec[idx + 2] = float(tile.get("watered_today", False))
                vec[idx + 3] = min((day - planted_day) / 30.0, 1.0)
            # structures/locked tiles: all zeros (not empty, not plant)
            idx += TILE_FEATURES

    # Scalar features
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


# --- Rule-based helpers (market + hands) ---

def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None


def heuristic_market(obs):
    """
    Rule-based market actions for the RL agent's turn.
    Keeps seeds stocked, sells wheat immediately, sells melon when price is good.
    """
    player = obs["player"]
    farm = obs["farms"][player]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    day = obs["day"]
    prices = obs["market"]["prices"]

    tiles = farm["tiles"]
    all_tiles = [(x, y, t) for y, row in enumerate(tiles) for x, t in enumerate(row)]
    melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
    wheat_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

    actions = []

    # Restock seeds
    if seeds.get("MELON", 0) + melon_count < 8:
        need = 8 - melon_count - seeds.get("MELON", 0)
        if need > 0:
            actions.append(["BUY_SEED", "MELON", need])
    if seeds.get("WHEAT", 0) + wheat_count < 4:
        need = 4 - wheat_count - seeds.get("WHEAT", 0)
        if need > 0:
            actions.append(["BUY_SEED", "WHEAT", need])

    # Sell
    if shed.get("WHEAT", 0) > 0:
        actions.append(["SELL", "WHEAT", shed["WHEAT"]])
    melon_shed = shed.get("MELON", 0)
    if melon_shed > 0:
        if day >= 27:
            actions.append(["SELL", "MELON", melon_shed])
        elif prices.get("MELON", 150) >= 120:
            actions.append(["SELL", "MELON", min(4, melon_shed)])

    return actions


def hand_action(hx, hy, tiles_2d, seeds, day):
    """Rule-based action for a hired hand: water > harvest > plant."""
    all_t = [(x, y, t) for y, row in enumerate(tiles_2d) for x, t in enumerate(row)]
    water = [(x, y, t) for x, y, t in all_t
             if isinstance(t, dict) and t.get("kind") == "PLANT"
             and not t.get("watered_today", False)]
    harvest = [(x, y, t) for x, y, t in all_t
               if isinstance(t, dict) and t.get("kind") == "PLANT"
               and t.get("yield_units", 0) > 0
               and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    empty = [(x, y) for x, y, t in all_t if t is None]

    if water:
        tx, ty, _ = min(water, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if harvest:
        tx, ty, _ = min(harvest, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
        if tx == hx and ty == hy: return ["HARVEST"]
        return [_step_toward(hx, hy, tx, ty)]
    for crop in ["MELON", "WHEAT"]:
        if seeds.get(crop, 0) > 0 and empty:
            tx, ty = min(empty, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
            if tx == hx and ty == hy: return ["PLANT", crop]
            return [_step_toward(hx, hy, tx, ty)]
    return ["PASS"]


# --- Gymnasium environment ---

class KaggricultureEnv(gym.Env):
    """
    Wraps the kaggle Kaggriculture game as a standard Gymnasium environment.

    Player 0 = RL agent (farmer action chosen by policy)
    Player 1 = heuristic opponent (any callable, or PASS if None)

    Each call to step() advances the game by one turn (1/24 of a day).
    An episode is 720 turns (30 days × 24 turns/day).
    """

    metadata = {"render_modes": []}

    def __init__(self, opponent_fn=None):
        super().__init__()
        self.opponent_fn = opponent_fn
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(OBS_SIZE,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(N_ACTIONS)
        self._env = None
        self._prev_money = 3000

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self._env = make("kaggriculture", configuration={"episodeSteps": 720})
        self._env.reset()
        self._prev_money = 3000
        obs = self._env.state[0].observation
        return encode_obs(obs), {}

    def step(self, action_int):
        obs0 = self._env.state[0].observation
        obs1 = self._env.state[1].observation

        # Build player 0 action: RL farmer + rule-based market + rule-based hands
        player = obs0["player"]
        farm = obs0["farms"][player]
        seeds = obs0["private"]["seeds"]
        day = obs0["day"]

        action0 = {
            "farmer": FARMER_ACTIONS[action_int],
            "hands": [hand_action(hx, hy, farm["tiles"], seeds, day)
                      for hx, hy in farm.get("hands", [])],
            "market": heuristic_market(obs0),
        }

        # Build player 1 action from heuristic opponent
        if self.opponent_fn is not None:
            try:
                action1 = self.opponent_fn(obs1)
            except Exception:
                action1 = {"farmer": ["PASS"], "hands": [], "market": []}
        else:
            action1 = {"farmer": ["PASS"], "hands": [], "market": []}

        self._env.step([action0, action1])

        state0 = self._env.state[0]
        done = state0.status in ("DONE", "ERROR", "TIMEOUT", "INVALID")

        new_obs = state0.observation
        new_money = new_obs["farms"][new_obs["player"]].get("money", self._prev_money)

        # Dense reward: money gained this step, normalized
        reward = (new_money - self._prev_money) / 1000.0
        self._prev_money = new_money

        return encode_obs(new_obs), reward, done, False, {}
