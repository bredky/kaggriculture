"""
Quick round-robin: top historical agents + newly fixed agents.
3 seeds each pair, prints win/loss leaderboard.
"""
import sys, os, importlib, itertools
sys.path.insert(0, os.path.dirname(__file__))

from kaggle_environments import make

AGENTS = {
    "36_nearest_task_greedy":        ("agents.agent_36_nearest_task_greedy",        "nearest_task_greedy"),
    "47_price_momentum_seller":      ("agents.agent_47_price_momentum_seller",      "price_momentum_seller"),
    "49_opponent_money_watcher":     ("agents.agent_49_opponent_money_watcher",     "opponent_money_watcher"),
    "50_melon_bail_out":             ("agents.agent_50_melon_bail_out",             "melon_bail_out"),
    "06_early_bird_melon":           ("agents.agent_06_early_bird_melon",           "early_bird_melon"),
    "53_ne_melon_one_hand":          ("agents.agent_53_ne_melon_one_hand",          "ne_melon_one_hand"),
    "54_ne_sw_two_hands":            ("agents.agent_54_ne_sw_two_hands",            "ne_sw_two_hands"),
    "55_ne_four_hands_harvest_pri":  ("agents.agent_55_ne_four_hands_harvest_priority", "ne_four_hands_harvest_priority"),
    "57_max_heuristic":              ("agents.agent_57_max_heuristic",              "max_heuristic"),
}

SEEDS = [0, 42, 99]

def load(mod_path, fn_name):
    mod = importlib.import_module(mod_path)
    fn  = getattr(mod, fn_name)
    def agent(obs, cfg):
        return fn(obs)
    return agent

def run_game(a0, a1, seed):
    env = make("meijeran_kaggriculture", debug=False)
    env.reset(seed=seed)
    env.run([a0, a1])
    scores = env.state[-1]
    r0 = scores[0].reward or 0
    r1 = scores[1].reward or 0
    return r0, r1

agents = {name: load(mod, fn) for name, (mod, fn) in AGENTS.items()}
names  = list(agents.keys())

wins   = {n: 0 for n in names}
total  = {n: 0.0 for n in names}
games  = {n: 0 for n in names}

pairs = list(itertools.combinations(names, 2))
print(f"Running {len(pairs)} pairs × {len(SEEDS)} seeds = {len(pairs)*len(SEEDS)} games\n")

for i, (a, b) in enumerate(pairs):
    for seed in SEEDS:
        r0, r1 = run_game(agents[a], agents[b], seed)
        total[a] += r0; total[b] += r1
        games[a] += 1;  games[b] += 1
        if r0 > r1: wins[a] += 1
        elif r1 > r0: wins[b] += 1
    print(f"  [{i+1}/{len(pairs)}] {a} vs {b}  →  {total[a]/games[a]:.0f} / {total[b]/games[b]:.0f} avg so far")

print("\n=== LEADERBOARD ===")
ranked = sorted(names, key=lambda n: (-wins[n], -total[n]))
for rank, n in enumerate(ranked, 1):
    avg = total[n] / games[n] if games[n] else 0
    print(f"  {rank}. {n:<40}  wins={wins[n]}  avg=${avg:,.0f}")
