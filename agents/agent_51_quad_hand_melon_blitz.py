"""
Quad Hand Melon Blitz
- Hires 4 hands at hour 0 every day (cost $1+$1+$2+$3 = $7/day)
- Farmer + 4 hands = 5 workers covering the farm simultaneously
- Targets up to 20 melon plots + 3 wheat, buying only what we can afford
- Priority: water-urgent > harvest-maxed > water-bonus-window > harvest-any > plant > water-idle
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


def _hand_action(hx, hy, tiles_2d, seeds, day, melon_target, wheat_target):
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

    if melon_count < melon_target and seeds.get("MELON", 0) > 0 and empty:
        tx, ty = min(empty, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
        if tx == hx and ty == hy: return ["PLANT", "MELON"]
        return [_step_toward(hx, hy, tx, ty)]

    if wheat_count < wheat_target and seeds.get("WHEAT", 0) > 0 and empty:
        tx, ty = min(empty, key=lambda c: abs(c[0] - hx) + abs(c[1] - hy))
        if tx == hx and ty == hy: return ["PLANT", "WHEAT"]
        return [_step_toward(hx, hy, tx, ty)]

    return ["PASS"]


def quad_hand_melon_blitz(obs):
    try:
        player = obs["player"]
        farm   = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds  = obs["private"]["seeds"]
        shed   = obs["private"]["shed"]
        day    = obs["day"]
        prices = obs["market"]["prices"]
        money  = farm.get("money", 0) or 0

        s = _state.setdefault(player, {"_dbg_turn": 0})
        s["_dbg_turn"] += 1

        # ── DEBUG: print at start of each day (hour==0) to track money across 30 days ──
        hour_val = obs.get("hour", "MISSING")
        if hour_val == 0 or s["_dbg_turn"] <= 3:
            hands_val = farm.get("hands", [])
            melon_in_seeds = obs["private"]["seeds"].get("MELON", 0)
            melon_in_shed  = obs["private"]["shed"].get("MELON", 0)
            print(f"[DBG51 P{player} turn={s['_dbg_turn']} day={day} hour={hour_val}] "
                  f"money=${money} hands={len(hands_val)} seeds_melon={melon_in_seeds} shed_melon={melon_in_shed}")

        MELON_TARGET = 20
        WHEAT_TARGET = 3
        SEED_PRICE   = 90   # conservative per-seed cost estimate
        BUFFER       = 400  # keep this much cash in reserve

        market_actions = []

        all_tiles   = _find_tiles(farm)
        melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # ── Hire 4 hands at start of each day ───────────────────────────────────
        # Fibonacci resets daily: 1st=$1, 2nd=$1, 3rd=$2, 4th=$3 → total $7/day
        hire_fired = obs.get("hour", 0) == 0
        if hire_fired:
            for _ in range(4):
                market_actions.append(["HIRE"])
        if s["_dbg_turn"] <= 3:
            print(f"[DBG51 P{player} turn={s['_dbg_turn']}] hire_fired={hire_fired} market_so_far={market_actions}")

        # ── Buy seeds — only as many as we can afford ────────────────────────────
        spendable = max(0, money - BUFFER)

        melon_have = melon_count + seeds.get("MELON", 0)
        melon_need = MELON_TARGET - melon_have
        if melon_need > 0:
            can_afford = max(0, int(spendable // SEED_PRICE))
            buy = min(melon_need, can_afford)
            if buy > 0:
                market_actions.append(["BUY_SEED", "MELON", buy])
                spendable -= buy * SEED_PRICE

        wheat_have = wheat_count + seeds.get("WHEAT", 0)
        wheat_need = WHEAT_TARGET - wheat_have
        if wheat_need > 0 and spendable > SEED_PRICE * wheat_need:
            market_actions.append(["BUY_SEED", "WHEAT", wheat_need])

        # ── Sell ─────────────────────────────────────────────────────────────────
        melon_price = prices.get("MELON", 120)

        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        melon_shed = shed.get("MELON", 0)
        if melon_shed > 0:
            if day >= 27:
                market_actions.append(["SELL", "MELON", melon_shed])
            elif melon_price >= 120:
                # sell more aggressively with 5 workers producing faster
                market_actions.append(["SELL", "MELON", min(8, melon_shed)])

        # ── Farmer priority queue ────────────────────────────────────────────────
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

        # ── Hands ────────────────────────────────────────────────────────────────
        hand_actions = [
            _hand_action(hx, hy, farm["tiles"], seeds, day, MELON_TARGET, WHEAT_TARGET)
            for hx, hy in farm.get("hands", [])
        ]

        return {"farmer": farmer_action, "hands": hand_actions, "market": market_actions}

    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
