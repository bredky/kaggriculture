from kaggle_environments.envs.kaggriculture.kaggriculture import CROPS

_state = {}

def _step_toward(fx, fy, tx, ty):
    if fx > tx: return "WEST"
    if fx < tx: return "EAST"
    if fy > ty: return "NORTH"
    if fy < ty: return "SOUTH"
    return None

def _find_tiles(farm):
    result = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            result.append((x, y, tile))
    return result

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


def three_crop_rotation(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        prices = obs["market"]["prices"]
        market_actions = []

        wheat_price = prices.get("WHEAT", 15)
        carrot_price = prices.get("CARROT", 25)
        melon_price = prices.get("MELON", 150)

        # Zone assignments
        # Wheat: y=0, x=0-4 (top row, 5 tiles)
        # Carrot: y=1-2 (10 tiles)
        # Melon: y=3-4 but only 6 planted

        def zone_crop(y, x):
            if y == 0 and x <= 4:
                return "WHEAT"
            elif y in (1, 2):
                return "CARROT"
            elif y in (3, 4):
                return "MELON"
            return None

        all_tiles = _find_tiles(farm)

        # Buy seeds
        wheat_needed = sum(1 for x, y, t in all_tiles if t is None and zone_crop(y, x) == "WHEAT")
        carrot_needed = sum(1 for x, y, t in all_tiles if t is None and zone_crop(y, x) == "CARROT")
        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        melon_empty = [(x, y) for x, y, t in all_tiles if t is None and zone_crop(y, x) == "MELON"]
        melon_need = min(len(melon_empty), max(0, 6 - melon_count))

        if seeds.get("WHEAT", 0) < wheat_needed + 2:
            market_actions.append(["BUY_SEED", "WHEAT", wheat_needed + 2 - seeds.get("WHEAT", 0)])
        if seeds.get("CARROT", 0) < carrot_needed + 2:
            market_actions.append(["BUY_SEED", "CARROT", carrot_needed + 2 - seeds.get("CARROT", 0)])
        if seeds.get("MELON", 0) < melon_need:
            market_actions.append(["BUY_SEED", "MELON", melon_need - seeds.get("MELON", 0)])

        # Sell logic with price floors
        if shed.get("WHEAT", 0) > 0 and wheat_price >= 12:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])
        if shed.get("CARROT", 0) > 0 and carrot_price >= 17:
            market_actions.append(["SELL", "CARROT", shed["CARROT"]])
        if shed.get("MELON", 0) > 0 and melon_price >= 125:
            market_actions.append(["SELL", "MELON", min(3, shed["MELON"])])

        # Farmer actions
        water_urgent = [(x, y, t) for x, y, t in all_tiles
                        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest_ready = [(x, y, t) for x, y, t in all_tiles
                         if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
        plant_empty_zones = [(x, y) for x, y, t in all_tiles
                              if t is None and zone_crop(y, x) is not None]

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
        elif plant_empty_zones:
            tx, ty = min(plant_empty_zones, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            crop = zone_crop(ty, tx)
            if crop == "MELON" and melon_count >= 6:
                pass
            elif seeds.get(crop, 0) > 0:
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", crop]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
