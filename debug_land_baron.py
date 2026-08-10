"""Quick debug: run land_baron for a few days, track money."""
import sys, traceback
sys.path.insert(0, "agents")

from kaggle_environments import make
from agent_26_land_baron import land_baron
from agent_melon_test import test_melon_maxxer

errors = []
money_log = []

def wrapped_lb(obs):
    try:
        result = land_baron(obs)
        money = obs["farms"][obs["player"]]["money"]
        if obs.get("hour", 0) == 0:
            money_log.append((obs["day"], money))
        return result
    except Exception as e:
        errors.append(traceback.format_exc())
        return {"farmer": ["PASS"], "hands": [], "market": []}

env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=True)
env.run([wrapped_lb, test_melon_maxxer])

final = env.steps[-1]
print(f"land_baron: ${final[0].reward:.0f}   melon_test: ${final[1].reward:.0f}")
print("\nMoney at start of each day:")
for day, money in money_log:
    print(f"  Day {day:2d}: ${money:.0f}")
if errors:
    print(f"\nErrors: {len(errors)}")
    print(errors[0])
