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



def _shed_adjacent(fx, fy):
    return (fx, fy) in {(4, 4), (5, 4), (4, 5), (5, 5)}

def _animal_setup(fx, fy, all_tiles, farm, inv, shed, animal, structure):
    """Returns farmer action for placing animals, or None if done."""
    cur_tile = farm["tiles"][fy][fx] if 0 <= fy < len(farm["tiles"]) and 0 <= fx < len(farm["tiles"][fy]) else None
    has_inv = inv.get(animal, 0) > 0
    has_shed = shed.get(animal, 0) > 0
    structures = [(x, y, t) for x, y, t in all_tiles
                  if isinstance(t, dict) and t.get("kind") == structure]
    unoccupied = [(x, y, t) for x, y, t in structures if "animal" not in t]
    occupied = [(x, y, t) for x, y, t in structures if "animal" in t]

    if has_inv:
        # Place animal: find or build structure
        if unoccupied:
            tx, ty, _ = min(unoccupied, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            if tx == fx and ty == fy:
                return ["PLACE", animal]
            return [_step_toward(fx, fy, tx, ty)]
        if cur_tile is None:
            return ["BUILD_COOP"] if structure == "COOP" else ["BUILD_PASTURE"]
        empty = [(x, y) for x, y, t in all_tiles if t is None]
        if empty:
            tx, ty = min(empty, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
            return [_step_toward(fx, fy, tx, ty)]

    if has_shed:
        if _shed_adjacent(fx, fy):
            return ["PICKUP", animal, 1]
        return [_step_toward(fx, fy, 4, 4)]

    if occupied:
        return None  # animals placed, proceed to feeding logic

    return None

def _animal_care(fx, fy, all_tiles, farm, inv, structure):
    """Handle FEED/CARE/HARVEST/COLLECT for occupied structures."""
    occupied = [(x, y, t) for x, y, t in all_tiles
                if isinstance(t, dict) and t.get("kind") == structure and "animal" in t]
    if not occupied:
        return None
    cur_tile = farm["tiles"][fy][fx] if 0 <= fy < len(farm["tiles"]) and 0 <= fx < len(farm["tiles"][fy]) else None
    if isinstance(cur_tile, dict) and "animal" in cur_tile:
        wheat_inv = inv.get("WHEAT", 0)
        if not cur_tile.get("fed_today", False) and wheat_inv > 0:
            return ["FEED"]
        if not cur_tile.get("cared_today", False):
            return ["CARE"]
        if cur_tile.get("yield_units", 0) > 0:
            return ["HARVEST"]
        if cur_tile.get("fertilizer_available", False):
            return ["COLLECT_FERTILIZER"]
    # Need to get wheat from shed first for feeding
    needs_feed = [(x, y, t) for x, y, t in occupied if not t.get("fed_today", False)]
    if needs_feed and inv.get("WHEAT", 0) == 0:
        if _shed_adjacent(fx, fy):
            return ["PICKUP", "WHEAT", len(needs_feed)]
        return [_step_toward(fx, fy, 4, 4)]
    if occupied:
        tx, ty, _ = min(occupied, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
        if tx != fx or ty != fy:
            return [_step_toward(fx, fy, tx, ty)]
    return None


def adaptive_income(obs):
    try:
        player = obs["player"]
        farm = obs["farms"][player]
        fx, fy = farm["farmer"]
        seeds = obs["private"]["seeds"]
        shed = obs["private"]["shed"]
        day = obs["day"]
        money = farm.get("money", 0)
        market_actions = []
        all_tiles = _find_tiles(farm)

        s = _state.setdefault(player, {"geese_bought": False, "extra_geese_bought": False})

        if not s["geese_bought"]:
            market_actions.append(["BUY_ANIMAL", "GOOSE", 4])
            s["geese_bought"] = True

        if money > 2000 and not s["extra_geese_bought"]:
            market_actions.append(["BUY_ANIMAL", "GOOSE", 2])
            s["extra_geese_bought"] = True

        melon_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "MELON")
        wheat_count = sum(1 for x, y, t in all_tiles if isinstance(t, dict) and t.get("crop") == "WHEAT")
        empty_tiles = [(x, y) for x, y, t in all_tiles if t is None]

        # Bank check
        low_bank = money < 500

        if not low_bank:
            # Phase-based seed buying
            if day < 10:
                # Phase 1: wheat
                if seeds.get("WHEAT", 0) + wheat_count < 5:
                    need = 5 - wheat_count - seeds.get("WHEAT", 0)
                    if need > 0:
                        market_actions.append(["BUY_SEED", "WHEAT", need])
            elif day <= 20:
                # Phase 2: melon
                if day < 25 and melon_count < 6:
                    if seeds.get("MELON", 0) + melon_count < 6:
                        need = 6 - melon_count - seeds.get("MELON", 0)
                        if need > 0:
                            market_actions.append(["BUY_SEED", "MELON", need])
                if seeds.get("WHEAT", 0) + wheat_count < 5:
                    need = 5 - wheat_count - seeds.get("WHEAT", 0)
                    if need > 0:
                        market_actions.append(["BUY_SEED", "WHEAT", need])
                # Phase 3: wheat only
                if seeds.get("WHEAT", 0) + wheat_count < 5:
                    need = 5 - wheat_count - seeds.get("WHEAT", 0)
                    if need > 0:
                        market_actions.append(["BUY_SEED", "WHEAT", need])

        # Sell logic
        if shed.get("EGG", 0) > 0:
            market_actions.append(["SELL", "EGG", shed["EGG"]])
        if shed.get("WHEAT", 0) > 0:
            market_actions.append(["SELL", "WHEAT", shed["WHEAT"]])

        melon_shed = shed.get("MELON", 0)
        if low_bank:
            if melon_shed > 0:
                market_actions.append(["SELL", "MELON", melon_shed])
        elif 10 <= day <= 20 and melon_shed > 0:
            market_actions.append(["SELL", "MELON", min(4, melon_shed)])

        # Farmer
        cur_tile = farm["tiles"][fy][fx] if 0 <= fy < len(farm["tiles"]) and 0 <= fx < len(farm["tiles"][fy]) else None

        water_urgent = [(x, y, t) for x, y, t in all_tiles
                        if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
        harvest_ready = [(x, y, t) for x, y, t in all_tiles
                         if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0 and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]

    
        farmer_action = ["PASS"]

        # Animal lifecycle: highest priority
        inv = obs["private"]["inventories"][0]
        _asetup = _animal_setup(fx, fy, all_tiles, farm, inv, shed, "GOOSE", "COOP")
        if _asetup is not None:
            farmer_action = _asetup
        else:
            _acare = _animal_care(fx, fy, all_tiles, farm, inv, "COOP")
            if _acare is not None:
                farmer_action = _acare

        # Regular farming: water > harvest > plant wheat > BUILD structure
        if farmer_action == ["PASS"]:
            water = [(x, y, t) for x, y, t in all_tiles
                     if isinstance(t, dict) and t.get("kind") == "PLANT" and not t.get("watered_today", False)]
            harvest = [(x, y, t) for x, y, t in all_tiles
                       if isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("yield_units", 0) > 0
                       and (t.get("crop") != "MELON" or (day - t.get("planted_day", 0)) >= 10)]
            empty = [(x, y) for x, y, t in all_tiles if t is None]
            if water:
                tx, ty, _ = min(water, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                farmer_action = ["WATER"] if tx == fx and ty == fy else [_step_toward(fx, fy, tx, ty)]
            elif harvest:
                tx, ty, _ = min(harvest, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                farmer_action = ["HARVEST"] if tx == fx and ty == fy else [_step_toward(fx, fy, tx, ty)]
            elif empty and seeds.get("WHEAT", 0) > 0:
                tx, ty = min(empty, key=lambda c: abs(c[0]-fx)+abs(c[1]-fy))
                farmer_action = ["PLANT", "WHEAT"] if tx == fx and ty == fy else [_step_toward(fx, fy, tx, ty)]

        return {"farmer": farmer_action, "hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": market_actions}
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
