"""
Agent 55 — NE Land + 4 Hands with HARVEST-FIRST priority
The quad_hand fix: with 20 tiles, hands should have enough space to spread.
Key change: hands check HARVEST before WATER — so once melons ripen, income
flows immediately instead of hands watering forever. Trade-off is some missed
waterings, but the stagger from a bigger farm covers that.
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

def _hand_action_harvest_first(hx, hy, tiles_2d, seeds, day, melon_target, wheat_target):
    """Harvest-first variant: ripe crops take priority over watering.
    This prevents the 'always watering, never harvesting' deadlock."""
    all_t = [(x, y, t) for y, row in enumerate(tiles_2d) for x, t in enumerate(row)]
    # Ripe harvest (high priority — income now)
    harvest_ripe = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and t.get("yield_units", 0) >= 3
                    and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    # Emergency water (dying plants)
    water_urgent = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and t.get("consecutive_unwatered", 0) >= 1]
    # Regular harvest (yield >= 1, ripe)
    harvest_any  = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and t.get("yield_units", 0) > 0
                    and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    # Normal water
    water_normal = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and not t.get("watered_today", False)]
    empty = [(x, y) for x, y, t in all_t if t is None]
    mc = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "MELON")
    wc = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "WHEAT")

    if harvest_ripe:
        tx, ty, _ = min(harvest_ripe, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["HARVEST"]
        return [_step_toward(hx, hy, tx, ty)]
    if water_urgent:
        tx, ty, _ = min(water_urgent, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if harvest_any:
        tx, ty, _ = min(harvest_any, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["HARVEST"]
        return [_step_toward(hx, hy, tx, ty)]
    if water_normal:
        tx, ty, _ = min(water_normal, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if mc < melon_target and seeds.get("MELON", 0) > 0 and empty:
        tx, ty = min(empty, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["PLANT", "MELON"]
        return [_step_toward(hx, hy, tx, ty)]
    if wc < wheat_target and seeds.get("WHEAT", 0) > 0 and empty:
        tx, ty = min(empty, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["PLANT", "WHEAT"]
        return [_step_toward(hx, hy, tx, ty)]
    return ["PASS"]

def ne_four_hands_harvest_priority(obs):
    try:
        player = obs["player"]
        farm   = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds  = obs["private"]["seeds"]
        shed   = obs["private"]["shed"]
        day    = obs["day"]
        prices = obs["market"]["prices"]
        money  = farm.get("money", 0) or 0

        s = _state.setdefault(player, {"land_ne": False})
        market_actions = []

        all_tiles   = _find_tiles(farm)
        melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        MELON_TARGET = 18
        WHEAT_TARGET = 3

        # Buy NE land asap
        if not s["land_ne"] and money >= 1000:
            market_actions.append(["BUY_LAND"])
            s["land_ne"] = True

        # 4 hands at hour 0 ($7/day)
        if obs.get("hour", 0) == 0:
            for _ in range(4):
                market_actions.append(["HIRE"])

        # Seeds — conservative buy (keep $500 buffer)
        spendable = max(0, money - 500)
        melon_have = melon_count + seeds.get("MELON", 0)
        if melon_have < MELON_TARGET:
            buy = min(MELON_TARGET - melon_have, max(0, int(spendable // 90)))
            if buy > 0:
                market_actions.append(["BUY_SEED", "MELON", buy])
                spendable -= buy * 90
        wheat_have = wheat_count + seeds.get("WHEAT", 0)
        if wheat_have < WHEAT_TARGET and spendable > 50:
            market_actions.append(["BUY_SEED", "WHEAT", WHEAT_TARGET - wheat_have])

        # Sell
        melon_price = prices.get("MELON", 120)
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])
        melon_shed = shed.get("MELON", 0)
        if melon_shed > 0:
            if day >= 27:
                market_actions.append(["SELL", "MELON", melon_shed])
            elif melon_price >= 120:
                market_actions.append(["SELL", "MELON", min(8, melon_shed)])

        # Farmer: same proven priority queue
        candidates = []
        for x, y, t in all_tiles:
            dist = abs(x-fx)+abs(y-fy)
            if t is None:
                if melon_count < MELON_TARGET and seeds.get("MELON", 0) > 0:
                    candidates.append((3, dist, x, y, ("PLANT", "MELON")))
                elif wheat_count < WHEAT_TARGET and seeds.get("WHEAT", 0) > 0:
                    candidates.append((3, dist, x, y, ("PLANT", "WHEAT")))
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                crop=t.get("crop",""); consec=t.get("consecutive_unwatered",0)
                yield_u=t.get("yield_units",0); age=day-t.get("planted_day",0)
                watered=t.get("watered_today",False); max_yld=6 if crop=="MELON" else 4
                if consec>=1:               candidates.append((0,dist,x,y,("WATER",)))
                elif yield_u>=max_yld:      candidates.append((1,dist,x,y,("HARVEST",)))
                elif crop=="MELON" and 6<=age<=10 and not watered: candidates.append((2,dist,x,y,("WATER",)))
                elif yield_u>=2:            candidates.append((4,dist,x,y,("HARVEST",)))
                elif not watered:           candidates.append((5,dist,x,y,("WATER",)))

        farmer_action = ["PASS"]
        if candidates:
            candidates.sort(key=lambda c:(c[0],c[1]))
            best=candidates[0]; bx,by,bact=best[2],best[3],best[4]
            if bx==fx and by==fy: farmer_action=list(bact)
            else: farmer_action=[_step_toward(fx,fy,bx,by)]

        return {"farmer": farmer_action,
                "hands": [_hand_action_harvest_first(hx,hy,farm["tiles"],seeds,day,MELON_TARGET,WHEAT_TARGET) for hx,hy in farm.get("hands",[])],
                "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
