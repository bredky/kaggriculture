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


def day6_melon_planter(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        market_actions = []

        s = _state.setdefault(player, {"melon_bought": False, "hands_hired": False})

        if not s["hands_hired"]:
            market_actions.append(["HIRE"])
            s["hands_hired"] = True

        all_tiles = _find_tiles(farm)
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        if day < 6:
            # Phase 1: all wheat
            if seeds.get("WHEAT", 0) + wheat_count < 20:
                need = 20 - wheat_count - seeds.get("WHEAT", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "WHEAT", need])
            if shed.get("WHEAT", 0) > 0:
                market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

            water_urgent = [(x, y, t) for x, y, t in all_tiles
                            if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
            harvest_ready = [(x, y, t) for x, y, t in all_tiles
                              if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

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
            elif empty_tiles and seeds.get("WHEAT", 0) > 0:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "WHEAT"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

            return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
        else:
            # Phase 2/3: pivot to melon
            if not s["melon_bought"]:
                market_actions.append(["BUY_SEED", "MELON", 12])
                s["melon_bought"] = True
            # Continuously restock melon seeds to enable second harvest cycle
            if seeds.get("MELON", 0) + melon_count < 12:
                need = 12 - melon_count - seeds.get("MELON", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "MELON", need])

            if shed.get("WHEAT", 0) > 0:
                market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

            melon_shed = shed.get("MELON", 0)
            if day >= 27 and melon_shed > 0:
                market_actions.append(["SELL", "MELON", melon_shed])
            elif day >= 16 and melon_shed > 0:
                market_actions.append(["SELL", "MELON", min(5, melon_shed)])

            # DIG immature wheat tiles to make room for melons
            immature_wheat = [(x, y, t) for x, y, t in all_tiles
                               if isinstance(t, dict) and t.get("crop") == "WHEAT"
                               and t.get("yield_units", 0) == 0
                               and (day - t.get("planted_day", 0)) < 4
                               and melon_count < 12]

            water_urgent = [(x, y, t) for x, y, t in all_tiles
                            if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
            harvest_ready = [(x, y, t) for x, y, t in all_tiles
                              if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

            farmer_action = ["PASS"]
            if immature_wheat:
                tx, ty, _ = min(immature_wheat, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
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
            elif empty_tiles and melon_count < 12 and seeds.get("MELON", 0) > 0:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "MELON"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
            elif empty_tiles and seeds.get("WHEAT", 0) > 0:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "WHEAT"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

            return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
