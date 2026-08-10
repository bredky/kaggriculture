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


def melon_bail_out(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        prices = obs["market"]["prices"]
        market_actions = []

        s = _state.setdefault(player, {
            "low_price_count": 0,
            "bail_out": False,
            "last_track_day": -1
        })

        melon_price = prices.get("MELON", 150)

        # Track price once per day
        if day != s["last_track_day"]:
            if melon_price < 100:
                s["low_price_count"] += 1
            else:
                s["low_price_count"] = 0

            if s["low_price_count"] >= 2:
                s["bail_out"] = True

            s["last_track_day"] = day

        all_tiles = _find_tiles(farm)
        melon_tiles = [(x, y, t) for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON"]
        melon_count = len(melon_tiles)
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        if s["bail_out"]:
            # Switch all sells to wheat
            if shed.get("WHEAT", 0) > 0:
                market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])
            # Still sell any accumulated melons
            if shed.get("MELON", 0) > 0:
                market_actions.append(["SELL", "MELON", shed["MELON"]])

            # Buy wheat seeds
            if seeds.get("WHEAT", 0) + wheat_count < 13:
                need = 13 - wheat_count - seeds.get("WHEAT", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "WHEAT", need])

            # Farmer: DIG immature melons > plant wheat > water > harvest
            immature_melon = [(x, y, t) for x, y, t in melon_tiles
                               if t.get("yield_units", 0) == 0 and (day - t.get("planted_day", 0)) < 10]

            water_urgent = [(x, y, t) for x, y, t in all_tiles
                            if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
            harvest_ready = [(x, y, t) for x, y, t in all_tiles
                              if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

            farmer_action = ["PASS"]
            if immature_melon:
                tx, ty, _ = min(immature_melon, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
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
            elif empty_tiles and seeds.get("WHEAT", 0) > 0:
                tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    farmer_action = ["PLANT", "WHEAT"]
                else:
                    farmer_action = [_step_toward(fx, fy, tx, ty)]

            return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}

        else:
            # Normal mode: melon + wheat
            if seeds.get("MELON", 0) + melon_count < 8:
                need = 8 - melon_count - seeds.get("MELON", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "MELON", need])
            if seeds.get("WHEAT", 0) + wheat_count < 5:
                need = 5 - wheat_count - seeds.get("WHEAT", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "WHEAT", need])

            if shed.get("WHEAT", 0) > 0:
                market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

            melon_shed = shed.get("MELON", 0)
            if melon_shed > 0:
                if day >= 27:
                    market_actions.append(["SELL", "MELON", melon_shed])
                elif melon_price >= 120:
                    market_actions.append(["SELL", "MELON", min(4, melon_shed)])

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
