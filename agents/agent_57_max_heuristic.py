"""
Agent 57 — MAX HEURISTIC: Everything combined.

Synthesis of every lesson from replay analysis:
- NE land ($1000) bought on day 0 immediately
- SW land ($2000) bought once first melons sell (day 5-8)
- 4 hands hired daily — now with enough tiles they won't cluster
- Melon target: 16 after NE, 24 after SW
- Hands use harvest-first when melons are ripe (yield >= 3), emergency water
  otherwise — breaking the 'always watering, never harvesting' deadlock
- Sell timing: opponent-aware (opponent_money_watcher) + price momentum
  (price_momentum_seller) + price crash bail-out (melon_bail_out) combined
- Sell up to 8 melons per turn for fast cash collection
- Bail to wheat if melon price < 80 for 3 consecutive days
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

def _hand_action(hx, hy, tiles_2d, seeds, day, melon_target, wheat_target, bail_out):
    all_t = [(x, y, t) for y, row in enumerate(tiles_2d) for x, t in enumerate(row)]
    mc = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "MELON")
    wc = sum(1 for _, _, t in all_t if isinstance(t, dict) and t.get("crop") == "WHEAT")
    empty = [(x, y) for x, y, t in all_t if t is None]

    # Ripe harvest — income first (yield >= 3 = well ripened melon or near max wheat)
    harvest_ripe = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and t.get("yield_units", 0) >= 3
                    and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    # Emergency — dying plants
    water_urgent = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and t.get("consecutive_unwatered", 0) >= 1]
    # Any harvestable (yield > 0, ripe)
    harvest_any  = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and t.get("yield_units", 0) > 0
                    and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
    # Normal water
    water_normal = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("kind") == "PLANT"
                    and not t.get("watered_today", False)]

    if bail_out:
        # During bail: DIG immature melons, plant wheat instead
        immature = [(x, y, t) for x, y, t in all_t if isinstance(t, dict) and t.get("crop") == "MELON"
                    and t.get("yield_units", 0) == 0 and (day - t.get("planted_day", 0)) < 10]
        if immature:
            tx, ty, _ = min(immature, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
            if tx == hx and ty == hy: return ["DIG"]
            return [_step_toward(hx, hy, tx, ty)]
        if harvest_any:
            tx, ty, _ = min(harvest_any, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
            if tx == hx and ty == hy: return ["HARVEST"]
            return [_step_toward(hx, hy, tx, ty)]
        if water_normal:
            tx, ty, _ = min(water_normal, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
            if tx == hx and ty == hy: return ["WATER"]
            return [_step_toward(hx, hy, tx, ty)]
        if wc < wheat_target and seeds.get("WHEAT", 0) > 0 and empty:
            tx, ty = min(empty, key=lambda c: abs(c[0]-hx)+abs(c[1]-hy))
            if tx == hx and ty == hy: return ["PLANT", "WHEAT"]
            return [_step_toward(hx, hy, tx, ty)]
        return ["PASS"]

    # Normal mode: harvest-first once ripe, emergency water, then balance
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


def max_heuristic(obs):
    try:
        player = obs["player"]
        farms  = obs["farms"]
        farm   = farms[player]
        fx, fy = farm["farmer"]
        seeds  = obs["private"]["seeds"]
        shed   = obs["private"]["shed"]
        day    = obs["day"]
        prices = obs["market"]["prices"]
        money  = farm.get("money", 0) or 0
        opp    = 1 - player
        opp_money = farms[opp].get("money", 0) if opp < len(farms) else 0

        s = _state.setdefault(player, {
            "land_ne": False, "land_sw": False,
            "price_history": [], "last_price_day": -1,
            "low_price_days": 0, "bail_out": False,
            "own_hist": [], "opp_hist": [], "last_track_day": -1,
        })
        last_hire_day = s.get("last_hire_day", -1)

        # ── Track price + money once per day ────────────────────────────────────
        if day != s["last_price_day"]:
            p = prices.get("MELON", 150)
            s["price_history"].append(p)
            if len(s["price_history"]) > 6: s["price_history"] = s["price_history"][-6:]
            s["low_price_days"] = s["low_price_days"] + 1 if p < 80 else 0
            if s["low_price_days"] >= 3: s["bail_out"] = True
            s["last_price_day"] = day

        if day != s["last_track_day"]:
            s["own_hist"].append(money)
            s["opp_hist"].append(opp_money)
            if len(s["own_hist"]) > 3: s["own_hist"] = s["own_hist"][-3:]
            if len(s["opp_hist"]) > 3: s["opp_hist"] = s["opp_hist"][-3:]
            s["last_track_day"] = day

        # Price momentum
        hist = s["price_history"]
        momentum = (hist[-1] - hist[-4]) / 3 if len(hist) >= 4 else 0

        # Opponent delta (3-day)
        own_delta = (s["own_hist"][-1] - s["own_hist"][0]) if len(s["own_hist"]) >= 2 else 0
        opp_delta = (s["opp_hist"][-1] - s["opp_hist"][0]) if len(s["opp_hist"]) >= 2 else 0

        market_actions = []
        all_tiles   = _find_tiles(farm)
        melon_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for _, _, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")

        # ── Land: NE day 0, SW once first batch sells (money > $3k) ────────────
        if not s["land_ne"] and money >= 1000:
            market_actions.append(["BUY_LAND"])
            s["land_ne"] = True
        if s["land_ne"] and not s["land_sw"] and money >= 3000 and day >= 5:
            market_actions.append(["BUY_LAND"])
            s["land_sw"] = True

        # Melon target scales with land
        if s["land_sw"]:
            MELON_TARGET = 24
        elif s["land_ne"]:
            MELON_TARGET = 16
        else:
            MELON_TARGET = 10
        WHEAT_TARGET = 3 if not s["bail_out"] else 16

        # ── Hire 4 hands at hour 0 ───────────────────────────────────────────────
        if day != last_hire_day:
            for _ in range(4):
                market_actions.append(["HIRE"])
            s["last_hire_day"] = day

        # ── Seeds — keep $500 buffer ─────────────────────────────────────────────
        spendable = max(0, money - 500)
        if not s["bail_out"]:
            melon_have = melon_count + seeds.get("MELON", 0)
            if melon_have < MELON_TARGET:
                buy = min(MELON_TARGET - melon_have, max(0, int(spendable // 90)))
                if buy > 0:
                    market_actions.append(["BUY_SEED", "MELON", buy])
                    spendable -= buy * 90
        wheat_have = wheat_count + seeds.get("WHEAT", 0)
        if wheat_have < WHEAT_TARGET and spendable > 50:
            buy_w = min(WHEAT_TARGET - wheat_have, max(0, int(spendable // 30)))
            if buy_w > 0:
                market_actions.append(["BUY_SEED", "WHEAT", buy_w])

        # ── Sell — combined momentum + opponent awareness ─────────────────────────
        melon_price = prices.get("MELON", 120)
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])
        if s["bail_out"] and shed.get("MELON", 0) > 0:
            market_actions.append(["SELL", "MELON", shed["MELON"]])
        elif shed.get("MELON", 0) > 0:
            melon_shed = shed["MELON"]
            if day >= 27:
                market_actions.append(["SELL", "MELON", melon_shed])
            elif melon_price >= 120:
                # Opponent-aware sell cap
                if opp_delta > own_delta + 500:
                    sell_cap = 4   # opponent pulling ahead — sell less, stockpile
                elif opp_delta < own_delta - 500:
                    sell_cap = 8   # we're winning — dump more
                else:
                    sell_cap = 6   # neutral
                # Momentum boost/reduction
                if momentum >= 5:
                    sell_cap = min(8, sell_cap + 2)   # price rising — sell more now
                elif momentum <= -5:
                    sell_cap = max(2, sell_cap - 2)   # price falling — hold
                market_actions.append(["SELL", "MELON", min(sell_cap, melon_shed)])

        # ── Farmer priority queue (proven nearest_task_greedy system) ────────────
        candidates = []
        for x, y, t in all_tiles:
            dist = abs(x-fx)+abs(y-fy)
            if t is None:
                if not s["bail_out"] and melon_count < MELON_TARGET and seeds.get("MELON", 0) > 0:
                    candidates.append((3, dist, x, y, ("PLANT", "MELON")))
                elif wheat_count < WHEAT_TARGET and seeds.get("WHEAT", 0) > 0:
                    candidates.append((3, dist, x, y, ("PLANT", "WHEAT")))
            elif isinstance(t, dict) and t.get("kind") == "PLANT":
                crop=t.get("crop",""); consec=t.get("consecutive_unwatered",0)
                yield_u=t.get("yield_units",0); age=day-t.get("planted_day",0)
                watered=t.get("watered_today",False); max_yld=6 if crop=="MELON" else 4
                # Bail out: dig immature melons
                if s["bail_out"] and crop=="MELON" and yield_u==0 and age<10:
                    candidates.append((0, dist, x, y, ("DIG",)))
                elif consec>=1:               candidates.append((0,dist,x,y,("WATER",)))
                elif yield_u>=max_yld:        candidates.append((1,dist,x,y,("HARVEST",)))
                elif crop=="MELON" and 6<=age<=10 and not watered: candidates.append((2,dist,x,y,("WATER",)))
                elif yield_u>=2:              candidates.append((4,dist,x,y,("HARVEST",)))
                elif not watered:             candidates.append((5,dist,x,y,("WATER",)))

        farmer_action = ["PASS"]
        if candidates:
            candidates.sort(key=lambda c:(c[0],c[1]))
            best=candidates[0]; bx,by,bact=best[2],best[3],best[4]
            if bx==fx and by==fy: farmer_action=list(bact)
            else: farmer_action=[_step_toward(fx,fy,bx,by)]

        return {"farmer": farmer_action,
                "hands": [_hand_action(hx,hy,farm["tiles"],seeds,day,MELON_TARGET,WHEAT_TARGET,s["bail_out"])
                          for hx,hy in farm.get("hands",[])],
                "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
