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


def carrot_rush_to_melon(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        market_actions = []

        s = _state.setdefault(player, {"pivot_done": False, "melon_bought": False})

        all_tiles = _find_tiles(farm)
        carrot_tiles = [(x, y, t) for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "CARROT"]
        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        if day < 9:
            # Phase 1: carrot rush
            carrot_need = len(empty_tiles) + 3
            if seeds.get("CARROT", 0) < carrot_need:
                market_actions.append(["BUY_SEED", "CARROT", carrot_need - seeds.get("CARROT", 0)])
            if shed.get("CARROT", 0) > 0:
                market_actions.append(["SELL", "CARROT", shed["CARROT"]])

            # Farmer: water > harvest > plant carrot
            water_urgent = [(x, y, t) for x, y, t in all_tiles
                            if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
            harvest_carrot = [(x, y, t) for x, y, t in carrot_tiles if t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

            farmer_action = ["PASS"]
            if water_urgent:
                tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["WATER"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
            elif harvest_carrot:
                tx, ty, _ = min(harvest_carrot, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["HARVEST"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
            elif empty_tiles and seeds.get("CARROT", 0) > 0:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "CARROT"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
        else:
            # Phase 2: pivot to melon
            if not s["melon_bought"]:
                market_actions.append(["BUY_SEED", "MELON", 15])
                s["melon_bought"] = True

            if shed.get("CARROT", 0) > 0:
                market_actions.append(["SELL", "CARROT", shed["CARROT"]])
            if day >= 19 and shed.get("MELON", 0) > 0:
                market_actions.append(["SELL", "MELON", min(6, shed["MELON"])])
            if day >= 27 and shed.get("MELON", 0) > 0:
                market_actions.append(["SELL", "MELON", shed["MELON"]])

            # Farmer: DIG immature carrots > water > harvest > plant melon
            immature_carrots = [(x, y, t) for x, y, t in carrot_tiles
                                 if t.get("yield_units", 0) == 0 and (day - t.get("planted_day", 0)) < 3]
            water_urgent = [(x, y, t) for x, y, t in all_tiles
                            if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
            harvest_ready = [(x, y, t) for x, y, t in all_tiles
                              if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

            farmer_action = ["PASS"]
            if immature_carrots and melon_count < 15:
                tx, ty, _ = min(immature_carrots, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["DIG"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
            elif water_urgent:
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
            elif empty_tiles and melon_count < 15 and seeds.get("MELON", 0) > 0:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "MELON"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
