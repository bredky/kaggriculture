"""Quick test: run agents 51,53,54,55,57 in step-by-step mode to confirm $0 bug."""
import sys, importlib
from kaggle_environments import make

sys.path.insert(0, "agents")

BROKEN = [
    ("agent_51_quad_hand_melon_blitz",           "quad_hand_melon_blitz"),
    ("agent_53_ne_melon_one_hand",               "ne_melon_one_hand"),
    ("agent_54_ne_sw_two_hands",                 "ne_sw_two_hands"),
    ("agent_55_ne_four_hands_harvest_priority",  "ne_four_hands_harvest_priority"),
    ("agent_57_max_heuristic",                   "max_heuristic"),
]

def run_stepwise(fn):
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.reset()
    while True:
        s = env.state[0]
        if s.status != "ACTIVE":
            break
        obs = s.observation
        try:
            a = fn(obs)
        except Exception:
            a = {"farmer": ["PASS"], "hands": [], "market": []}
        env.step([a, {"farmer": ["PASS"], "hands": [], "market": []}])
    return env.steps[-1][0].reward or 0

for mod_name, fn_name in BROKEN:
    mod = importlib.import_module(mod_name)
    fn  = getattr(mod, fn_name)
    score = run_stepwise(fn)
    print(f"{fn_name:<45} step-by-step score: ${score:.0f}")
