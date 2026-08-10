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


def opponent_money_watcher(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        money = farm.get("money", 0)
        market_actions = []

        farms = obs["farms"]
        opp = 1 - player
        opp_money = farms[opp].get("money", 0) if opp < len(farms) else 0

        s = _state.setdefault(player, {
            "own_money_history": [],
            "opp_money_history": [],
            "last_track_day": -1
        })

        # Track money once per day
        if day != s["last_track_day"]:
            s["own_money_history"].append(money)
            s["opp_money_history"].append(opp_money)
            if len(s["own_money_history"]) > 3:
                s["own_money_history"] = s["own_money_history"][-3:]
                s["opp_money_history"] = s["opp_money_history"][-3:]
            s["last_track_day"] = day

        own_hist = s["own_money_history"]
        opp_hist = s["opp_money_history"]
        own_3day = (own_hist[-1] - own_hist[0]) if len(own_hist) >= 2 else 0
        opp_3day = (opp_hist[-1] - opp_hist[0]) if len(opp_hist) >= 2 else 0

        all_tiles = _find_tiles(farm)
        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        # Buy seeds
        if seeds.get("MELON", 0) + melon_count < 8:
            need = 8 - melon_count - seeds.get("MELON", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "MELON", need])
        if seeds.get("WHEAT", 0) + wheat_count < 5:
            need = 5 - wheat_count - seeds.get("WHEAT", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "WHEAT", need])

        # Sell wheat
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        # Sell melon: adapt rate based on opp performance
        melon_shed = shed.get("MELON", 0)
        if melon_shed > 0:
            if day >= 27:
                market_actions.append(["SELL", "MELON", melon_shed])
            elif opp_3day > own_3day + 500:
                market_actions.append(["SELL", "MELON", min(2, melon_shed)])
            elif opp_3day < own_3day - 500:
                market_actions.append(["SELL", "MELON", min(6, melon_shed)])
            else:
                market_actions.append(["SELL", "MELON", min(4, melon_shed)])

        # Farmer
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
        elif empty_tiles:
            plant_crop = None
            if melon_count < 8 and seeds.get("MELON", 0) > 0:
                plant_crop = "MELON"
            elif wheat_count < 5 and seeds.get("WHEAT", 0) > 0:
                plant_crop = "WHEAT"
            if plant_crop:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", plant_crop]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
