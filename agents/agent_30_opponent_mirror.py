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


def _count_crop(tiles, crop):
    return sum(1 for x, y, t in tiles if isinstance(t, dict) and t.get("crop") == crop)

def opponent_mirror(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        market_actions = []

        farms = obs["farms"]
        opp = 1 - player
        opp_farm = farms[opp] if opp < len(farms) else None

        s = _state.setdefault(player, {"decision": None, "last_check": -1, "init": False})

        # Day 0: plant 5 wheat
        all_tiles = _find_tiles(farm)
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        if not s["init"]:
            market_actions.append(["BUY_SEED", "WHEAT", 5])
            s["init"] = True

        # Re-check opponent every 3 days
        if day >= 1 and (day - s["last_check"]) >= 3:
            if opp_farm:
                opp_tiles = _find_tiles(opp_farm)
                opp_melon = _count_crop(opp_tiles, "MELON")
                opp_carrot = _count_crop(opp_tiles, "CARROT")
                opp_tomato = _count_crop(opp_tiles, "TOMATO")

                if opp_melon >= 3:
                    s["decision"] = "TOMATO_CARROT"
                elif opp_carrot >= 5:
                    s["decision"] = "MELON"
                elif opp_tomato >= 5:
                    s["decision"] = "MELON"
                else:
                    s["decision"] = "MELON"
            s["last_check"] = day

        # Buy seeds based on decision
        decision = s["decision"]
        if day >= 2 and decision:
            if decision == "MELON":
                melon_count = _count_crop(all_tiles, "MELON")
                if seeds.get("MELON", 0) + melon_count < 10:
                    need = 10 - melon_count - seeds.get("MELON", 0)
                    if need > 0:
                        market_actions.append(["BUY_SEED", "MELON", need])
            elif decision == "TOMATO_CARROT":
                tomato_count = _count_crop(all_tiles, "TOMATO")
                carrot_count = _count_crop(all_tiles, "CARROT")
                if seeds.get("TOMATO", 0) + tomato_count < 5:
                    need = 5 - tomato_count - seeds.get("TOMATO", 0)
                    if need > 0:
                        market_actions.append(["BUY_SEED", "TOMATO", need])
                if seeds.get("CARROT", 0) + carrot_count < 5:
                    need = 5 - carrot_count - seeds.get("CARROT", 0)
                    if need > 0:
                        market_actions.append(["BUY_SEED", "CARROT", need])

        # Sell all immediately
        for crop in ["WHEAT", "CARROT", "MELON", "TOMATO", "STRAWBERRY"]:
            if shed.get(crop, 0) > 0:
                market_actions.append(["SELL", crop, shed[crop]])

        # Farmer
        water_urgent = [(x, y, t) for x, y, t in all_tiles
                        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest_ready = [(x, y, t) for x, y, t in all_tiles
                         if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

        # Determine what to plant
        def pick_crop():
            if day < 2 or not decision:
                return "WHEAT"
            if decision == "MELON":
                return "MELON"
            # TOMATO_CARROT: alternate
            tc = _count_crop(all_tiles, "TOMATO")
            cc = _count_crop(all_tiles, "CARROT")
            return "TOMATO" if tc <= cc else "CARROT"

        plant_crop = pick_crop()

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
        elif empty_tiles and seeds.get(plant_crop, 0) > 0:
            tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["PLANT", plant_crop]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
