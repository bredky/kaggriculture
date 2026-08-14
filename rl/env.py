"""
rl/env.py — Gymnasium wrapper for Kaggriculture

The RL agent controls FARMER + MARKET decisions (35 discrete actions).
Actions 0-19:  farmer field/structure ops (farmer acts, melon seeds auto-bought)
Actions 20-34: market decisions (farmer PASSes, specific market order issued)

Observation: 741 floats encoding the full game state
  - 100 tiles × 7 features (crop/animal, yield, watered/structure, age, tile_type, stress, care)
  - 41 scalar features
Action:       Discrete(35)
Reward:       Money gained per turn (dense), normalized by /1000
Opponent:     Any callable agent function
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from kaggle_environments import make

# --- Constants ---

CROPS = ["WHEAT", "MELON", "STRAWBERRY", "TOMATO", "CARROT"]
CROP_TO_ID = {c: i + 1 for i, c in enumerate(CROPS)}  # 0 = none

ANIMALS = ["GOOSE", "COW", "SHEEP"]
ANIMAL_TO_ID = {a: i + 1 for i, a in enumerate(ANIMALS)}  # 0 = none

# 32 discrete actions:
# 0-19  = farmer actions (farmer acts, seeds auto-bought in market)
# 20-31 = market decisions (farmer PASSes)
FARMER_ACTIONS = [
    ["PASS"],                # 0
    ["NORTH"],               # 1
    ["SOUTH"],               # 2
    ["EAST"],                # 3
    ["WEST"],                # 4
    ["WATER"],               # 5
    ["HARVEST"],             # 6
    ["PLANT", "WHEAT"],      # 7
    ["PLANT", "MELON"],      # 8
    ["DIG"],                 # 9
    ["PLANT", "TOMATO"],     # 10
    ["PLANT", "CARROT"],     # 11
    ["PLANT", "STRAWBERRY"], # 12
    ["BUILD_COOP"],          # 13
    ["BUILD_PASTURE"],       # 14
    ["PICKUP_ANIMAL"],       # 15 — resolved at step(): PICKUP <animal> 1
    ["PICKUP_WHEAT"],        # 16 — resolved at step(): PICKUP WHEAT <n>
    ["PLACE_ANIMAL"],        # 17 — resolved at step(): PLACE <animal>
    ["CARE"],                # 18
    ["COLLECT_FERTILIZER"],  # 19
    # Market actions (farmer PASSes):
    ["HIRE"],                # 20
    ["BUY_LAND"],            # 21
    ["SELL", "MELON"],       # 22
    ["SELL", "WHEAT"],       # 23
    ["SELL", "TOMATO"],      # 24
    ["SELL", "CARROT"],      # 25
    ["SELL", "STRAWBERRY"],  # 26
    ["SELL", "FERTILIZER"],  # 27
    ["BUY_ANIMAL", "GOOSE"], # 28
    ["BUY_ANIMAL", "COW"],   # 29
    ["BUY_ANIMAL", "SHEEP"], # 30
    ["BUY_SEED", "WHEAT"],       # 31
    ["BUY_SEED", "TOMATO"],      # 32
    ["BUY_SEED", "CARROT"],      # 33
    ["BUY_SEED", "STRAWBERRY"],  # 34
]
N_ACTIONS = len(FARMER_ACTIONS)  # 35

# Observation vector size:
# 100 tiles × 7 features + 41 scalar features = 741
#
# Tile features per tile:
#   [0] crop_id/5 or animal_id/3
#   [1] yield_units/20
#   [2] watered_today (plant) | 0.5=COOP / 1.0=PASTURE (structure)
#   [3] age/30
#   [4] tile_type: 0=planted, 0.33=empty, 0.67=COOP/PASTURE
#   [5] consecutive_unwatered/5 (plant) | consecutive_unfed/5 (animal)
#   [6] 0 (plant) | care state: 0.33=fed only, 0.67=cared only, 1.0=both (animal)
TILE_FEATURES = 7
N_TILES = 100
SCALAR_FEATURES = 41
OBS_SIZE = N_TILES * TILE_FEATURES + SCALAR_FEATURES  # = 741


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

    # Grid: 100 tiles, each encoded as 7 floats
    coop_count = 0
    pasture_count = 0
    total_animals = 0

    for row in farm["tiles"]:
        for tile in row:
            if tile is None:
                vec[idx + 4] = 0.33  # empty
            elif isinstance(tile, dict):
                kind = tile.get("kind", "")
                if kind == "PLANT":
                    crop_id = CROP_TO_ID.get(tile.get("crop", ""), 0)
                    planted_day = tile.get("planted_day", day)
                    vec[idx]     = crop_id / 5.0
                    vec[idx + 1] = min(tile.get("yield_units", 0) / 20.0, 1.0)
                    vec[idx + 2] = float(tile.get("watered_today", False))
                    vec[idx + 3] = min((day - planted_day) / 30.0, 1.0)
                    # vec[idx+4] = 0 (planted)
                    vec[idx + 5] = min(tile.get("consecutive_unwatered", 0) / 5.0, 1.0)
                    # vec[idx+6] = 0 (not an animal)
                elif kind == "COOP":
                    coop_count += 1
                    animal = tile.get("animal", "")
                    if animal:
                        total_animals += 1
                    vec[idx]     = ANIMAL_TO_ID.get(animal, 0) / 3.0
                    vec[idx + 1] = min(tile.get("yield_units", 0) / 20.0, 1.0)
                    vec[idx + 2] = 0.5   # COOP flag
                    vec[idx + 4] = 0.67  # structure
                    vec[idx + 5] = min(tile.get("consecutive_unfed", 0) / 5.0, 1.0)
                    fed   = float(tile.get("fed_today", False))
                    cared = float(tile.get("cared_today", False))
                    vec[idx + 6] = 0.33 * fed + 0.67 * cared  # 0, 0.33, 0.67, or 1.0
                elif kind == "PASTURE":
                    pasture_count += 1
                    animal = tile.get("animal", "")
                    if animal:
                        total_animals += 1
                    vec[idx]     = ANIMAL_TO_ID.get(animal, 0) / 3.0
                    vec[idx + 1] = min(tile.get("yield_units", 0) / 20.0, 1.0)
                    vec[idx + 2] = 1.0   # PASTURE flag
                    vec[idx + 4] = 0.67  # structure
                    vec[idx + 5] = min(tile.get("consecutive_unfed", 0) / 5.0, 1.0)
                    fed   = float(tile.get("fed_today", False))
                    cared = float(tile.get("cared_today", False))
                    vec[idx + 6] = 0.33 * fed + 0.67 * cared
                # locked/weed/other: all zeros
            idx += TILE_FEATURES

    # Scalar features (41 total)
    fx, fy = farm["farmer"]
    unlocked_count = len(farm.get("unlocked_quadrants", []))
    hires_today = farm.get("hires_today", 0)
    active_hands = len(farm.get("hands", []))
    hour = obs.get("hour", 0)
    inventories = obs.get("private", {}).get("inventories", [{}])
    inventory = inventories[0] if inventories else {}
    farmer_has_animal = int(any(inventory.get(a, 0) > 0 for a in ANIMALS))

    # Opponent money (competitive signal)
    opp_player = 1 - player
    opp_farms = obs.get("farms", {})
    opp_money = opp_farms[opp_player].get("money", 3000) if opp_player in opp_farms else 3000

    # 0-1: farmer position
    vec[idx]      = fx / 9.0
    vec[idx + 1]  = fy / 9.0
    # 2-6: seeds
    vec[idx + 2]  = min(seeds.get("WHEAT", 0) / 20.0, 1.0)
    vec[idx + 3]  = min(seeds.get("MELON", 0) / 20.0, 1.0)
    vec[idx + 4]  = min(seeds.get("TOMATO", 0) / 20.0, 1.0)
    vec[idx + 5]  = min(seeds.get("CARROT", 0) / 20.0, 1.0)
    vec[idx + 6]  = min(seeds.get("STRAWBERRY", 0) / 20.0, 1.0)
    # 7-15: shed crops + animal products
    vec[idx + 7]  = min(shed.get("WHEAT", 0) / 20.0, 1.0)
    vec[idx + 8]  = min(shed.get("MELON", 0) / 20.0, 1.0)
    vec[idx + 9]  = min(shed.get("TOMATO", 0) / 20.0, 1.0)
    vec[idx + 10] = min(shed.get("CARROT", 0) / 20.0, 1.0)
    vec[idx + 11] = min(shed.get("STRAWBERRY", 0) / 20.0, 1.0)
    vec[idx + 12] = min(shed.get("EGG", 0) / 20.0, 1.0)
    vec[idx + 13] = min(shed.get("MILK", 0) / 20.0, 1.0)
    vec[idx + 14] = min(shed.get("WOOL", 0) / 20.0, 1.0)
    vec[idx + 15] = min(shed.get("FERTILIZER", 0) / 20.0, 1.0)
    # 16-18: animals in shed (waiting to be placed)
    vec[idx + 16] = min(shed.get("GOOSE", 0) / 5.0, 1.0)
    vec[idx + 17] = min(shed.get("COW", 0) / 5.0, 1.0)
    vec[idx + 18] = min(shed.get("SHEEP", 0) / 5.0, 1.0)
    # 19: money
    vec[idx + 19] = min(farm.get("money", 3000) / 50000.0, 1.0)
    # 20-21: time
    vec[idx + 20] = day / 30.0
    vec[idx + 21] = hour / 23.0
    # 22-29: market prices (all products)
    vec[idx + 22] = min(prices.get("WHEAT", 50) / 200.0, 1.0)
    vec[idx + 23] = min(prices.get("MELON", 150) / 400.0, 1.0)
    vec[idx + 24] = min(prices.get("TOMATO", 100) / 300.0, 1.0)
    vec[idx + 25] = min(prices.get("CARROT", 80) / 200.0, 1.0)
    vec[idx + 26] = min(prices.get("STRAWBERRY", 120) / 300.0, 1.0)
    vec[idx + 27] = min(prices.get("EGG", 30) / 100.0, 1.0)
    vec[idx + 28] = min(prices.get("MILK", 50) / 200.0, 1.0)
    vec[idx + 29] = min(prices.get("WOOL", 80) / 300.0, 1.0)
    vec[idx + 30] = min(prices.get("FERTILIZER", 20) / 50.0, 1.0)
    # 31-32: farm expansion state
    vec[idx + 31] = unlocked_count / 4.0
    vec[idx + 32] = min(hires_today / 5.0, 1.0)
    # 33-37: animal / structure / workforce state
    vec[idx + 33] = min(coop_count / 5.0, 1.0)
    vec[idx + 34] = min(pasture_count / 5.0, 1.0)
    vec[idx + 35] = min(total_animals / 10.0, 1.0)
    vec[idx + 36] = float(farmer_has_animal)
    vec[idx + 37] = min(active_hands / 5.0, 1.0)
    # 38: wheat in farmer inventory (for feeding)
    vec[idx + 38] = min(inventory.get("WHEAT", 0) / 5.0, 1.0)
    # 39: opponent money (competitive signal)
    vec[idx + 39] = min(opp_money / 50000.0, 1.0)
    # 40: reserved
    vec[idx + 40] = 0.0

    return vec


# --- Rule-based helpers ---

def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None


def heuristic_market_seeds_only(obs):
    """
    Minimal rule-based market: only restocks MELON seeds automatically.
    WHEAT seeds can be bought via action 31.
    All other decisions (SELL, HIRE, BUY_LAND, BUY_ANIMAL) are RL actions.
    """
    player = obs["player"]
    farm = obs["farms"][player]
    seeds = obs["private"]["seeds"]

    tiles = farm["tiles"]
    all_tiles = [(x, y, t) for y, row in enumerate(tiles) for x, t in enumerate(row)]
    melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
    unlocked = set(farm.get("unlocked_quadrants", []))

    melon_target = 18 if "SW" in unlocked else (14 if "NE" in unlocked else 8)

    actions = []
    if seeds.get("MELON", 0) + melon_count < melon_target:
        need = melon_target - melon_count - seeds.get("MELON", 0)
        if need > 0:
            actions.append(["BUY_SEED", "MELON", need])
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
    Wraps Kaggriculture as a standard Gymnasium environment.

    Player 0 = RL agent
      - Actions 0-19:  farmer acts, melon seeds auto-bought in market
      - Actions 20-34: farmer PASSes, specific market order issued
    Player 1 = heuristic opponent

    Episode = 720 turns (30 days × 24 turns/day).
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

        player = obs0["player"]
        farm = obs0["farms"][player]
        seeds = obs0["private"]["seeds"]
        shed = obs0["private"]["shed"]
        inventories = obs0.get("private", {}).get("inventories", [{}])
        inventory = inventories[0] if inventories else {}
        day = obs0["day"]

        # Melon seed restocking always runs
        market = heuristic_market_seeds_only(obs0)

        if action_int <= 9:
            farmer_act = FARMER_ACTIONS[action_int]

        elif action_int == 10:
            farmer_act = ["PLANT", "TOMATO"]
        elif action_int == 11:
            farmer_act = ["PLANT", "CARROT"]
        elif action_int == 12:
            farmer_act = ["PLANT", "STRAWBERRY"]
        elif action_int == 13:
            farmer_act = ["BUILD_COOP"]
        elif action_int == 14:
            farmer_act = ["BUILD_PASTURE"]

        elif action_int == 15:
            # Pick up first available animal from shed
            farmer_act = ["PASS"]
            for animal in ANIMALS:
                if shed.get(animal, 0) > 0:
                    farmer_act = ["PICKUP", animal, 1]
                    break

        elif action_int == 16:
            # Pick up wheat from shed for feeding
            wheat_in_shed = shed.get("WHEAT", 0)
            farmer_act = ["PICKUP", "WHEAT", min(2, wheat_in_shed)] if wheat_in_shed > 0 else ["PASS"]

        elif action_int == 17:
            # Place animal from farmer inventory onto current tile
            farmer_act = ["PASS"]
            for animal in ANIMALS:
                if inventory.get(animal, 0) > 0:
                    farmer_act = ["PLACE", animal]
                    break

        elif action_int == 18:
            farmer_act = ["CARE"]
        elif action_int == 19:
            farmer_act = ["COLLECT_FERTILIZER"]

        # --- Market actions (farmer PASSes) ---
        elif action_int == 20:
            farmer_act = ["PASS"]
            market.append(["HIRE"])
        elif action_int == 21:
            farmer_act = ["PASS"]
            market.append(["BUY_LAND"])
        elif action_int == 22:
            farmer_act = ["PASS"]
            amt = shed.get("MELON", 0)
            if amt > 0:
                market.append(["SELL", "MELON", amt])
        elif action_int == 23:
            farmer_act = ["PASS"]
            amt = shed.get("WHEAT", 0)
            if amt > 0:
                market.append(["SELL", "WHEAT", amt])
        elif action_int == 24:
            farmer_act = ["PASS"]
            amt = shed.get("TOMATO", 0)
            if amt > 0:
                market.append(["SELL", "TOMATO", amt])
        elif action_int == 25:
            farmer_act = ["PASS"]
            amt = shed.get("CARROT", 0)
            if amt > 0:
                market.append(["SELL", "CARROT", amt])
        elif action_int == 26:
            farmer_act = ["PASS"]
            amt = shed.get("STRAWBERRY", 0)
            if amt > 0:
                market.append(["SELL", "STRAWBERRY", amt])
        elif action_int == 27:
            farmer_act = ["PASS"]
            amt = shed.get("FERTILIZER", 0)
            if amt > 0:
                market.append(["SELL", "FERTILIZER", amt])
        elif action_int == 28:
            farmer_act = ["PASS"]
            market.append(["BUY_ANIMAL", "GOOSE", 1])
        elif action_int == 29:
            farmer_act = ["PASS"]
            market.append(["BUY_ANIMAL", "COW", 1])
        elif action_int == 30:
            farmer_act = ["PASS"]
            market.append(["BUY_ANIMAL", "SHEEP", 1])
        elif action_int == 31:
            farmer_act = ["PASS"]
            market.append(["BUY_SEED", "WHEAT", 5])
        elif action_int == 32:
            farmer_act = ["PASS"]
            market.append(["BUY_SEED", "TOMATO", 5])
        elif action_int == 33:
            farmer_act = ["PASS"]
            market.append(["BUY_SEED", "CARROT", 5])
        elif action_int == 34:
            farmer_act = ["PASS"]
            market.append(["BUY_SEED", "STRAWBERRY", 5])
        else:
            farmer_act = ["PASS"]

        action0 = {
            "farmer": farmer_act,
            "hands": [hand_action(hx, hy, farm["tiles"], seeds, day)
                      for hx, hy in farm.get("hands", [])],
            "market": market,
        }

        # Opponent action
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

        reward = (new_money - self._prev_money) / 1000.0
        self._prev_money = new_money

        return encode_obs(new_obs), reward, done, False, {}
