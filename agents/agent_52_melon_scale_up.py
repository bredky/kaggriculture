"""
Melon Scale-Up — maximum heuristic from replays.

Key lessons from replay analysis:
- nearest_task_greedy earns steady $1,400/day from day 11 with 10 melons + 1 hand
- It naturally staggers planting (walks to each tile individually) → continuous income
- 4 hands compete on the same tiles → cluster on same plots → mostly watering, barely harvesting
- The farm has 12 plantable tiles; nearest_task_greedy only uses 10

Strategy:
- Hire 1 hand at hour 0 (same as nearest_task_greedy, proven to work)
- Scale melon target from 10 → 12 (fills all farmable tiles, +20% output)
- Keep wheat at 3 tiles for early/fallback income
- Sell up to 6 melons/turn when price >= 120 (vs 4 in original) for faster cash collection
- Otherwise identical priority queue to nearest_task_greedy
"""

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
    all_t = [(x, y, t) for y, row in enumerate(tiles_2d) for x, t in enumerate(row)]
    water = [(x, y, t) for x, y, t in all_t
             if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    harvest = [(x, y, t) for x, y, t in all_t
               if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0
               and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    empty = [(x, y) for x, y, t in all_t if t is None]
    melon_count = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "MELON")
    wheat_count = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "WHEAT")

    if water:
        tx, ty, _ = min(water, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if harvest:
        tx, ty, _ = min(harvest, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
        if tx == hx and ty == hy: return ["HARVEST"]
        return [_step_toward(hx, hy, tx, ty)]
    for crop in ["MELON", "WHEAT"]:
        if crop == "MELON" and melon_count < 12 and seeds.get("MELON", 0) > 0 and empty:
            tx, ty = min(empty, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
            if tx == hx and ty == hy: return ["PLANT", "MELON"]
            return [_step_toward(hx, hy, tx, ty)]
        if crop == "WHEAT" and wheat_count < 3 and seeds.get("WHEAT", 0) > 0 and empty:
            tx, ty = min(empty, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
            if tx == hx and ty == hy: return ["PLANT", "WHEAT"]
            return [_step_toward(hx, hy, tx, ty)]
    return ["PASS"]


def melon_scale_up(obs):
    try:
        player = obs["player"]
        farm   = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds  = obs["private"]["seeds"]
        shed   = obs["private"]["shed"]
        day    = obs["day"]
        hour   = obs.get("hour", 0)
        prices = obs["market"]["prices"]

        MELON_TARGET = 12
        WHEAT_TARGET = 3

        market_actions = []

        all_tiles   = _find_tiles(farm)
        melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # ── Hire 1 hand at hour 0 each day (Fibonacci resets → costs $1/day) ──
        if hour == 0:
            market_actions.append(["HIRE"])

        # ── Buy seeds ────────────────────────────────────────────────────────────
        melon_have = melon_count + seeds.get("MELON", 0)
        if melon_have < MELON_TARGET:
            market_actions.append(["BUY_SEED", "MELON", MELON_TARGET - melon_have])

        wheat_have = wheat_count + seeds.get("WHEAT", 0)
        if wheat_have < WHEAT_TARGET:
            market_actions.append(["BUY_SEED", "WHEAT", WHEAT_TARGET - wheat_have])

        # ── Sell ─────────────────────────────────────────────────────────────────
        melon_price = prices.get("MELON", 120)

        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        melon_shed = shed.get("MELON", 0)
        if melon_shed > 0:
            if day >= 27:
                market_actions.append(["SELL", "MELON", melon_shed])
            elif melon_price >= 120:
                # Sell up to 6 per turn (vs 4 in nearest_task_greedy) for faster cash
                market_actions.append(["SELL", "MELON", min(6, melon_shed)])

        # ── Farmer: identical priority queue to nearest_task_greedy ──────────────
        candidates = []
        for x, y, t in all_tiles:
            dist = abs(x - fx) + abs(y - fy)
            if t is None:
                if melon_count < MELON_TARGET and seeds.get("MELON", 0) > 0:
                    candidates.append((3, dist, x, y, ("PLANT", "MELON")))
                elif wheat_count < WHEAT_TARGET and seeds.get("WHEAT", 0) > 0:
                    candidates.append((3, dist, x, y, ("PLANT", "WHEAT")))
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                crop    = t.get("crop", "")
                consec  = t.get("consecutive_unwatered", 0)
                yield_u = t.get("yield_units", 0)
                age     = day - t.get("planted_day", 0)
                watered = t.get("watered_today", False)
                max_yld = 6 if crop == "MELON" else 4

                if consec >= 1:
                    candidates.append((0, dist, x, y, ("WATER",)))
                elif yield_u >= max_yld:
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
            best   = candidates[0]
            bx, by = best[2], best[3]
            bact   = best[4]
            if bx == fx and by == fy:
                farmer_action = list(bact)
            else:
                farmer_action = [_step_toward(fx, fy, bx, by)]

        hand_actions = [
            _hand_action(hx, hy, farm["tiles"], seeds, day)
            for hx, hy in farm.get("hands", [])
        ]

        return {"farmer": farmer_action, "hands": hand_actions, "market": market_actions}

    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
