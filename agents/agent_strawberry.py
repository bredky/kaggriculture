from kaggle_environments.envs.kaggriculture.kaggriculture import CROPS

STRAWBERRY_SEED_COST = CROPS["STRAWBERRY"]["seed"]       # 100
STRAWBERRY_FIRST_YIELD_DAY = CROPS["STRAWBERRY"]["first_yield_day"]  # 10
SELL_THRESHOLD = 150
TARGET_PLANTS = 6
PRICE_HISTORY_LEN = 6
RISING_MIN_GAIN = 5


def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None


def _count_strawberries(farm, board_size):
    count = 0
    for y in range(board_size):
        for x in range(board_size):
            tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile["crop"] == "STRAWBERRY":
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
            if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile["crop"] == "STRAWBERRY":
                purpose = None
                # Ongoing crop: harvest whenever yield_units > 0 after first yield day
                if (tile["yield_units"] > 0 and tile.get("planted_day") is not None
                        and (day - tile["planted_day"]) >= STRAWBERRY_FIRST_YIELD_DAY):
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


def _opponent_ripe_count(farms, player, board_size, day):
    opp = 1 - player
    if opp >= len(farms):
        return 0
    count = 0
    for row in farms[opp]["tiles"]:
        for tile in row:
            if (isinstance(tile, dict) and tile.get("kind") == "PLANT"
                    and tile.get("crop") == "STRAWBERRY"
                    and tile.get("planted_day") is not None
                    and (day - tile["planted_day"]) >= STRAWBERRY_FIRST_YIELD_DAY - 1):
                count += 1
    return count


def _price_trend(history):
    if len(history) < 3:
        return "stable"
    recent = history[-3:]
    avg_change = (recent[-1] - recent[0]) / 2
    if avg_change >= RISING_MIN_GAIN:
        return "rising"
    if avg_change <= -RISING_MIN_GAIN:
        return "falling"
    return "stable"


_state = {}


def strawberry_maxxer(obs):
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
    strawberry_price = market_prices.get("STRAWBERRY", 0)

    if player not in _state:
        _state[player] = {"price_history": []}
    state = _state[player]
    state["price_history"].append(strawberry_price)
    if len(state["price_history"]) > PRICE_HISTORY_LEN:
        state["price_history"].pop(0)

    trend = _price_trend(state["price_history"])
    opp_ripe = _opponent_ripe_count(farms, player, board_size, day)
    season_end = day >= 25

    market = []

    strawberries_in_shed = shed.get("STRAWBERRY", 0)
    if strawberries_in_shed > 0:
        if season_end:
            market.append(["SELL", "STRAWBERRY", strawberries_in_shed])
        elif opp_ripe >= 3 and strawberry_price >= 100:
            market.append(["SELL", "STRAWBERRY", strawberries_in_shed])
        elif trend == "falling" and strawberry_price >= SELL_THRESHOLD:
            market.append(["SELL", "STRAWBERRY", strawberries_in_shed])
        elif trend == "rising":
            pass
        elif strawberry_price >= SELL_THRESHOLD:
            market.append(["SELL", "STRAWBERRY", strawberries_in_shed])

    # Strawberry is ongoing — only buy seeds to reach TARGET_PLANTS, never replant
    strawberry_count = _count_strawberries(farm, board_size)
    seeds_have = seeds.get("STRAWBERRY", 0)
    seeds_needed = max(0, TARGET_PLANTS - strawberry_count - seeds_have)
    if seeds_needed > 0 and farm["money"] >= STRAWBERRY_SEED_COST:
        market.append(["BUY_SEED", "STRAWBERRY", seeds_needed])

    need_space = strawberry_count + seeds_have < TARGET_PLANTS

    farmer = ["PASS"]

    if isinstance(tile, dict) and tile.get("kind") == "PLANT" and tile["crop"] == "STRAWBERRY":
        age = day - tile["planted_day"]
        if age >= STRAWBERRY_FIRST_YIELD_DAY and tile["yield_units"] > 0:
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
        farmer = ["PLANT", "STRAWBERRY"]
    else:
        target = _find_target_tile(farm, board_size, seeds_have > 0, need_space, day, skip_x=None, skip_y=None)
        if target:
            if fx == target[0] and fy == target[1]:
                if target[2] == "dig":
                    farmer = ["DIG"]
                elif target[2] == "plant":
                    farmer = ["PLANT", "STRAWBERRY"]
            else:
                step = _step_toward(fx, fy, target[0], target[1])
                if step:
                    farmer = [step]

    return {"farmer": farmer, "hands": [], "market": market}
