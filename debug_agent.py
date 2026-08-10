"""Quick diagnostic: run one game with debug=True to surface agent errors."""
import sys, traceback
sys.path.insert(0, "agents")

from kaggle_environments import make
from agent_01_wheat_grinder import wheat_grinder
from agent_melon_test import test_melon_maxxer

errors = []

def wrapped_wheat(obs):
    try:
        return wheat_grinder(obs)
    except Exception as e:
        errors.append(traceback.format_exc())
        return {"farmer": ["PASS"], "hands": [], "market": []}

env = make("kaggriculture", configuration={"episodeSteps": 24, "seed": 0}, debug=True)
env.run([wrapped_wheat, test_melon_maxxer])

final = env.steps[-1]
print(f"wheat_grinder: ${final[0].reward:.0f}   melon_test: ${final[1].reward:.0f}")

if errors:
    print(f"\nFirst error ({len(errors)} total errors across {24} turns):")
    print(errors[0])
else:
    print("\nNo errors — agent ran cleanly.")
