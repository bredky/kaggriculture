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


def carrot_sprinter(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    fx, fy = farm["farmer"]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    prices = obs["market"]["prices"]
    market_actions = []

    carrot_price = prices.get("CARROT", 20)
    wheat_price = prices.get("WHEAT", 10)
    use_carrot = carrot_price >= 15

    all_tiles = _find_tiles(farm)
    empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

    if use_carrot:
        needed = max(0, len(empty_tiles) + 15 - seeds.get("CARROT", 0))
        if needed > 0:
            market_actions.append(["BUY_SEED", "CARROT", needed])
    else:
        needed = max(0, len(empty_tiles) + 5 - seeds.get("WHEAT", 0))
        if needed > 0:
            market_actions.append(["BUY_SEED", "WHEAT", needed])

    if shed.get("CARROT", 0) > 0:
        market_actions.append(["SELL", "CARROT", shed["CARROT"]])
    if shed.get("WHEAT", 0) > 0:
        market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

    water_urgent = [(x, y, t) for x, y, t in all_tiles
                    if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    harvest_ready = [(x, y, t) for x, y, t in all_tiles
                     if isinstance(t, dict) and t.get("kind") == "PLANT"
                     and obs["day"] - t.get("planted_day", 0) >= 3]
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
    elif harvest_ready:
        tx, ty, _ = min(harvest_ready, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx == fx and ty == fy:
            farmer_action = ["HARVEST"]
        else:
            farmer_action = [_step_toward(fx, fy, tx, ty)]
    elif plantable:
        crop = "CARROT" if use_carrot and seeds.get("CARROT", 0) > 0 else ("WHEAT" if seeds.get("WHEAT", 0) > 0 else None)
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
