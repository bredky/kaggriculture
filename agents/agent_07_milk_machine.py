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


def _shed_adjacent(fx, fy):
    return (fx, fy) in {(4, 4), (5, 4), (4, 5), (5, 5)}

def _animal_setup(fx, fy, all_tiles, farm, inv, shed, animal, structure):
    cur_tile = farm["tiles"][fy][fx] if 0 <= fy < len(farm["tiles"]) and 0 <= fx < len(farm["tiles"][fy]) else None
    has_inv = inv.get(animal, 0) > 0
    has_shed = shed.get(animal, 0) > 0
    structures = [(x, y, t) for x, y, t in all_tiles if isinstance(t, dict) and t.get("kind") == structure]
    unoccupied = [(x, y, t) for x, y, t in structures if "animal" not in t]
    occupied = [(x, y, t) for x, y, t in structures if "animal" in t]
    if has_inv:
        if unoccupied:
            tx, ty, _ = min(unoccupied, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy: return ["PLACE", animal]
            return [_step_toward(fx, fy, tx, ty)]
        if cur_tile is None:
            return ["BUILD_COOP"] if structure == "COOP" else ["BUILD_PASTURE"]
        empty = [(x, y) for x, y, t in all_tiles if t is None]
        if empty:
            tx, ty = min(empty, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            return [_step_toward(fx, fy, tx, ty)]
    if has_shed:
        if _shed_adjacent(fx, fy): return ["PICKUP", animal, 1]
        return [_step_toward(fx, fy, 4, 4)]
    return None

def _animal_care(fx, fy, all_tiles, farm, inv, structure):
    occupied = [(x, y, t) for x, y, t in all_tiles if isinstance(t, dict) and t.get("kind") == structure and "animal" in t]
    if not occupied: return None
    cur_tile = farm["tiles"][fy][fx] if 0 <= fy < len(farm["tiles"]) and 0 <= fx < len(farm["tiles"][fy]) else None
    if isinstance(cur_tile, dict) and "animal" in cur_tile:
        if not cur_tile.get("fed_today", False) and inv.get("WHEAT", 0) > 0: return ["FEED"]
        if not cur_tile.get("cared_today", False): return ["CARE"]
        if cur_tile.get("yield_units", 0) > 0: return ["HARVEST"]
        if cur_tile.get("fertilizer_available", False): return ["COLLECT_FERTILIZER"]
    needs_feed = [(x, y, t) for x, y, t in occupied if not t.get("fed_today", False)]
    if needs_feed and inv.get("WHEAT", 0) == 0:
        if _shed_adjacent(fx, fy): return ["PICKUP", "WHEAT", len(needs_feed)]
        return [_step_toward(fx, fy, 4, 4)]
    if occupied:
        tx, ty, _ = min(occupied, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx != fx or ty != fy: return [_step_toward(fx, fy, tx, ty)]
    return None


def milk_machine(obs):
    player = obs["player"]
    farm = obs["farms"][player]
    fx, fy = farm["farmer"]
    seeds = obs["private"]["seeds"]
    shed = obs["private"]["shed"]
    prices = obs["market"]["prices"]
    market_inv = obs["market"]["inventory"]
    day = obs["day"]
    market_actions = []
    all_tiles = _find_tiles(farm)

    s = _state.setdefault(player, {"cows_bought": 0, "milk_sold_today": 0, "last_day": -1})
    if day != s["last_day"]:
        s["milk_sold_today"] = 0
        s["last_day"] = day

    if day == 0 and s["cows_bought"] == 0:
        market_actions.append(["BUY_ANIMAL", "COW", 2])
        s["cows_bought"] = 2
    elif day == 2 and s["cows_bought"] < 4:
        market_actions.append(["BUY_ANIMAL", "COW", 2])
        s["cows_bought"] = 4

    empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]
    if seeds.get("WHEAT", 0) < len(empty_tiles) + 5:
        market_actions.append(["BUY_SEED", "WHEAT", len(empty_tiles) + 5 - seeds.get("WHEAT", 0)])

    milk_in_shed = shed.get("MILK", 0)
    milk_inv = market_inv.get("MILK", 0)
    if milk_in_shed > 0 and s["milk_sold_today"] < 5:
        if milk_inv <= 45:
            sell_qty = min(milk_in_shed, 5 - s["milk_sold_today"])
            market_actions.append(["SELL", "MILK", sell_qty])
            s["milk_sold_today"] += sell_qty

    if shed.get("FERTILIZER", 0) > 0:
        market_actions.append(["SELL", "FERTILIZER", shed["FERTILIZER"]])
    if shed.get("WHEAT", 0) > 0:
        market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

    pastures = [(x, y, t) for x, y, t in all_tiles if isinstance(t, dict) and t.get("kind") == "PASTURE"]
    water_urgent = [(x, y, t) for x, y, t in all_tiles
                    if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    wheat_harvest = [(x, y, t) for x, y, t in all_tiles
                     if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "WHEAT"
                     and day - t.get("planted_day", 0) >= 4]
    plantable = [(x, y) for x, y, t in all_tiles if t is None]


    farmer_action = ["PASS"]

    # Animal lifecycle: highest priority
    inv = obs["private"]["inventories"][0]
    _asetup = _animal_setup(fx, fy, all_tiles, farm, inv, shed, "COW", "PASTURE")
    if _asetup is not None:
        farmer_action = _asetup
    else:
        _acare = _animal_care(fx, fy, all_tiles, farm, inv, "PASTURE")
        if _acare is not None:
            farmer_action = _acare

    # Regular farming: water > harvest > plant wheat
    if farmer_action == ["PASS"]:
        water = [(x, y, t) for x, y, t in all_tiles
                 if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest = [(x, y, t) for x, y, t in all_tiles
                   if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0
                   and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
        empty = [(x, y) for x, y, t in all_tiles if t is None]
        if water:
            tx, ty, _ = min(water, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            farmer_action = ["WATER"] if tx == fx and ty == fy else [_step_toward(fx, fy, tx, ty)]
        elif harvest:
            tx, ty, _ = min(harvest, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            farmer_action = ["HARVEST"] if tx == fx and ty == fy else [_step_toward(fx, fy, tx, ty)]
        elif empty and seeds.get("WHEAT", 0) > 0:
            tx, ty = min(empty, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            farmer_action = ["PLANT", "WHEAT"] if tx == fx and ty == fy else [_step_toward(fx, fy, tx, ty)]

    return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
