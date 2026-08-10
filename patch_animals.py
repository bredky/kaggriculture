"""
Fix animal agents: add PICKUP/BUILD/PLACE lifecycle to farmer action.
Injects a helper and rewrites the farmer_action block.
"""
import os
import re

ANIMAL_HELPER = '''
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

'''

# Map of agent file → (animal, structure) pairs
ANIMAL_AGENTS = {
    "agent_06_egg_factory.py": [("GOOSE", "COOP")],
    "agent_07_milk_machine.py": [("COW", "PASTURE")],
    "agent_08_wool_weaver.py": [("SHEEP", "PASTURE")],
    "agent_10_fertilizer_seller.py": [("GOOSE", "COOP")],
    "agent_16_goose_wheat_dual.py": [("GOOSE", "COOP")],
    "agent_21_goose_fertilizer_melon.py": [("GOOSE", "COOP")],
    "agent_22_cow_milk_drip.py": [("COW", "PASTURE")],
    "agent_24_sheep_wool_wheat.py": [("SHEEP", "PASTURE")],
    "agent_25_strawberry_egg_cafe.py": [("GOOSE", "COOP")],
    "agent_27_melon_goose_portfolio.py": [("GOOSE", "COOP")],
    "agent_32_adaptive_income.py": [("GOOSE", "COOP")],
    "agent_33_town_demand_predictor.py": [("COW", "PASTURE")],
    "agent_35_compound_goose_empire.py": [("GOOSE", "COOP")],
    "agent_38_wheat_egg_steady.py": [("GOOSE", "COOP")],
    "agent_45_fertilized_wheat_geese.py": [("GOOSE", "COOP")],
    "agent_48_goose_snowball.py": [("GOOSE", "COOP")],
}

agents_dir = "/Users/kyransinha/kaggriculture/agents"

for fname, animal_pairs in ANIMAL_AGENTS.items():
    path = os.path.join(agents_dir, fname)
    if not os.path.exists(path):
        print(f"MISSING: {fname}")
        continue
    
    with open(path) as f:
        src = f.read()
    
    if "_animal_setup" in src:
        print(f"SKIP {fname}: already patched")
        continue

    # Add helper after _hand_action function
    insert_after = "    return [\"PASS\"]\n\n"
    idx = src.find(insert_after)
    if idx == -1:
        insert_after = "    return [\"PASS\"]\n"
        idx = src.find(insert_after)
    if idx == -1:
        print(f"SKIP {fname}: can't find insertion point")
        continue
    idx += len(insert_after)
    src = src[:idx] + "\n" + ANIMAL_HELPER + src[idx:]

    # Now inject animal setup calls into farmer_action logic
    # Find the line "    farmer_action = [\"PASS\"]" and add setup code after it
    animal, structure = animal_pairs[0]
    
    inject_code = f'''
        # Animal lifecycle: PICKUP → BUILD → PLACE
        inv = obs["private"]["inventories"][0]
        _asetup = _animal_setup(fx, fy, all_tiles, farm, inv, shed, "{animal}", "{structure}")
        if _asetup is not None:
            farmer_action = _asetup
        else:
            _acare = _animal_care(fx, fy, all_tiles, farm, inv, "{structure}")
            if _acare is not None:
                farmer_action = _acare
            else:
'''

    # Find farmer_action = ["PASS"] and the if/elif block after it
    # Replace the whole farmer logic block with animal-aware version
    # Strategy: inject before the first "if" after "farmer_action = ["PASS"]"
    
    farmer_pass_pat = r'        farmer_action = \["PASS"\]\n\n'
    match = re.search(farmer_pass_pat, src)
    if not match:
        farmer_pass_pat = r'        farmer_action = \["PASS"\]\n'
        match = re.search(farmer_pass_pat, src)
    
    if match:
        end_pos = match.end()
        # Now indent the block after farmer_action = ["PASS"] by 4 extra spaces
        # Find end of the if/elif block (find the return statement)
        return_pat = r'\n        return \{'
        ret_match = re.search(return_pat, src[end_pos:])
        if ret_match:
            block_start = end_pos
            block_end = end_pos + ret_match.start()
            block = src[block_start:block_end]
            # Indent the block by 4 more spaces
            indented_block = "\n".join("    " + line if line.strip() else line 
                                       for line in block.split("\n"))
            # Build the new section
            new_section = inject_code + indented_block
            src = src[:block_start] + new_section + src[block_end:]
            print(f"PATCHED {fname}")
        else:
            print(f"SKIP {fname}: can't find return")
            continue
    else:
        print(f"SKIP {fname}: can't find farmer_action=PASS")
        continue

    with open(path, "w") as f:
        f.write(src)

print("Done")

# Fix the 4-space indent agents separately
import re

ANIMAL_AGENTS_4 = {
    "agent_06_egg_factory.py": ("GOOSE", "COOP"),
    "agent_07_milk_machine.py": ("COW", "PASTURE"),
    "agent_08_wool_weaver.py": ("SHEEP", "PASTURE"),
    "agent_10_fertilizer_seller.py": ("GOOSE", "COOP"),
    "agent_16_goose_wheat_dual.py": ("GOOSE", "COOP"),
}

for fname, (animal, structure) in ANIMAL_AGENTS_4.items():
    path = os.path.join(agents_dir, fname)
    with open(path) as f:
        src = f.read()
    if "_animal_setup" in src:
        print(f"SKIP {fname}: already patched")
        continue
    
    # Add helpers after _hand_action
    insert_after = "    return [\"PASS\"]\n\n"
    idx = src.find(insert_after)
    if idx == -1:
        insert_after = "    return [\"PASS\"]\n"
        idx = src.find(insert_after)
    if idx != -1:
        idx += len(insert_after)
        src = src[:idx] + "\n" + ANIMAL_HELPER + src[idx:]

    inject_code = f'''
        # Animal lifecycle: PICKUP → BUILD → PLACE
        inv = obs["private"]["inventories"][0]
        _asetup = _animal_setup(fx, fy, all_tiles, farm, inv, shed, "{animal}", "{structure}")
        if _asetup is not None:
            farmer_action = _asetup
        else:
            _acare = _animal_care(fx, fy, all_tiles, farm, inv, "{structure}")
            if _acare is not None:
                farmer_action = _acare
            else:
'''

    # 4-space indent version
    farmer_pass_pat = r'    farmer_action = \["PASS"\]\n\n'
    match = re.search(farmer_pass_pat, src)
    if not match:
        farmer_pass_pat = r'    farmer_action = \["PASS"\]\n'
        match = re.search(farmer_pass_pat, src)
    
    if match:
        end_pos = match.end()
        return_pat = r'\n    return \{'
        ret_match = re.search(return_pat, src[end_pos:])
        if ret_match:
            block_start = end_pos
            block_end = end_pos + ret_match.start()
            block = src[block_start:block_end]
            indented_block = "\n".join("    " + line if line.strip() else line 
                                       for line in block.split("\n"))
            new_section = inject_code + indented_block
            src = src[:block_start] + new_section + src[block_end:]
            print(f"PATCHED {fname}")
        else:
            print(f"SKIP {fname}: can't find return")
            continue
    else:
        print(f"SKIP {fname}: can't find farmer_action=PASS (4-space)")
        continue
    
    with open(path, "w") as f:
        f.write(src)

print("Done 4-space agents")
