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


MELON_TILES = 6
MELON_START_DAY = 2

def wheat_melon_alternator(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    fx, fy = farm["farmer"]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    prices = obs["market"]["prices"]
    day = obs["day"]
    market_actions = []

    s = _state.setdefault(player, {"melon_sold_today": 0, "last_day": -1})
    if day != s["last_day"]:
        s["melon_sold_today"] = 0
        s["last_day"] = day

    all_tiles = _find_tiles(farm)
    melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "MELON")
    empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

    if day >= 20:
        if seeds.get("WHEAT", 0) < len(empty_tiles) + 5:
            market_actions.append(["BUY_SEED", "WHEAT", len(empty_tiles) + 5 - seeds.get("WHEAT", 0)])
    elif day >= MELON_START_DAY:
        melon_needed = max(0, MELON_TILES - melon_count)
        if melon_needed > 0 and seeds.get("MELON", 0) < melon_needed:
            market_actions.append(["BUY_SEED", "MELON", melon_needed - seeds.get("MELON", 0)])
        wheat_slots = max(0, len(empty_tiles) - melon_needed)
        if wheat_slots > 0 and seeds.get("WHEAT", 0) < wheat_slots:
            market_actions.append(["BUY_SEED", "WHEAT", wheat_slots - seeds.get("WHEAT", 0)])
    else:
        if seeds.get("WHEAT", 0) < len(empty_tiles) + 5:
            market_actions.append(["BUY_SEED", "WHEAT", len(empty_tiles) + 5 - seeds.get("WHEAT", 0)])

    melon_price = prices.get("MELON", 100)
    melon_in_shed = shed.get("MELON", 0)
    if melon_in_shed > 0 and melon_price >= 120 and s["melon_sold_today"] < 6:
        sell_qty = min(melon_in_shed, 6 - s["melon_sold_today"])
        market_actions.append(["SELL", "MELON", sell_qty])
        s["melon_sold_today"] += sell_qty

    if shed.get("WHEAT", 0) > 0:
        market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

    water_urgent = [(x, y, t) for x, y, t in all_tiles
                    if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    harvest_ready = [(x, y, t) for x, y, t in all_tiles
                     if isinstance(t, dict) and t.get("kind") == "PLANT"
                     and ((t.get("crop") == "MELON" and day - t.get("planted_day", 0) >= 10)
                          or (t.get("crop") == "WHEAT" and day - t.get("planted_day", 0) >= 4))]

    melon_needed_now = max(0, MELON_TILES - melon_count) if day >= MELON_START_DAY and day < 20 else 0
    plantable_melon = [(x, y) for x, y, t in all_tiles if t is None and melon_needed_now > 0 and seeds.get("MELON", 0) > 0]
    plantable_wheat = [(x, y) for x, y, t in all_tiles if t is None and seeds.get("WHEAT", 0) > 0]
    water_bonus = [(x, y, t) for x, y, t in all_tiles
                   if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]

    farmer_action = ["PASS"]

    if water_urgent:
        tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["WATER"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif harvest_ready:
        tx, ty, _ = min(harvest_ready, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["HARVEST"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif plantable_melon:
        tx, ty = min(plantable_melon, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["PLANT", "MELON"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif plantable_wheat:
        tx, ty = min(plantable_wheat, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["PLANT", "WHEAT"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif water_bonus:
        tx, ty, _ = min(water_bonus, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["WATER"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]

    return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
