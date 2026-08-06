# Reinforcement Learning for Kaggriculture: A Conceptual Guide

## Introduction

Kaggriculture is a two-player farming competition game running on the kaggle-environments framework. Two agents compete over 30 days (720 turns total, 24 turns/day) to accumulate the most money by planting crops, watering them, harvesting, and selling on a dynamic market. This document explains, at a conceptual level, how to frame and build a reinforcement learning agent for this game from scratch — from state representation through to a full training pipeline.

---

## 1. Game Framing as an RL Problem

### The Basic MDP Structure

Kaggriculture maps cleanly onto a Markov Decision Process (MDP):

- **State**: the full observable game situation at a given turn
- **Action**: what the farmer does this turn (movement, farm action) plus any market orders
- **Reward**: some signal derived from outcomes (see Section 4)
- **Transition**: the game engine steps forward one turn, resolving both players' actions simultaneously

The episode terminates after exactly 720 turns. The win condition is final bank balance, not a running score — so the "true" reward is delivered in one lump at the very end.

### What Makes This Hard for RL

Several properties combine to make Kaggriculture a genuinely difficult RL problem:

**Partial observability**: Your opponent's shed contents are hidden. You can see their farm tiles (so you know what they planted), but not how much harvested produce they are holding or when they plan to sell. This matters enormously for market timing.

**Long time horizon**: 720 turns is a long episode. Actions taken on turn 1 (buying a melon seed, watering immediately) have consequences on turns 250–300 when the melon is harvested. Credit assignment — figuring out which early actions were responsible for a good or bad outcome — is very difficult over this span.

**Sparse and delayed reward**: The final reward is one number at turn 720. If the agent only receives reward at the end, it must somehow connect 720 steps of decisions to a single outcome signal.

**Combinatorial action space**: Each turn combines a movement/farm-action choice with a list of up to 10 market orders. The joint action space is enormous.

**Stochastic environment**: Weed spawns are random (0.5% per empty tile per day), and which town shops unlock (and when) is randomised each episode. This injects noise into episode outcomes that makes learning harder.

---

## 2. State Representation

What you feed to the neural network matters enormously. The network can only learn what it can see. Here is a breakdown of everything the observation contains and how to encode it.

### Farm Grid (10×10)

The farm is a 10×10 grid where each tile is one of: empty, locked, plant (with multiple sub-fields), weed, or animal structure. This is the richest and most spatially structured part of the observation.

The cleanest encoding for a neural network is a **multi-channel tensor** of shape `(C, 10, 10)`, where each channel captures one attribute:

