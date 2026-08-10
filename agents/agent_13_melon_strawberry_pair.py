_state = {}

def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None

def _find_tiles(farm):
    tiles = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            tiles.append((x, y, tile))
    return tiles

def _hand_action(hx, hy, tiles_2d, seeds, day):
    """Generate an action for a hired hand at (hx, hy)."""
    all_t = [(x, y, t) for y, row in enumerate(tiles_2d) for x, t in enumerate(row)]
    water = [(x, y, t) for x, y, t in all_t
             if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    harvest = [(x, y, t) for x, y, t in all_t
               if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0
               and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    empty = [(x, y) for x, y, t in all_t if t is None]
    if water:
        tx, ty, _ = min(water, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if harvest:
        tx, ty, _ = min(harvest, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["HARVEST"]
        return [_step_toward(hx, hy, tx, ty)]
    for crop in ["WHEAT", "MELON", "STRAWBERRY", "TOMATO", "CARROT"]:
        if seeds.get(crop, 0) > 0 and empty:
            tx, ty = min(empty, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
            if tx == hx and ty == hy: return ["PLANT", crop]
            return [_step_toward(hx, hy, tx, ty)]
    return ["PASS"]


MELON_TARGET = 8
STRAWBERRY_TARGET = 6

def melon_strawberry_pair(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    fx, fy = farm["farmer"]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    prices = obs["market"]["prices"]
    day = obs["day"]
    market_actions = []

    s = _state.setdefault(player, {
        "melon_sold_today": 0, "sb_sold_today": 0, "last_sell": "", "last_day": -1
    })
    if day != s["last_day"]:
        s["melon_sold_today"] = 0
        s["sb_sold_today"] = 0
        s["last_sell"] = ""
        s["last_day"] = day

    all_tiles = _find_tiles(farm)
    melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "MELON")
    sb_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY")
    empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

    melon_needed = max(0, MELON_TARGET - melon_count)
    sb_needed = max(0, STRAWBERRY_TARGET - sb_count)

    if melon_needed > 0 and seeds.get("MELON", 0) < melon_needed:
        market_actions.append(["BUY_SEED", "MELON", melon_needed - seeds.get("MELON", 0)])
    if sb_needed > 0 and seeds.get("STRAWBERRY", 0) < sb_needed:
        market_actions.append(["BUY_SEED", "STRAWBERRY", sb_needed - seeds.get("STRAWBERRY", 0)])

    melon_price = prices.get("MELON", 100)
    sb_price = prices.get("STRAWBERRY", 100)

    melon_in_shed = shed.get("MELON", 0)
    sb_in_shed = shed.get("STRAWBERRY", 0)

    if melon_in_shed > 0 and melon_price >= 150 and s["melon_sold_today"] < 3 and s["last_sell"] != "sb":
        sell_qty = min(melon_in_shed, 3 - s["melon_sold_today"])
        market_actions.append(["SELL", "MELON", sell_qty])
        s["melon_sold_today"] += sell_qty
        s["last_sell"] = "melon"
    elif sb_in_shed > 0 and sb_price >= 80 and s["sb_sold_today"] < 2 and s["last_sell"] != "melon":
        sell_qty = min(sb_in_shed, 2 - s["sb_sold_today"])
        market_actions.append(["SELL", "STRAWBERRY", sell_qty])
        s["sb_sold_today"] += sell_qty
        s["last_sell"] = "sb"

    water_urgent = [(x, y, t) for x, y, t in all_tiles
                    if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    melon_harvest = [(x, y, t) for x, y, t in all_tiles
                     if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "MELON"
                     and day - t.get("planted_day", 0) >= 10]
    sb_harvest = [(x, y, t) for x, y, t in all_tiles
                  if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY"
                  and t.get("yield_units", 0) >= 1 and day - t.get("planted_day", 0) >= 10]
    water_bonus = [(x, y, t) for x, y, t in all_tiles
                   if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]

    farmer_action = ["PASS"]

    if water_urgent:
        tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["WATER"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif melon_harvest or sb_harvest:
        candidates = melon_harvest if melon_harvest else sb_harvest
        tx, ty, _ = min(candidates, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["HARVEST"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif empty_tiles:
        crop = None
        if melon_needed > 0 and seeds.get("MELON", 0) > 0:
            crop = "MELON"
        elif sb_needed > 0 and seeds.get("STRAWBERRY", 0) > 0:
            crop = "STRAWBERRY"
        if crop:
            tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["PLANT", crop]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif water_bonus:
        tx, ty, _ = min(water_bonus, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["WATER"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]

    return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
