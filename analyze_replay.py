"""
Kaggriculture replay analyzer.
Usage: python analyze_replay.py [replay.json]
"""
import json
import sys
from collections import defaultdict


def analyze(path="replay.json"):
    with open(path) as f:
        data = json.load(f)

    steps = data["steps"]
    n_players = len(steps[0])
    print(f"Replay: {len(steps)} steps, {n_players} players\n")

    # Per-player state tracking
    prev_money = [None] * n_players
    prev_plants = [0] * n_players
    prev_shed = [defaultdict(int) for _ in range(n_players)]
    total_harvested = [defaultdict(int) for _ in range(n_players)]
    total_sold_revenue = [0] * n_players
    events = [[] for _ in range(n_players)]

    for i, step in enumerate(steps):
        for pid in range(n_players):
            s = step[pid]
            obs = s.get("observation", {})
            if not obs:
                continue

            day = obs.get("day", 0)
            hour = obs.get("hour", 0)
            farms = obs.get("farms", [])
            if not farms or pid >= len(farms):
                continue

            farm = farms[pid]
            money = farm.get("money", 0)
            tiles = farm.get("tiles", [])
            private = obs.get("private", {}) or {}
            shed = private.get("shed", {}) or {}
            seeds = private.get("seeds", {}) or {}
            market = (obs.get("market", {}) or {}).get("prices", {})

            # Count plants per crop
            plant_counts = defaultdict(int)
            for row in tiles:
                for t in row:
                    if isinstance(t, dict) and t.get("kind") == "PLANT":
                        plant_counts[t["crop"]] += 1
            total_plants = sum(plant_counts.values())

            # Detect harvest (shed increases)
            for crop, qty in shed.items():
                prev_qty = prev_shed[pid][crop]
                if qty > prev_qty:
                    gained = qty - prev_qty
                    total_harvested[pid][crop] += gained
                    events[pid].append(
                        f"  Day {day:2d} h{hour} (step {i:3d}): HARVESTED {gained} {crop} → shed={qty}"
                    )

            # Detect sale (money jumps and shed decreases)
            if prev_money[pid] is not None:
                delta = money - prev_money[pid]
                if delta > 100:
                    total_sold_revenue[pid] += delta
                    events[pid].append(
                        f"  Day {day:2d} h{hour} (step {i:3d}): SOLD     → +${delta:.0f}  (money ${prev_money[pid]:.0f} → ${money:.0f})"
                    )

            # Detect planting
            if total_plants > prev_plants[pid]:
                new = total_plants - prev_plants[pid]
                events[pid].append(
                    f"  Day {day:2d} h{hour} (step {i:3d}): PLANTED  {new} (total on-farm={total_plants}) seeds_left={seeds}"
                )

            prev_money[pid] = money
            prev_plants[pid] = total_plants
            for crop, qty in shed.items():
                prev_shed[pid][crop] = qty

    # Print per-player summary
    for pid in range(n_players):
        final_step = steps[-1][pid]
        final_money = final_step.get("reward", 0)
        print(f"{'='*60}")
        print(f"Player {pid} — Final: ${final_money:.0f}")
        print(f"  Total harvested: {dict(total_harvested[pid])}")
        print(f"  Total sell revenue: ${total_sold_revenue[pid]:.0f}")
        print("  Key events:")
        for e in events[pid]:
            print(e)
        print()

    # Head-to-head comparison
    print("=" * 60)
    print("HEAD-TO-HEAD")
    rewards = [steps[-1][pid].get("reward", 0) for pid in range(n_players)]
    winner = rewards.index(max(rewards))
    for pid in range(n_players):
        delta = rewards[pid] - rewards[1 - pid] if n_players == 2 else 0
        sign = "+" if delta >= 0 else ""
        print(f"  P{pid}: ${rewards[pid]:.0f}  ({sign}{delta:.0f} vs opponent)")
    print(f"  Winner: P{winner}")

    # Market snapshot at first sell (step ~313)
    sell_steps = [i for i, step in enumerate(steps)
                  if any(step[pid].get("observation", {}).get("private", {}) or {} for pid in range(n_players))]
    # Find first sell event from events list
    for pid in range(n_players):
        for e in events[pid]:
            if "SOLD" in e:
                step_num = int(e.split("step")[1].split(")")[0].strip())
                obs = steps[step_num][pid].get("observation", {}) or {}
                prices = (obs.get("market", {}) or {}).get("prices", {})
                if prices:
                    print(f"\n  Market at first P{pid} sale (step {step_num}): MELON=${prices.get('MELON', '?')}")
                break


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "replay.json"
    analyze(path)
