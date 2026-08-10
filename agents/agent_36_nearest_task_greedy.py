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


def nearest_task_greedy(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        prices = obs["market"]["prices"]
        market_actions = []

        if obs.get("hour", 0) == 0:
            market_actions.append(["HIRE"])

        all_tiles = _find_tiles(farm)
        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # Buy seeds
        if seeds.get("MELON", 0) + melon_count < 10:
            need = 10 - melon_count - seeds.get("MELON", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "MELON", need])
        if seeds.get("WHEAT", 0) + wheat_count < 5:
            need = 5 - wheat_count - seeds.get("WHEAT", 0)
            if need > 0:
                market_actions.append(["BUY_SEED", "WHEAT", need])

        # Sell
        melon_price = prices.get("MELON", 120)
        if shed.get("MELON", 0) > 0 and melon_price >= 120:
            market_actions.append(["SELL", "MELON", min(4, shed["MELON"])])
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        # Build candidate list with priority classes
        # 0=WATER urgent, 1=HARVEST max_yield, 2=WATER bonus window, 3=PLANT empty+seed, 4=HARVEST any yield, 5=WATER otherwise
        candidates = []

        for x, y, t in all_tiles:
            dist = abs(x - fx) + abs(y - fy)
            if t is None:
                crop_to_plant = None
                if melon_count < 10 and seeds.get("MELON", 0) > 0:
                    crop_to_plant = "MELON"
                elif wheat_count < 5 and seeds.get("WHEAT", 0) > 0:
                    crop_to_plant = "WHEAT"
                if crop_to_plant:
                    candidates.append((3, dist, x, y, ("PLANT", crop_to_plant)))
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                crop = t.get("crop", "")
                consec = t.get("consecutive_unwatered", 0)
                yield_u = t.get("yield_units", 0)
                age = day - t.get("planted_day", 0)
                watered = t.get("watered_today", False)
                max_yield = 6 if crop == "MELON" else 4

                if consec >= 1:
                    candidates.append((0, dist, x, y, ("WATER",)))
                elif yield_u >= max_yield:
                    candidates.append((1, dist, x, y, ("HARVEST",)))
                elif crop == "MELON" and 6 <= age <= 10 and not watered:
                    candidates.append((2, dist, x, y, ("WATER",)))
                elif yield_u >= 2:
                    candidates.append((4, dist, x, y, ("HARVEST",)))
                elif not watered:
                    candidates.append((5, dist, x, y, ("WATER",)))

        farmer_action = ["PASS"]

        if candidates:
            candidates.sort(key=lambda c: (c[0], c[1]))
            best = candidates[0]
            bx, by, baction = best[2], best[3], best[4]
            if bx == fx and by == fy:
                farmer_action = list(baction)
            else:
                farmer_action = [_step_toward(fx, fy, bx, by)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
