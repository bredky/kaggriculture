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


def price_momentum_seller(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        hour = obs["hour"]
        prices = obs["market"]["prices"]
        market_actions = []

        s = _state.setdefault(player, {
            "price_history": [],
            "last_price_day": -1,
            "low_price_days": 0,
            "bail_out": False
        })

        melon_price = prices.get("MELON", 150)

        # Track price once per day
        if day != s["last_price_day"]:
            s["price_history"].append(melon_price)
            if len(s["price_history"]) > 6:
                s["price_history"] = s["price_history"][-6:]
            s["last_price_day"] = day

            # Check low price streak
            if melon_price < 80:
                s["low_price_days"] += 1
            else:
                s["low_price_days"] = 0

            if s["low_price_days"] >= 3:
                s["bail_out"] = True

        # Compute momentum
        history = s["price_history"]
        if len(history) >= 4:
            momentum = (history[-1] - history[-4]) / 3
        else:
            momentum = 0

        all_tiles = _find_tiles(farm)
        melon_tiles = [(x, y, t) for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON"]
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        melon_count = len(melon_tiles)

        melon_shed = shed.get("MELON", 0)

        # Bail out: DIG immature melon tiles, plant wheat
        if s["bail_out"]:
            if shed.get("WHEAT", 0) > 0:
                market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])
            if melon_shed > 0:
                market_actions.append(["SELL", "MELON", melon_shed])

            # Farmer: DIG immature melon, plant wheat
            immature_melon = [(x, y, t) for x, y, t in melon_tiles
                               if t.get("yield_units", 0) == 0 and (day - t.get("planted_day", 0)) < 10]
            if immature_melon:
                tx, ty, _ = min(immature_melon, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                if tx == fx and ty == fy:
                    return {"farmer": ["DIG"], "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
                else:
                    return {"farmer": [_step_toward(fx, fy, tx, ty)], "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
        else:
            # Buy seeds
            if seeds.get("MELON", 0) + melon_count < 8:
                need = 8 - melon_count - seeds.get("MELON", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "MELON", need])
            if seeds.get("WHEAT", 0) + wheat_count < 5:
                need = 5 - wheat_count - seeds.get("WHEAT", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "WHEAT", need])

            # Melon sell by momentum
            if day >= 27:
                if melon_shed > 0:
                    market_actions.append(["SELL", "MELON", melon_shed])
            elif melon_shed > 0:
                if momentum >= 5:
                    market_actions.append(["SELL", "MELON", melon_shed])
                elif momentum <= -5:
                    pass  # hold
                else:
                    market_actions.append(["SELL", "MELON", min(4, melon_shed)])

        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

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
            if not s["bail_out"] and melon_count < 8 and seeds.get("MELON", 0) > 0:
                plant_crop = "MELON"
            elif seeds.get("WHEAT", 0) > 0 and wheat_count < 5:
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
