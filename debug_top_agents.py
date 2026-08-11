"""Debug top agents: track money, actions, and farm state over time."""
import sys
sys.path.insert(0, "agents")
from kaggle_environments import make

def run_debug(agent_fn, agent_name, reset_fn=None):
    money_log = []
    errors = []
    
    def wrapped(obs):
        player = obs["player"]
        farm = obs["farms"][player]
        day = obs["day"]
        hour = obs.get("hour", 0)
        if hour == 0:
            money_log.append((day, farm.get("money", 0)))
        try:
            return agent_fn(obs)
        except Exception as e:
            import traceback
            errors.append(traceback.format_exc())
            return {"farmer": ["PASS"], "hands": [], "market": []}
    
    from agent_melon_test import test_melon_maxxer
    if reset_fn: reset_fn()
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": 0}, debug=False)
    env.run([wrapped, test_melon_maxxer])
    final = env.steps[-1]
    
    print(f"\n{'='*50}")
    print(f"{agent_name}: ${final[0].reward:.0f}  (melon: ${final[1].reward:.0f})")
    print("Money per day:")
    prev = 3000
    for day, money in money_log:
        delta = money - prev
        bar = "+" if delta >= 0 else ""
        print(f"  Day {day:2d}: ${money:7.0f}  ({bar}{delta:.0f})")
        prev = money
    if errors:
        print(f"  ERRORS: {len(errors)}")
        print(errors[0][:300])

