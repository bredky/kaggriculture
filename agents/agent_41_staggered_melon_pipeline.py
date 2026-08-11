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


def staggered_melon_pipeline(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        market_actions = []

        s = _state.setdefault(player, {"waves_planted": set()})

        all_tiles = _find_tiles(farm)
        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        # Wave scheduling: wave N planted on day N*3
        # After day 21: stop planting melon, use wheat
        wave_schedule = {0: 0, 1: 3, 2: 6, 3: 9}
        active_waves = {w for w, d in wave_schedule.items() if d <= day <= 21}
        pending_waves = active_waves - s["waves_planted"]

        # Each wave = 4 melon seeds (increased from 3)
        seeds_for_wave = 4
        for wave in sorted(pending_waves):
            target_melon = min(16, (len(s["waves_planted"]) + 1) * seeds_for_wave)
            if seeds.get("MELON", 0) + melon_count < target_melon:
                need = target_melon - melon_count - seeds.get("MELON", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "MELON", need])
            s["waves_planted"].add(wave)

        # After day 21, fill with wheat
        use_wheat = day > 21
        if use_wheat or len(empty_tiles) > melon_count:
            if seeds.get("WHEAT", 0) + wheat_count < 10:
                need = 10 - wheat_count - seeds.get("WHEAT", 0)
                if need > 0:
                    market_actions.append(["BUY_SEED", "WHEAT", need])

        # Sell
        if shed.get("MELON", 0) > 0:
            market_actions.append(["SELL", "MELON", min(6, shed["MELON"])])
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        # Farmer
        water_urgent = [(x, y, t) for x, y, t in all_tiles
                        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest_ready = [(x, y, t) for x, y, t in all_tiles
                         if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

        target_melon_total = min(16, len(s["waves_planted"]) * 4)
        plant_crop = None
        if day <= 21 and melon_count < target_melon_total and seeds.get("MELON", 0) > 0:
            plant_crop = "MELON"
        elif seeds.get("WHEAT", 0) > 0:
            plant_crop = "WHEAT"

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
        elif empty_tiles and plant_crop:
            tx, ty = min(empty_tiles, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                farmer_action = ["PLANT", plant_crop]
            else:
                farmer_action = [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
