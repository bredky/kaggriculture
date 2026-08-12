"""
Run top-5 agents vs test_melon_maxxer.
Saves full episode replays as JSON.
Prints a detailed per-day + per-action analysis to verify:
  - HIRE is firing and hands accumulate
  - Hands are doing real work (WATER / HARVEST / PLANT)
  - Sell timing and crop counts per day
"""

import sys
import importlib
import json
import os
import traceback

sys.path.insert(0, "agents")

from kaggle_environments import make

TOP5 = [
    ("agent_36_nearest_task_greedy",  "nearest_task_greedy"),
    ("agent_40_opponent_money_watcher","opponent_money_watcher"),
    ("agent_50_melon_bail_out",        "melon_bail_out"),
    ("agent_34_price_momentum_seller", "price_momentum_seller"),
    ("agent_15_early_bird_melon",      "early_bird_melon"),
]

MELON_MODULE = "agent_melon_test"
MELON_FN     = "test_melon_maxxer"
SEEDS        = [0, 1, 2]

os.makedirs("replays", exist_ok=True)


# ── helpers ────────────────────────────────────────────────────────────────────

def default(obj):
    """JSON fallback for non-serialisable objects."""
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def reset_state(module):
    if hasattr(module, "_state"):
        module._state.clear()


def run_and_save(fn_a, fn_b, mod_a, mod_b, seed, label):
    """Run one game; return (steps, reward_a, reward_b)."""
    reset_state(mod_a)
    reset_state(mod_b)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([fn_a, fn_b])
    steps = env.steps
    ra = steps[-1][0]["reward"]
    rb = steps[-1][1]["reward"]

    # Save replay
    path = f"replays/{label}_seed{seed}.json"
    with open(path, "w") as f:
        json.dump(steps, f, default=default, indent=None)
    print(f"  [saved] {path}")

    return steps, ra, rb


# ── per-step analysis ──────────────────────────────────────────────────────────

def crop_counts(tiles_2d):
    counts = {}
    for row in tiles_2d:
        for tile in row:
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                c = tile.get("crop", "?")
                counts[c] = counts.get(c, 0) + 1
    return counts


