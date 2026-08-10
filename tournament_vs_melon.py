"""
Tournament: every agent vs test_melon_maxxer
Runs each challenger as P0, melon_test as P1, then swapped — across N seeds.
"""

import sys
import importlib
import traceback
from kaggle_environments import make

sys.path.insert(0, "agents")

# ── agent registry ────────────────────────────────────────────────────────────
AGENTS = [
    ("agent_01_wheat_grinder",        "wheat_grinder"),
    ("agent_02_carrot_sprinter",      "carrot_sprinter"),
    ("agent_03_melon_baron",          "melon_baron"),
    ("agent_04_tomato_perennial",     "tomato_perennial"),
    ("agent_05_strawberry_hedge",     "strawberry_hedge"),
    ("agent_06_egg_factory",          "egg_factory"),
    ("agent_07_milk_machine",         "milk_machine"),
    ("agent_08_wool_weaver",          "wool_weaver"),
    ("agent_09_wheat_feeder",         "wheat_feeder"),
    ("agent_10_fertilizer_seller",    "fertilizer_seller"),
    ("agent_11_wheat_melon_alternator","wheat_melon_alternator"),
    ("agent_12_carrot_tomato_relay",  "carrot_tomato_relay"),
    ("agent_13_melon_strawberry_pair","melon_strawberry_pair"),
    ("agent_14_wheat_flood_timing",   "wheat_flood_timing"),
    ("agent_15_early_bird_melon",     "early_bird_melon"),
    ("agent_16_goose_wheat_dual",     "goose_wheat_dual"),
    ("agent_17_tomato_fertilizer_max","tomato_fertilizer_max"),
    ("agent_18_ne_quadrant_expander", "ne_quadrant_expander"),
    ("agent_19_late_strawberry_spike","late_strawberry_spike"),
    ("agent_20_carrot_wheat_watcher", "carrot_wheat_watcher"),
    ("agent_21_goose_fertilizer_melon","goose_fertilizer_melon"),
    ("agent_22_cow_milk_drip",        "cow_milk_drip"),
    ("agent_23_three_crop_rotation",  "three_crop_rotation"),
    ("agent_24_sheep_wool_wheat",     "sheep_wool_wheat"),
    ("agent_25_strawberry_egg_cafe",  "strawberry_egg_cafe"),
    ("agent_26_land_baron",           "land_baron"),
    ("agent_27_melon_goose_portfolio","melon_goose_portfolio"),
    ("agent_28_shop_responsive",      "shop_responsive"),
    ("agent_29_fertilizer_arbitrageur","fertilizer_arbitrageur"),
    ("agent_30_opponent_mirror",      "opponent_mirror"),
    ("agent_31_melon_price_sniper",   "melon_price_sniper"),
    ("agent_32_adaptive_income",      "adaptive_income"),
    ("agent_33_town_demand_predictor","town_demand_predictor"),
    ("agent_34_price_momentum_seller","price_momentum_seller"),
    ("agent_35_compound_goose_empire","compound_goose_empire"),
    ("agent_36_nearest_task_greedy",  "nearest_task_greedy"),
    ("agent_37_dual_quadrant_melon",  "dual_quadrant_melon"),
    ("agent_38_wheat_egg_steady",     "wheat_egg_steady"),
    ("agent_39_late_cash_surge",      "late_cash_surge"),
    ("agent_40_opponent_money_watcher","opponent_money_watcher"),
    ("agent_41_staggered_melon_pipeline","staggered_melon_pipeline"),
    ("agent_42_carrot_rush_to_melon", "carrot_rush_to_melon"),
    ("agent_43_four_hand_wheat_blitz","four_hand_wheat_blitz"),
    ("agent_44_melon_micro_seller",   "melon_micro_seller"),
    ("agent_45_fertilized_wheat_geese","fertilized_wheat_geese"),
    ("agent_46_day6_melon_planter",   "day6_melon_planter"),
    ("agent_47_tomato_two_wave",      "tomato_two_wave"),
    ("agent_48_goose_snowball",       "goose_snowball"),
    ("agent_49_wheat_tomato_split",   "wheat_tomato_split"),
    ("agent_50_melon_bail_out",       "melon_bail_out"),
    # prototype agents
    ("agent_melon",                   "melon_maxxer"),
    ("agent_strawberry",              "strawberry_maxxer"),
    ("agent_tomato",                  "tomato_maxxer"),
]

MELON_MODULE = "agent_melon_test"
MELON_FN     = "test_melon_maxxer"
SEEDS        = [0]


def reset_state(module):
    """Clear the per-player _state dict that many agents keep between calls."""
    if hasattr(module, "_state"):
        module._state.clear()


def run_game(fn_a, fn_b, mod_a, mod_b, seed):
    """Run one game. Returns (reward_a, reward_b)."""
    reset_state(mod_a)
    reset_state(mod_b)
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
    env.run([fn_a, fn_b])
    final = env.steps[-1]
    return final[0].reward, final[1].reward


def main():
    melon_mod = importlib.import_module(MELON_MODULE)
    melon_fn  = getattr(melon_mod, MELON_FN)

    results = []

    header = f"{'Agent':<35} {'W':>4} {'L':>4} {'T':>4} {'Avg $challenger':>16} {'Avg $melon':>12}"
    print(header)
    print("-" * len(header))

    for mod_name, fn_name in AGENTS:
        try:
            mod = importlib.import_module(mod_name)
            fn  = getattr(mod, fn_name)
        except Exception as e:
            print(f"  IMPORT ERROR {mod_name}: {e}")
            continue

        wins = losses = ties = 0
        challenger_rewards = []
        melon_rewards      = []

        for seed in SEEDS:
            try:
                ra, rb = run_game(fn, melon_fn, mod, melon_mod, seed)
                challenger_rewards.append(ra)
                melon_rewards.append(rb)
                if ra > rb:   wins   += 1
                elif ra < rb: losses += 1
                else:         ties   += 1
            except Exception:
                print(f"  GAME ERROR {mod_name} seed={seed}:")
                traceback.print_exc()

        n = len(challenger_rewards)
        avg_c = sum(challenger_rewards) / n if n else 0
        avg_m = sum(melon_rewards) / n if n else 0

        row = f"{fn_name:<35} {wins:>4} {losses:>4} {ties:>4} {avg_c:>16.0f} {avg_m:>12.0f}"
        print(row)
        results.append((fn_name, wins, losses, ties, avg_c, avg_m))

    print("\n── Top challengers by win count ──")
    results.sort(key=lambda r: (-r[1], -r[4]))
    for rank, (name, w, l, t, ac, am) in enumerate(results[:10], 1):
        print(f"  {rank:2}. {name:<35} {w}W {l}L {t}T  avg ${ac:.0f} vs melon ${am:.0f}")


if __name__ == "__main__":
    main()
