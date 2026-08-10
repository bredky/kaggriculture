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


TOMATO_TARGET = 12

def tomato_perennial(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    fx, fy = farm["farmer"]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    day = obs["day"]
    market_actions = []

    all_tiles = _find_tiles(farm)
    empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]
    tomato_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "TOMATO")
    tomatoes_needed = max(0, TOMATO_TARGET - tomato_count)

    if tomatoes_needed > 0 and seeds.get("TOMATO", 0) < tomatoes_needed:
        market_actions.append(["BUY_SEED", "TOMATO", tomatoes_needed - seeds.get("TOMATO", 0)])

    wheat_slots = max(0, len(empty_tiles) - tomatoes_needed)
    if wheat_slots > 0 and seeds.get("WHEAT", 0) < wheat_slots:
        market_actions.append(["BUY_SEED", "WHEAT", wheat_slots - seeds.get("WHEAT", 0)])

    if shed.get("TOMATO", 0) > 0:
        market_actions.append(["SELL", "TOMATO", shed["TOMATO"]])
    if shed.get("WHEAT", 0) > 0:
        market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

    water_urgent = [(x, y, t) for x, y, t in all_tiles
                    if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    tomato_harvest = [(x, y, t) for x, y, t in all_tiles
                      if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "TOMATO"
                      and t.get("yield_units", 0) >= 2]
    wheat_harvest = [(x, y, t) for x, y, t in all_tiles
                     if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "WHEAT"
                     and day - t.get("planted_day", 0) >= 4]
    plantable = [(x, y) for x, y, t in all_tiles if t is None]
    water_bonus = [(x, y, t) for x, y, t in all_tiles
                   if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]

    farmer_action = ["PASS"]

    if water_urgent:
        tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["WATER"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif tomato_harvest:
        tx, ty, _ = min(tomato_harvest, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["HARVEST"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif wheat_harvest:
        tx, ty, _ = min(wheat_harvest, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["HARVEST"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif plantable:
        crop = None
        if tomatoes_needed > 0 and seeds.get("TOMATO", 0) > 0:
            crop = "TOMATO"
        elif seeds.get("WHEAT", 0) > 0:
            crop = "WHEAT"
        if crop:
            tx, ty = min(plantable, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
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
