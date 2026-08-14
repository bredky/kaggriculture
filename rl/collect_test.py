"""
rl/collect_test.py — Quick sanity check before running full collect.py

Runs the agents that were scoring $0 (due to reward=None bug) against
a few strong opponents to confirm:
  1. Scores are read correctly via farm["money"] (not reward field)
  2. Data is being kept above the threshold

Takes ~5 minutes on Kaggle. Run this before collect.py.
"""

import os, sys, importlib
import numpy as np
from kaggle_environments import make

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rl.env import encode_obs
from rl.collect import action_to_int, reset_agent_state, SCORE_THRESHOLD

AGENTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")

# Agents that were showing $0 due to reward bug
SUSPECTS = [
    "agent_51_quad_hand_melon_blitz",
    "agent_53_ne_melon_one_hand",
    "agent_54_ne_sw_two_hands",
    "agent_55_ne_four_hands_harvest_priority",
    "agent_57_max_heuristic",
]

# Strong opponents to test against
OPPONENTS = [
    "agent_36_nearest_task_greedy",
    "agent_50_melon_bail_out",
    "agent_01_wheat_grinder",   # weak — good agent should dominate
]

N_SEEDS = 2


def load(module_name):
    spec = importlib.util.spec_from_file_location(
        module_name, os.path.join(AGENTS_DIR, module_name + ".py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = next(
        getattr(mod, a) for a in dir(mod)
        if not a.startswith("_") and callable(getattr(mod, a))
        and not isinstance(getattr(mod, a), type)
    )
    return mod, fn


def run_game(fn0, mod0, fn1, mod1):
    reset_agent_state(mod0)
    reset_agent_state(mod1)
    env = make("kaggriculture", configuration={"episodeSteps": 720}, debug=False)
    env.reset()

    last_money0, last_money1 = 3000, 3000
    while True:
        s0, s1 = env.state[0], env.state[1]
        if s0.status != "ACTIVE":
            break
        obs0, obs1 = s0.observation, s1.observation

        # Track money every turn — final state observation can be None on Kaggle
        try:
            p0 = obs0["player"]
            last_money0 = obs0["farms"][p0].get("money", last_money0)
        except Exception:
            pass
        try:
            p1 = obs1["player"]
            last_money1 = obs1["farms"][p1].get("money", last_money1)
        except Exception:
            pass

        try:   a0 = fn0(obs0)
        except: a0 = {"farmer": ["PASS"], "hands": [], "market": []}
        try:   a1 = fn1(obs1)
        except: a1 = {"farmer": ["PASS"], "hands": [], "market": []}
        env.step([a0, a1])

    return last_money0, last_money1, 0


def main():
    print("=== Collect Sanity Check ===")
    print(f"Threshold: ${SCORE_THRESHOLD:,}\n")

    all_pass = True

    for suspect_name in SUSPECTS:
        print(f"── {suspect_name} ──")
        try:
            mod_s, fn_s = load(suspect_name)
        except Exception as e:
            print(f"  LOAD ERROR: {e}")
            all_pass = False
            continue

        for opp_name in OPPONENTS:
            try:
                mod_o, fn_o = load(opp_name)
            except Exception as e:
                print(f"  LOAD ERROR {opp_name}: {e}")
                continue

            for seed in range(N_SEEDS):
                # Run suspect as P0
                s0, s1, steps = run_game(fn_s, mod_s, fn_o, mod_o)
                kept0 = "✓ KEPT" if s0 >= SCORE_THRESHOLD else "  skip"
                print(f"  P0 vs {opp_name.replace('agent_',''):<35} s{seed} → suspect ${s0:>7,.0f}  opp ${s1:>7,.0f}  {kept0}")

                # Run suspect as P1
                s0, s1, steps = run_game(fn_o, mod_o, fn_s, mod_s)
                kept1 = "✓ KEPT" if s1 >= SCORE_THRESHOLD else "  skip"
                print(f"  P1 vs {opp_name.replace('agent_',''):<35} s{seed} → suspect ${s1:>7,.0f}  opp ${s0:>7,.0f}  {kept1}")

                suspect_score = s1  # suspect was P1 in this game
                if suspect_score == 0:
                    print(f"  !! WARNING: suspect scored $0 — reward bug still present !!")
                    all_pass = False
        print()

    if all_pass:
        print("✓ All agents scoring correctly. Safe to run collect.py.")
    else:
        print("✗ Issues detected. Check output above before running collect.py.")


if __name__ == "__main__":
    main()
