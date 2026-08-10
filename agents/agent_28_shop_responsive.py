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


def shop_responsive(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        prices = obs["market"]["prices"]
        market_actions = []

        shops = obs.get("town", {}).get("unlocked_shops", [])

        # Compute demand scores
        def demand_score(crop):
            score = 1
            for shop in shops:
                if crop.lower() in shop.lower():
                    score += 2
            return score

        crop_scores = {c: demand_score(c) for c in ["WHEAT", "CARROT", "MELON", "STRAWBERRY", "TOMATO"]}
        best_crop = max(crop_scores, key=crop_scores.get)

        # Restrict late-game planting for melon/strawberry
        if day > 18 and best_crop in ("MELON", "STRAWBERRY"):
            # Fall back to next best
            remaining = {c: s for c, s in crop_scores.items() if c not in ("MELON", "STRAWBERRY")}
            best_crop = max(remaining, key=remaining.get) if remaining else "WHEAT"

        s = _state.setdefault(player, {"init": False})

        all_tiles = _find_tiles(farm)
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        # Initial plant day 0: 10 wheat + 5 carrot
        if not s["init"]:
            market_actions.append(["BUY_SEED", "WHEAT", 10])
            market_actions.append(["BUY_SEED", "CARROT", 5])
            market_actions.append(["HIRE"])
            s["init"] = True
        else:
            if obs.get("hour", 0) == 0:
                market_actions.append(["HIRE"])
            # Buy best_crop seeds for empty slots
            if seeds.get(best_crop, 0) < len(empty_tiles) + 2:
                need = len(empty_tiles) + 2 - seeds.get(best_crop, 0)
                market_actions.append(["BUY_SEED", best_crop, need])

        # Sell all harvested goods immediately
        for crop in ["WHEAT", "CARROT", "MELON", "STRAWBERRY", "TOMATO"]:
            if shed.get(crop, 0) > 0:
                market_actions.append(["SELL", crop, shed[crop]])

        # Determine planting crop (depends on what's planted vs day)
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        carrot_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "CARROT")

        def choose_plant_crop():
            if day == 0:
                if wheat_count < 10:
                    return "WHEAT"
                elif carrot_count < 5:
                    return "CARROT"
            return best_crop

        plant_crop = choose_plant_crop()

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
        elif empty_tiles and seeds.get(plant_crop, 0) > 0:
            tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["PLANT", plant_crop]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
