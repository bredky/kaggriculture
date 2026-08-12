"""
Agent 53 — NE Land + 1 Hand, 14 Melons
Simplest land expansion: buy NE ($1000) on day 0 to unlock ~8 extra tiles,
keep proven 1-hand nearest-task-greedy approach, scale melon target to 14.
Baseline: does land buying alone beat $25k?
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
    water   = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
    harvest = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
               and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    empty   = [(x, y) for x, y, t in all_t if t is None]
    mc = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "MELON")
    wc = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "WHEAT")
    if water:
        tx, ty, _ = min(water,   key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["WATER"]
        return [_step_toward(hx, hy, tx, ty)]
    if harvest:
        tx, ty, _ = min(harvest, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
        if tx == hx and ty == hy: return ["HARVEST"]
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

def ne_melon_one_hand(obs):
    try:
        player = obs["player"]
        farm   = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds  = obs["private"]["seeds"]
        shed   = obs["private"]["shed"]
        day    = obs["day"]
        prices = obs["market"]["prices"]
        money  = farm.get("money", 0) or 0

        MELON_TARGET = 14
        WHEAT_TARGET = 3

        s = _state.setdefault(player, {"land_ne": False})
        last_hire_day = s.get("last_hire_day", -1)
        market_actions = []

        all_tiles   = _find_tiles(farm)
        melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # Buy NE land asap (day 0 if possible)
        if not s["land_ne"] and money >= 1000:
            market_actions.append(["BUY_LAND"])
            s["land_ne"] = True

        # 1 hand at hour 0
        if day != last_hire_day:
            market_actions.append(["HIRE"])
            s["last_hire_day"] = day

        # Seeds — only buy what we can afford (keep $300 buffer)
        spendable = max(0, money - 300)
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
                market_actions.append(["SELL", "MELON", min(5, melon_shed)])

        # Farmer priority queue (nearest_task_greedy style)
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
                "hands": [_hand_action(hx,hy,farm["tiles"],seeds,day,MELON_TARGET,WHEAT_TARGET) for hx,hy in farm.get("hands",[])],
                "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