def analyse_replay(steps, agent_name, seed, pidx=0):
    print(f"\n{'='*72}")
    print(f"  AGENT: {agent_name}  |  SEED: {seed}  |  Player {pidx}")
    print(f"{'='*72}")

    prev_day = -1
    day_data = {}   # day → aggregated info

    hire_events   = []  # (day, hour)
    sell_events   = []  # (day, hour, crop, qty, price_approx)
    hand_actions  = {}  # day → list of unique hand actions seen

    for step_num, step in enumerate(steps):
        if pidx >= len(step):
            continue
        ps  = step[pidx]
        obs = ps.get("observation") or {}
        act = ps.get("action") or {}

        if not obs:
            continue

        day   = obs.get("day", 0)
        hour  = obs.get("hour", 0)
        farms = obs.get("farms", [])
        farm  = farms[pidx] if pidx < len(farms) else {}
        money = farm.get("money", 0) or 0
        hands = farm.get("hands", [])  # list of (x,y) positions
        tiles = farm.get("tiles", [])
        shed  = (obs.get("private") or {}).get("shed", {})
        prices = (obs.get("market") or {}).get("prices", {})

        n_hands = len(hands)

        if day != prev_day:
            day_data[day] = {
                "money_start": money,
                "money_end":   money,
                "hands":       n_hands,
                "crops_start": crop_counts(tiles),
            }
            prev_day = day
        else:
            day_data[day]["money_end"] = money
            day_data[day]["hands"] = max(day_data[day]["hands"], n_hands)

        # --- Inspect actions ---
        market = act.get("market") or []
        for m in (market or []):
            if not m:
                continue
            cmd = m[0] if isinstance(m, list) else m
            if cmd == "HIRE":
                hire_events.append((day, hour))
            elif cmd == "SELL":
                crop = m[1] if len(m) > 1 else "?"
                qty  = m[2] if len(m) > 2 else 0
                sell_events.append((day, hour, crop, qty))

        # --- Hand actions ---
        hand_acts = act.get("hands") or []
        for ha in hand_acts:
            if ha and ha[0] not in ("PASS",):
                day_data[day].setdefault("hand_cmds", []).append(ha[0])

    # ── print per-day table ────────────────────────────────────────────────────
    print(f"\n  {'Day':>4} {'$Start':>8} {'$End':>8} {'Gain':>7} {'Hands':>6}  Crops")
    print(f"  {'-'*4} {'-'*8} {'-'*8} {'-'*7} {'-'*6}  {'-'*30}")
    for day in sorted(day_data):
        d     = day_data[day]
        ms    = d["money_start"]
        me    = d["money_end"]
        gain  = me - ms
        nh    = d["hands"]
        crops = d["crops_start"]
        crop_str = "  ".join(f"{k}:{v}" for k, v in sorted(crops.items()))
        print(f"  {day:>4} {ms:>8.0f} {me:>8.0f} {gain:>+7.0f} {nh:>6}  {crop_str}")

    # ── hire events ───────────────────────────────────────────────────────────
    print(f"\n  HIRE events: {len(hire_events)}")
    if hire_events:
        by_day = {}
        for d, h in hire_events:
            by_day.setdefault(d, []).append(h)
        for d in sorted(by_day)[:10]:
            print(f"    Day {d:2d}  hours: {by_day[d]}")
        if len(by_day) > 10:
            print(f"    ... and {len(by_day)-10} more days")

    # ── sell summary ─────────────────────────────────────────────────────────
    melon_sells = [(d, h, q) for d, h, c, q in sell_events if c == "MELON"]
    wheat_sells = [(d, h, q) for d, h, c, q in sell_events if c == "WHEAT"]
    total_melon = sum(q for _, _, q in melon_sells)
    total_wheat = sum(q for _, _, q in wheat_sells)
    print(f"\n  SELLS — Melon: {total_melon} units across {len(melon_sells)} transactions")
    print(f"          Wheat: {total_wheat} units across {len(wheat_sells)} transactions")

    # ── hand work summary ─────────────────────────────────────────────────────
    all_hand_cmds = []
    for d in day_data.values():
        all_hand_cmds.extend(d.get("hand_cmds", []))
    if all_hand_cmds:
        from collections import Counter
        cmd_counts = Counter(all_hand_cmds)
        print(f"\n  HAND actions (non-PASS): {dict(cmd_counts)}")
    else:
        print(f"\n  HAND actions: none (hands always PASS or no hands hired)")

    # ── final score ───────────────────────────────────────────────────────────
    last = steps[-1]
    ra = last[0]["reward"]
    rb = last[1]["reward"]
    winner = agent_name if ra > rb else "melon"
    print(f"\n  FINAL: {agent_name} ${ra:.0f}  vs  melon ${rb:.0f}  → {'WIN' if ra>rb else 'LOSS'}")

    return ra, rb


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    melon_mod = importlib.import_module(MELON_MODULE)
    melon_fn  = getattr(melon_mod, MELON_FN)

    summary = []

    for mod_name, fn_name in TOP5:
        try:
            mod = importlib.import_module(mod_name)
            fn  = getattr(mod, fn_name)
        except Exception as e:
            print(f"IMPORT ERROR {mod_name}: {e}")
            continue

        agent_scores = []
        melon_scores = []

        for seed in SEEDS:
            try:
                print(f"\nRunning {fn_name} vs melon (seed={seed})...")
                steps, ra, rb = run_and_save(fn, melon_fn, mod, melon_mod, seed, fn_name)
                agent_scores.append(ra)
                melon_scores.append(rb)
                analyse_replay(steps, fn_name, seed, pidx=0)
            except Exception:
                print(f"  ERROR seed={seed}:")
                traceback.print_exc()

        if agent_scores:
            avg_a = sum(agent_scores) / len(agent_scores)
            avg_m = sum(melon_scores) / len(melon_scores)
            wins  = sum(1 for a, m in zip(agent_scores, melon_scores) if a > m)
            summary.append((fn_name, wins, len(SEEDS), avg_a, avg_m))

    # ── overall summary ───────────────────────────────────────────────────────
    print(f"\n\n{'#'*72}")
    print("  SUMMARY")
    print(f"{'#'*72}")
    print(f"  {'Agent':<35} {'W/N':>5} {'Avg $agent':>12} {'Avg $melon':>12}")
    for fn_name, wins, n, avg_a, avg_m in summary:
        print(f"  {fn_name:<35} {wins}/{n:>3} {avg_a:>12.0f} {avg_m:>12.0f}")


if __name__ == "__main__":
    main()