- Channel 0: tile type (empty=0, locked=1, weed=2, plant=3, animal structure=4)
- Channel 1: crop type (0 for no crop, then one integer per crop type: WHEAT=1, CARROT=2, TOMATO=3, STRAWBERRY=4, MELON=5)
- Channel 2: age of plant (days since planting, normalised by 30)
- Channel 3: watered today (binary)
- Channel 4: current yield units (normalised by max yield ~6)
- Channel 5: consecutive unwatered days (0, 1, or 2)
- Channel 6: fertilised flag (binary)
- Channel 7: farmer position (1 at farmer's tile, 0 elsewhere)

That gives 8 channels over the 10×10 grid, for **800 values** covering the player's own farm. The opponent's farm is also visible (tiles and farmer position, but no shed), adding roughly another 500 values.

A **CNN** is the natural architecture to process this grid — it can learn spatial patterns like "the farmer is one step away from an unwatered melon" without needing to hard-code positions. A 2–3 layer CNN with small (3×3) kernels is a reasonable starting point.

An alternative is to simply **flatten all tile features into a long vector** and use an MLP. This works but loses spatial inductive bias — the network has to learn from scratch that tile (4,3) is adjacent to (4,4), which a CNN gets for free.

### Non-Spatial Features

Everything outside the grid should be concatenated into a flat vector and merged with the CNN's output:

- **Day** (0–29, normalised to [0,1]): ~1 value
- **Hour** (0–23, normalised): ~1 value
- **Money** (own): log-scaled, ~1 value
- **Opponent money**: log-scaled, ~1 value
- **Seeds held** (per crop type, 5 values)
- **Shed contents** (per item type, ~9 values normalised by shed cap 100)
- **Market prices** (per product, ~9 values normalised by base price): e.g. current melon price / 250
- **Market inventory** (per product, ~9 values): how many units are on the market
- **Unlocked quadrants** (4 binary values)
- **Town unlocked shops** (8 binary values, one per possible shop)

Total non-spatial features: roughly **45–60 values**.

### Dimensionality Summary

| Component | Approximate Size |
|---|---|
| Own farm grid (8 channels × 10×10) | 800 values |
| Opponent farm grid (5 channels × 10×10) | 500 values |
| Scalars (day, hour, money, seeds, shed, market, town) | ~60 values |
| **Total raw input** | **~1360 values** |

After the CNN processes the grid portions, the flattened feature map is perhaps 256–512 values, which gets concatenated with the scalar features before the policy/value heads.

---

## 3. Action Space

### The Full Discrete Action Space

On each turn, the agent must output two things independently:

**Farmer action** (one of ~10 options):
- Movement: NORTH, SOUTH, EAST, WEST, PASS
- Farm actions on the current tile: PLANT (+ crop type), WATER, HARVEST, DIG, FERTILIZE
- Shed actions: PICKUP (+ item), DROP

**Market orders** (an ordered list of up to 10 orders per turn, each drawn from):
- BUY_SEED (crop, quantity)
- SELL (item, quantity)
- BUY_PRODUCT (WHEAT or FERTILIZER, quantity)
- BUY_ANIMAL (animal type, quantity)
- HIRE
- BUY_LAND

### How to Handle This in Practice

The cleanest RL framing is to define a **flat discrete action space** for the farmer action (roughly 15–20 distinct choices) and a **separate small discrete action space** for a single "priority market order" per turn. Most of the time the market orders are simple and repetitive (buy a seed if you have fewer than a target plant count; sell if price is good), so a small fixed vocabulary suffices.

Alternatively, treat the market as a **rule-based sub-policy** handled deterministically while RL focuses on spatial/movement decisions. This is a pragmatic simplification that dramatically reduces the action space without sacrificing much — market decisions are relatively simple compared to navigation and timing.

### Action Masking

Many actions are invalid in a given state, and allowing the agent to "attempt" them wastes capacity. **Action masking** zeroes out the logits for invalid actions before the softmax, so the policy never samples them:

- PLANT is invalid if the agent holds no seeds, or the current tile is not empty
- WATER is invalid if the current tile has no plant, or the plant was already watered today
- HARVEST is invalid if the plant has no yield units, or has not reached first yield day
- DIG is invalid if the current tile is empty, locked, or has an animal on it
- BUY_SEED is invalid if insufficient money

Invalid masking is cheap to implement and significantly accelerates convergence by preventing the agent from wasting gradient steps on structurally impossible moves.

---

## 4. Reward Shaping

### The Sparse Reward Problem

The game's native reward is: +1 if you win, -1 if you lose, 0 for a tie — all delivered at turn 720. For 720 turns of random exploration, this gives the agent essentially no learning signal. The probability that random actions produce a win is low, and even when they do, attributing causality is nearly impossible.

**Shaped reward** provides intermediate feedback to guide learning, at the cost of potentially changing what the agent optimises for.

### Intermediate Reward Candidates

Good intermediate rewards should be **correlated with winning** and **easy to detect**:

| Event | Suggested Reward | Rationale |
|---|---|---|
| Watering a melon on day ≥6 (in bonus window) | +0.1 | Directly builds yield |
| Harvesting a melon at yield_units=6 | +2.0 | Full yield achieved |
| Harvesting a melon at yield_units < 6 | +0.5 | Partial, still positive |
| Selling a melon at price ≥ $200 | +1.0 per unit sold | Good timing |
| Selling a melon at price < $100 | -0.5 per unit | Discourage panic selling |
| Plant turning into weed | -1.0 | Failure, lost seed cost |
| Money increase this turn (scaled) | +delta_money / 1000 | Dense but noisy |
| Final money delta vs opponent | ±10 | Terminal signal |

### Reward Hacking Risks

Reward shaping is dangerous if done naively. Some failure modes:

- **Watering obsession**: If watering earns reward, the agent may learn to move back and forth between two tiles and water repeatedly — but watering a plant twice in one day is a no-op. This is safe mechanically, but the agent wastes turns on no-ops. Fix by rewarding only the *first* watering each day.

- **Planting and immediately harvesting**: If harvest reward is not conditioned on yield, the agent might plant and immediately harvest a 1-yield melon for a small reward, ignoring the 10-day growth cycle. Fix by making harvest reward proportional to yield_units, not just the harvest act.

- **Price floor exploitation**: If the agent learns that selling anything earns positive reward, it may sell at $1 (the price floor) because it still gets +reward. Fix by making sell reward proportional to price, not a flat bonus.

### Shaping Parallel Plant Strategy

One of the key strategic insights in Kaggriculture is growing multiple crops simultaneously — melons take 10–12 days to mature, so a farmer growing one at a time wastes most of the game idle. Reward shaping can push the agent toward parallelism:

- A **bonus for having N active plants**, rewarded once per day rather than every turn
- A **penalty for idle turns** (PASS actions) when there are unwatered plants on the farm
- A **penalty for plant decay** — a plant turning to weed means the agent failed to water it, losing both the seed cost and all the turns spent growing it

---

## 5. Network Architecture

### High-Level Structure

The recommended architecture is an **actor-critic network** (two heads sharing a common trunk):

```
Input: farm grid (10×10, 8 channels) + opponent grid + scalars
         |
    CNN trunk (2-3 conv layers, 3×3 kernels, ~64 filters)
         |
    Flatten + concatenate with scalar features
         |
    MLP layers (2-3 layers, 256-512 units, ReLU)
         |
    ┌────┴────┐
Policy Head   Value Head
(softmax over   (scalar,
 action space)   no activation)
```

### Why Actor-Critic (PPO)

PPO (Proximal Policy Optimisation) is an actor-critic algorithm that simultaneously trains:
- **The policy** (actor): which action to take given the state
- **The value function** (critic): how much total reward to expect from this state onward

The value function provides a **baseline** for advantage estimation — it tells the policy not "you got +2 reward this turn" but "you got +2 reward when the baseline predicted +0.5, so this action was better than expected by +1.5." This dramatically reduces variance in gradient estimates.

PPO also uses a **clipped objective** that prevents the policy from updating too aggressively in a single step, which is important given the high variance in episode outcomes.

### What the Weights Learn

Conceptually, the network learns three kinds of patterns:

- **Spatial reasoning** (in the CNN layers): "when I am adjacent to an unwatered melon tile, moving to it is valuable." The CNN weight structure mirrors what a pathfinding heuristic would compute, but learned from data.

- **Temporal reasoning** (in the MLP, informed by day/hour features): "it is day 25, price is high, I have 6 melons in the shed — now is the time to sell." The network learns to associate late-game + high price + full shed with a sell action.

- **Value estimation** (the critic): "being in this state, with 3 growing melons, $1200 in the bank, and 15 days left, is worth approximately +3.5 in shaped reward going forward."

---

## 6. Training Setup

### Self-Play vs Fixed Opponent

Because market prices are shared between players, the two agents are not fully independent. If your opponent sells 300 melons on day 20, the melon price crashes to $1 and your strategy is ruined — even if you played perfectly. This is a **competitive interaction** that a fixed-opponent training setup cannot adequately model.

**Self-play** — where the agent trains against a copy of itself — is the gold standard for two-player competitive games. The key benefit: as your agent improves, so does its opponent, creating a curriculum that continuously challenges the agent at the appropriate level.

A practical self-play setup uses a **pool of past checkpoints** as opponents (not just the latest copy). This prevents the agent from over-fitting to its current self and cycling through rock-paper-scissors-style strategy loops.

### Episode Count

One episode = one 30-day game = 720 turns. At roughly 720 decisions per episode:

- **Behavioural cloning pre-training**: a few thousand episodes of demonstration data is sufficient
- **PPO fine-tuning**: 10,000–100,000 episodes to see meaningful convergence
- **Self-play**: 100,000+ episodes, potentially much more for strong play

This is not unusual for complex games — AlphaGo-style systems run millions of episodes. For Kaggriculture, the smaller state/action space means convergence should be faster, but expect training on the order of days on a single GPU.

### Curriculum Learning

A curriculum structures training to start simple and gradually increase complexity:

1. **Stage 1**: Single melon, unlimited time, no opponent — just learn to plant, water, and harvest one melon before it decays.
2. **Stage 2**: Multiple crops simultaneously, no opponent — learn to manage parallel planting, daily watering routes, and harvest timing.
3. **Stage 3**: Full game against a fixed heuristic opponent — learn to manage market dynamics and competition timing.
4. **Stage 4**: Self-play — refine against improving opposition.

Each stage gives the agent a solvable problem before confronting the full complexity.

---

## 7. Supervised Learning Pre-Training

### Behavioural Cloning

Before any RL, you can train the network to **imitate a hand-coded or heuristic agent**. This is called behavioural cloning (BC):

1. Write a simple deterministic agent that captures basic competence — plants crops, waters them daily, harvests at maturity, sells when price is reasonable
2. Run it for thousands of episodes, recording every (state, action) pair
3. Train the policy network as a classifier: given this state, predict which action the heuristic agent took

The result is a network that approximates the heuristic strategy — not optimal, but far better than random. This eliminates the painful early phase of RL where the agent wanders randomly and rarely gets meaningful reward.

### Why This Helps Enormously

The random-exploration phase is the bottleneck of RL for long-horizon tasks. For Kaggriculture, a randomly acting agent will:
- Frequently fail to water plants (causing weed deaths)
- Rarely time sells correctly
- Waste most turns on PASS or random movement

The shaped reward signal from these random episodes is almost entirely negative, giving the agent almost no useful learning signal. A BC-initialised agent, by contrast, already plays a basic competent strategy from episode one — generating meaningful reward signals that RL can then refine and exceed.

### Data Collection

From a single 720-turn episode you collect 720 (state, action) pairs. A few thousand episodes gives hundreds of thousands of training samples — enough for BC convergence. The kaggle-environments `env.run()` interface makes this straightforward: loop episodes, dump observations and actions to disk, train offline.

---

## 8. Game Theory Angle

### Is This Zero-Sum?

Kaggriculture is **not strictly zero-sum**. Both players can grow independently; one player watering their melons does not prevent the other from watering theirs. However, the **shared dynamic market** creates a coupling: selling large quantities of the same crop simultaneously drives the price down for both players.

From the price function table: melon has `above_func = sq` and `above_target = 3.60`. This means even a modest glut crashes the price very hard — if both players sell simultaneously, the price can drop to $1. This is the most important game-theoretic interaction in Kaggriculture.

### Price Impact and Coordination

The market inventory starts at I₀ = 10,000 units and melon's calibration throughput T = 300 units. Selling T units past I₀ (a relatively small number given the 10×10 grid) applies the full above-target curve and crashes prices to near $1. Two players each selling 150 melons simultaneously would have this effect.

This means **timing is strategic**: if you can infer from your opponent's farm tiles (which are visible) that they have 6 melons about to be harvested, you should sell yours first, before the glut. Conversely, holding your melons while the opponent sells and watching the price recover is also a valid strategy — if you can afford the wait.

### Nash Equilibrium Intuition

In a stylised version of the market timing game: if both players are rational and know each other's harvest schedules, the Nash equilibrium likely involves **staggered selling** — both players prefer to sell when the other is not selling. But since both have to sell before day 30, there is pressure to sell early. The equilibrium is probably a mixed strategy or a coordination problem with no clean dominant strategy.

In practice, opponent modelling (tracking their farm state to predict sell timing) is likely to be worth the complexity if the agent reaches a high enough skill level.

### Dominant Strategies vs Opponent Adaptation

Against a naive opponent, melons at base price ($250) offer the highest profit/tile/day of any crop at approximately $129/tile/day. This is a **dominant strategy in isolation** — melon farming is optimal regardless of what the opponent does, as long as price stays high.

The interesting game-theoretic region is when both players adopt this same strategy, causing price crashes. At that point, the agent needs to either:
- **Diversify** into crops with different price dynamics (wheat, carrot, eggs)
- **Optimise market timing** to sell before the opponent
- **Control tempo** by harvesting in waves that do not coincide with the opponent's

This is exactly the kind of strategic depth that self-play is designed to discover.

---

## 9. Practical Implementation Path

### Recommended Algorithm: PPO with Self-Play

PPO is the right starting point for this game because:
- It handles discrete action spaces naturally
- The clipped objective makes it stable with noisy rewards
- It is well-supported in libraries like Stable-Baselines3 and CleanRL
- Self-play extensions are well-documented

### Wrapping the Environment

The kaggle-environments interface is already in place — `env.run([agent_fn, agent_fn])` runs a full episode. For RL training, you need a standard Gym-compatible wrapper that:
- Resets by calling `env.reset()`
- Steps by calling `env.step([action_0, action_1])` and returning `(obs, reward, done, info)`
- Converts the dict observation to a tensor
- Applies action masking

This wrapper is ~100–200 lines and the most critical engineering piece before training begins.

### Key Hyperparameters to Tune

| Parameter | Suggested Starting Point |
|---|---|
| Learning rate | 3e-4 (decay to 1e-5) |
| PPO clip epsilon | 0.2 |
| Entropy coefficient | 0.01 (encourages exploration) |
| Value loss coefficient | 0.5 |
| GAE lambda | 0.95 |
| Rollout length | 720 (one full episode) |
| Minibatch size | 64–256 |
| Epochs per update | 4–10 |

### Milestone Roadmap

**Milestone 1 — Behavioural Cloning**
Generate 5,000 episodes using a simple heuristic agent (plant, water, harvest, sell). Train the policy network on the (state, action) pairs. Success criterion: the BC agent beats a random agent >90% of the time.

**Milestone 2 — PPO Fine-Tuning**
Take the BC-initialised weights and fine-tune with PPO against the heuristic agent as a fixed opponent. Add shaped rewards (harvest bonuses, weed penalties, sell-timing bonuses). Success criterion: RL agent wins >60% against the heuristic.

**Milestone 3 — Self-Play**
Replace the fixed opponent with a checkpoint pool. Update the pool every N thousand episodes. Success criterion: agent develops strategies the heuristic cannot express — market timing, crop diversification under price pressure, opponent-reactive selling.

**Milestone 4 — Submission**
Package the trained network weights + a small inference wrapper as `main.py`. Submit to the Kaggle leaderboard.

---

## 10. Open Questions and Experiments

### Does Market Timing Justify Optimisation?

The price function shows that melon crashes hard with a sq/above_target=3.60 curve. A single player selling 300 units (the calibration throughput T) moves the price significantly. With only a 10×10 grid and 30 days, can one player realistically produce enough melons to meaningfully crash prices alone? If yes, market timing matters enormously. If the game runs out of turns before either player reaches T units of production, timing is secondary to raw yield optimisation. This is worth running empirically.

### How Many Concurrent Plants Is Optimal?

There is a natural tension between parallel planting and watering capacity. Melons take 10–12 days to mature and need watering every day during the bonus window — but the farmer can only be in one place per turn. At some point adding a fourth or fifth plant means the farmer cannot service all of them in time, causing weed deaths that waste both seeds and turns. The optimal number depends on grid layout, unlocked quadrant size, and whether farm hands are hired. An RL agent operating in the full action space (including HIRE) might discover that 6–8 simultaneous plants with 2–3 workers is optimal — something that cannot be found by hand-tuning a rule-based agent. This is a natural experiment: train agents with different fixed plant counts and compare reward.

### Would an LSTM Help?

Market prices are partially predictable: the town center consumes products on a fixed schedule (every 12 turns, scaling up after days 10 and 20), and shop unlocks are discrete events visible in the observation. An **LSTM** (recurrent layer) could in principle learn to model the trajectory of market prices over time — noticing that melon prices have been stable for 5 days and are likely to stay high, vs observing a declining trend that suggests the opponent is selling.

Whether this outperforms a feedforward network that sees current price + a small price-history window (e.g. last 5 turns) is an empirical question. A simpler alternative is to add a fixed price-history buffer (last 5 melon prices) to the scalar observation and skip the LSTM entirely.

### Is Diversification Ever Optimal?

All analysis points to melon as the dominant crop in isolation. But under self-play, if both agents melon-farm and crash prices, the agent that pivots first to another strategy may gain an edge. The question is whether that pivot can be profitable given the long growth times (tomatoes take 8 days to first yield, strawberries take 10 days) and the remaining season length. A trained self-play agent will naturally discover this if diversification is indeed optimal — its emergence in policy would be strong evidence that the melon monoculture is a Nash equilibrium breakpoint under competitive play.

---

## Summary

Kaggriculture is a well-structured testbed for multi-agent RL. The key design decisions are:

1. Encode the 10×10 farm grid as a multi-channel CNN input alongside scalar market and inventory features
2. Use action masking to keep the effective action space manageable
3. Shape rewards around watering timeliness, harvest yield, and sell price to overcome the sparse terminal reward
4. Bootstrap training with behavioural cloning from a simple heuristic to skip the random exploration phase
5. Progress to PPO self-play to discover market timing and crop strategies that no hand-coded agent can express

The game's market mechanics — particularly melon's punishing above-glut price curve — create genuine strategic depth that a learned agent can exploit in ways a rule-based agent fundamentally cannot.
