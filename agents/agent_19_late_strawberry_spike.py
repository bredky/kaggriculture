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


def late_strawberry_spike(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        prices = obs["market"]["prices"]
        market_actions = []

        s = _state.setdefault(player, {"strawberry_planted": 0, "wheat_planted": False})

        all_tiles = _find_tiles(farm)

        # Buy seeds
        straw_planted = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "STRAWBERRY")
        wheat_planted = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        if seeds.get("STRAWBERRY", 0) < max(0, 10 - straw_planted):
            need = 10 - straw_planted - seeds.get("STRAWBERRY", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "STRAWBERRY", need])
        if seeds.get("WHEAT", 0) < max(0, 3 - wheat_planted):
            need = 3 - wheat_planted - seeds.get("WHEAT", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "WHEAT", need])

        # Sell logic
        melon_price = prices.get("MELON", 0)
        straw_price = prices.get("STRAWBERRY", 0)
        wheat_shed = shed.get("WHEAT", 0)
        straw_shed = shed.get("STRAWBERRY", 0)

        # Sell wheat daily
        if wheat_shed > 0:
            market_actions.append(["SELL", "WHEAT", wheat_shed])

        # Strawberry: hold until day 20
        if day >= 20 and straw_shed > 0:
            rate = 5 if straw_price > 150 else 3
            sell_qty = min(rate, straw_shed)
            market_actions.append(["SELL", "STRAWBERRY", sell_qty])

        # Farmer actions
        plant_tiles = [(x, y, t) for x, y, t in all_tiles if t is None]
        water_urgent = [(x, y, t) for x, y, t in all_tiles
                        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest_ready = [(x, y, t) for x, y, t in all_tiles
                         if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
        wheat_harvest = [(x, y, t) for x, y, t in harvest_ready if t.get("crop") == "WHEAT"]
        straw_harvest = [(x, y, t) for x, y, t in harvest_ready if t.get("crop") == "STRAWBERRY"]

        farmer_action = ["PASS"]

        if water_urgent:
            tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["WATER"]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]
        elif straw_harvest:
            tx, ty, _ = min(straw_harvest, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
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
        elif plant_tiles:
            # Plant strawberry first (up to 10), then wheat (up to 3)
            if straw_planted < 10 and seeds.get("STRAWBERRY", 0) > 0:
                tx, ty, _ = plant_tiles[0]
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "STRAWBERRY"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
            elif wheat_planted < 3 and seeds.get("WHEAT", 0) > 0:
                tx, ty, _ = plant_tiles[0]
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "WHEAT"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
