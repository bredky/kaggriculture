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


def fertilizer_arbitrageur(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        prices = obs["market"]["prices"]
        market_inv = obs["market"]["inventory"]
        market_actions = []

        s = _state.setdefault(player, {"geese_bought": False})

        if not s["geese_bought"]:
            market_actions.append(["BUY_ANIMAL", "GOOSE", 6])
            s["geese_bought"] = True

        all_tiles = _find_tiles(farm)
        tomato_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "TOMATO")
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # Buy seeds
        if seeds.get("TOMATO", 0) + tomato_count < 6:
            need = 6 - tomato_count - seeds.get("TOMATO", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "TOMATO", need])
        if seeds.get("WHEAT", 0) + wheat_count < 6:
            need = 6 - wheat_count - seeds.get("WHEAT", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "WHEAT", need])

        # Sell fertilizer (2-4/day based on market inventory)
        fert_inv = market_inv.get("FERTILIZER", 0)
        fert_rate = 2 if fert_inv > 300 else 4
        if shed.get("FERTILIZER", 0) > 0:
            market_actions.append(["SELL", "FERTILIZER", min(fert_rate, shed["FERTILIZER"])])

        # Sell eggs and tomatoes daily
        if shed.get("EGG", 0) > 0:
            market_actions.append(["SELL", "EGG", shed["EGG"]])
        if shed.get("TOMATO", 0) > 0:
            market_actions.append(["SELL", "TOMATO", shed["TOMATO"]])
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        # Farmer
        cur_tile = farm["tiles"][fy][fx] if 0 <= fy < len(farm["tiles"]) and 0 <= fx < len(farm["tiles"][fy]) else None

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

        if cur_tile and cur_tile.get("kind") in ("COOP", "PASTURE"):
            farmer_action = ["COLLECT_FERTILIZER"]
        elif water_urgent:
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
            if tomato_count < 6 and seeds.get("TOMATO", 0) > 0:
                tx, ty, _ = empty_tiles[0]
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "TOMATO"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]
            elif wheat_count < 6 and seeds.get("WHEAT", 0) > 0:
                tx, ty, _ = empty_tiles[0]
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "WHEAT"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
