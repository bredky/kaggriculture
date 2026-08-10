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


def wheat_tomato_split(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        market_actions = []

        s = _state.setdefault(player, {"init": False})

        if not s["init"]:
            market_actions.append(["BUY_SEED", "TOMATO", 10])
            market_actions.append(["BUY_SEED", "WHEAT", 12])
            market_actions.append(["HIRE"])
            s["init"] = True

        # Sell
        if shed.get("TOMATO", 0) > 0:
            market_actions.append(["SELL", "TOMATO", min(8, shed["TOMATO"])])
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        all_tiles = _find_tiles(farm)
        tomato_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "TOMATO")
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # Replenish seeds if needed
        if seeds.get("WHEAT", 0) + wheat_count < 12:
            need = 12 - wheat_count - seeds.get("WHEAT", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "WHEAT", need])

        # Zone assignment: tomato on y=0,1 rows (first 10 tiles), wheat on rest
        def preferred_crop(y, x):
            if y <= 1:
                return "TOMATO"
            return "WHEAT"

        # Farmer: water > harvest tomato >= 2 > harvest wheat > plant
        water_urgent = [(x, y, t) for x, y, t in all_tiles
                        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest_tomato = [(x, y, t) for x, y, t in all_tiles
                           if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "TOMATO"
                           and t.get("yield_units", 0) >= 2]
        harvest_wheat = [(x, y, t) for x, y, t in all_tiles
                          if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "WHEAT"
                          and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        farmer_action = ["PASS"]

        if water_urgent:
            tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["WATER"]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]
        elif harvest_tomato:
            tx, ty, _ = min(harvest_tomato, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["HARVEST"]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]
        elif harvest_wheat:
            tx, ty, _ = min(harvest_wheat, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["HARVEST"]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]
        elif empty_tiles:
            # Pick best tile based on zone
            tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            crop = preferred_crop(ty, tx)
            if crop == "TOMATO" and tomato_count < 10 and seeds.get("TOMATO", 0) > 0:
                pass
            elif crop == "WHEAT" or seeds.get("TOMATO", 0) == 0:
                crop = "WHEAT"
            if seeds.get(crop, 0) > 0:
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", crop]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
