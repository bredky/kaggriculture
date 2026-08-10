"""
Patch all agent files to:
1. Add _hand_action helper function
2. Replace "hands": [] in the main return with computed hand actions
"""
import os
import re

HAND_FUNC = '''
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

'''

agents_dir = "/Users/kyransinha/kaggriculture/agents"
patched = 0
skipped = 0

for fname in sorted(os.listdir(agents_dir)):
    if not (fname.startswith("agent_") and fname.endswith(".py")):
        continue
    path = os.path.join(agents_dir, fname)
    with open(path) as f:
        src = f.read()

    # Skip if already patched
    if "_hand_action" in src:
        skipped += 1
        continue

    # Add hand function after _find_tiles definition
    insert_after = "    return result\n"
    idx = src.find(insert_after)
    if idx == -1:
        # Try alternate pattern
        insert_after = "    return tiles\n"
        idx = src.find(insert_after)
    if idx == -1:
        print(f"SKIP {fname}: can't find _find_tiles end")
        skipped += 1
        continue
    idx += len(insert_after)
    src = src[:idx] + HAND_FUNC + src[idx:]

    # Replace "hands": [] in the MAIN return (not the except fallback which has "market": [])
    # Main returns have market_actions variable; except returns have []
    src = re.sub(
        r'"hands": \[\], "market": (market_actions)',
        r'"hands": [_hand_action(hx, hy, farm["tiles"], seeds, day) for hx, hy in farm.get("hands", [])], "market": \1',
        src
    )

    with open(path, "w") as f:
        f.write(src)
    print(f"PATCHED {fname}")
    patched += 1

print(f"\nDone: {patched} patched, {skipped} skipped")
