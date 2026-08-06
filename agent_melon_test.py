from kaggle_environments.envs.kaggriculture.kaggriculture import CROPS

MELON_SEED_COST = CROPS["MELON"]["seed"]
MELON_MAX_YIELD_DAY = CROPS["MELON"]["max_yield_day"]
SELL_THRESHOLD = 200
TARGET_PLANTS = 3  # how many melons to keep growing simultaneously

def _step_toward(fx, fy, tx, ty):
    if fx > tx:
        return "WEST"
    if fx < tx:
        return "EAST"
    if fy > ty:
        return "NORTH"
    if fy < ty:
        return "SOUTH"
    return None

def _count_melons(farm, board_size):
    count = 0
    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile["crop"] == "MELON":
                count += 1
    return count

def _find_target_tile(farm, board_size, have_seed, need_space, day, skip_x=None, skip_y=None):
    fx, fy = farm["farmer"]
    candidates = []
    for y in range(board_size):
        for x in range(board_size):
            if x == skip_x and y == skip_y:
                continue
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile["crop"] == "MELON":
                purpose = None
                if (tile["yield_units"] > 0 and tile.get("planted_day") is not None
                        and (day - tile["planted_day"]) >= MELON_MAX_YIELD_DAY):
                    purpose = "harvest"
                if not tile["watered_today"]:
                    purpose = "water" if purpose is None else purpose
                if purpose:
                    candidates.append((x, y, purpose))
            elif tile is None and have_seed:
                candidates.append((x, y, "plant"))
            elif isinstance(tile, dict) and tile.get("kind") == "WEED" and need_space:
                candidates.append((x, y, "dig"))

    if not candidates:
        return None

    priority = {"harvest": 0, "water": 1, "plant": 2, "dig": 3}
    candidates.sort(key=lambda c: (priority[c[2]], abs(c[0] - fx) + abs(c[1] - fy)))
    return candidates[0]

def test_melon_maxxer(obs):
    farms = obs.get("farms", [])
    player = obs.get("player", 0)
    private = obs.get("private", {}) or {}
    if not farms or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    farm = farms[player]
    board_size = len(farm["tiles"])
    fx, fy = farm["farmer"]
    tile = farm["tiles"][fy][fx]
    day = obs.get("day", 0)

    seeds = private.get("seeds", {})
    shed = private.get("shed", {})
    market_prices = (obs.get("market", {}) or {}).get("prices", {})
    melon_price = market_prices.get("MELON", 0)

    market = []

    # Sell melons if price is good enough, or in the last 5 days regardless of price.
    melons_in_shed = shed.get("MELON", 0)
    season_end = day >= 25
    if melons_in_shed > 0 and (melon_price >= SELL_THRESHOLD or season_end):
        market.append(["SELL", "MELON", melons_in_shed])

    # Buy enough seeds to fill up to TARGET_PLANTS tiles.
    melon_count = _count_melons(farm, board_size)
    seeds_have = seeds.get("MELON", 0)
    seeds_needed = max(0, TARGET_PLANTS - melon_count - seeds_have)
    if seeds_needed > 0 and farm["money"] >= MELON_SEED_COST:
        market.append(["BUY_SEED", "MELON", seeds_needed])

    need_space = melon_count + seeds_have < TARGET_PLANTS

    # Decide farmer action.
    farmer = ["PASS"]

    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile["crop"] == "MELON":
        age = day - tile["planted_day"]
        if age >= MELON_MAX_YIELD_DAY and tile["yield_units"] > 0:
            farmer = ["HARVEST"]
        elif not tile["watered_today"]:
            farmer = ["WATER"]
        else:
            target = _find_target_tile(farm, board_size, seeds_have > 0, need_space, day, skip_x=fx, skip_y=fy)
            if target:
                step = _step_toward(fx, fy, target[0], target[1])
                if step:
                    farmer = [step]
    elif isinstance(tile, dict) and tile.get("kind") == "WEED" and need_space:
        farmer = ["DIG"]
    elif tile is None and seeds_have > 0:
        farmer = ["PLANT", "MELON"]
    else:
        target = _find_target_tile(farm, board_size, seeds_have > 0, need_space, day, skip_x=None, skip_y=None)
        if target:
            if fx == target[0] and fy == target[1]:
                if target[2] == "dig":
                    farmer = ["DIG"]
                elif target[2] == "plant":
                    farmer = ["PLANT", "MELON"]
            else:
                step = _step_toward(fx, fy, target[0], target[1])
                if step:
                    farmer = [step]

    return {"farmer": farmer, "hands": [], "market": market}