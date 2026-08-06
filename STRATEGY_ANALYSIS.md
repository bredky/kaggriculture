# Kaggriculture: Comprehensive Strategy Analysis

This document is a technical reference for building competitive Kaggriculture agents. All numbers are derived from the game engine source code (`kaggriculture.py`) and the official `README.md`. Anything not directly confirmed by source code is marked **[HYPOTHESIS]**.

---

## 1. Resource Economics

### 1.1 Crop Data (from source `CROPS` dict)

| Crop | Seed Cost | Base Price | first_yield_day | max_yield_day | interval | max_yield | ongoing |
|------|-----------|------------|-----------------|---------------|----------|-----------|---------|
| Wheat | $10 | $25 | 2 | 4 | 0 | 6 | No |
| Carrot | $20 | $35 | 2 | 3 | 0 | 4 | No |
| Tomato | $50 | $60 | 8 | 8 | 1 | 4 | No (ongoing) |
| Strawberry | $100 | $120 | 10 | 10 | 2 | 4 | No (ongoing) |
| Melon | $80 | $250 | 10 | 12 | 0 | 6 | No |

### 1.2 Bonus Window Mechanics (Source: `_apply_unit_action`, op == \"WATER\")

For one-time crops, the bonus watering window starts at `ceil(max_yield_day / 2)` and ends at `max_yield_day`. Every day the plant is watered within this window, `yield_units` increases by 1 (or 2 if fertilized). The plant starts with `yield_units = 1`.

- **Wheat**: window = days 2-4 (3 watered days). Base yield = 1 + 3 = 4 unfertilized, 1 + 6 = 7 capped at max_yield=6 fertilized.
- **Carrot**: window = days 2-3 (2 watered days). Base yield = 1 + 2 = 3 unfertilized, 1 + 4 = 5 capped at max_yield=4 fertilized.
- **Melon**: window = days 6-12 (7 watered days). Base yield = 1 + 7 = 8 capped at max_yield=6 unfertilized. So melon hits 6 after 5 bonus days (day 10). Fertilized: hits 6 even sooner (day 8).

For ongoing crops, scheduled production happens at `first_yield_day + n*interval` for n=0,1,2,...,max_yield-1. Base yield per production is 1 (or 2 if fertilized AND watered that day).

- **Tomato**: produces at days 8, 9, 10, 11 (4 times). Total = 4 unfertilized, up to 8 fertilized (capped at max_yield=4 per accumulation check, so effectively 4-8 depending on harvest timing).
- **Strawberry**: produces at days 10, 12, 14, 16 (4 times). Total = 4 unfertilized, up to 8 fertilized (same cap caveat).

### 1.3 Profit Per Tile Per Day (at base market price, no price impact)

**One-Time Crops:**

| Crop | Seed | Max Yield (no fert) | Max Yield (fert) | Revenue (no fert) | Revenue (fert) | Profit (no fert) | Profit (fert) | Days Occupied | Profit/Tile/Day (no fert) | Profit/Tile/Day (fert) |
|------|------|---------------------|-------------------|-------------------|----------------|-------------------|----------------|---------------|---------------------------|------------------------|
| Wheat | $10 | 4 | 6 | $100 | $150 | $90 | $140 | 5* | $18.0 | $28.0 |
| Carrot | $20 | 3 | 4 | $105 | $140 | $85 | $120 | 4* | $21.3 | $30.0 |
| Melon | $80 | 6 | 6 | $1500 | $1500 | $1420 | $1420 | 11* | $129.1 | $129.1** |

*Days occupied = max_yield_day + 1 (one day after max_yield_day, the plant enters decay per source `max_lifespan_step = (day + max_yield_day + 1) * turns_per_day`). Must harvest before decay. Practically: Wheat occupies tile for ~5 days (plant day 0, harvestable from day 2, decays after day 5). Carrot occupies ~4 days. Melon occupies ~11 days (plant day 0, first harvestable day 10, decay starts day 13).

**Correction on occupancy**: The tile is freed immediately on HARVEST for one-time crops (`farm[\"tiles\"][fy][fx] = None`). So the tile is occupied from planting until harvest. Optimal harvest timing:
- **Wheat**: Plant day 0, water days 1-4, harvest day 4 (or later). Occupied = 5 days. Yield = 4 (unfert) or 6 (fert).
- **Carrot**: Plant day 0, water days 1-3, harvest day 3. Occupied = 4 days. Yield = 3 (unfert) or 4 (fert).
- **Melon**: Plant day 0, water days 1-10, harvest day 10. Occupied = 11 days. Yield = 6.

**Note on melon and fertilizer**: Melon's bonus window is days 6-12. Starting yield is 1. Each watered day in the window adds 1 (or 2 fert). By day 10 (5 watered bonus days), yield = 1+5 = 6 = max_yield. Fertilizer reaches cap at day 8 (1 + 2*3 days fert = 7, capped at 6). So fertilizer lets you harvest melon 2 days earlier (day 8 vs day 10), freeing the tile sooner. With fertilizer, melon occupancy = 9 days.

**Revised Melon with fertilizer**: Profit/tile/day = $1420/9 = $157.8.

**Ongoing Crops:**

| Crop | Seed | Total Yield (no fert) | Total Yield (fert, all days) | Revenue (no fert) | Revenue (fert) | Profit (no fert) | Profit (fert) | Days Occupied | Profit/Tile/Day (no fert) |
|------|------|-----------------------|-------------------------------|-------------------|----------------|-------------------|----------------|---------------|---------------------------|
| Tomato | $50 | 4 | up to 8 | $240 | $480 | $190 | $430 | ~13 | $14.6 |
| Strawberry | $100 | 4 | up to 8 | $480 | $960 | $380 | $860 | ~18 | $21.1 |

Tomato: produces days 8,9,10,11 (4 yields). Decay starts day 13 (`max_lifespan_step` set when production_count == max_yield on day 11 end-of-day refresh, so `(12+1)*24 = step 312` from planting). Total tile occupation ~13 days (plant to weed conversion).

Strawberry: produces days 10,12,14,16 (4 yields). Decay starts day 18. Total tile occupation ~18 days.

### 1.4 Break-Even Analysis

The break-even point is when cumulative revenue from harvested goods exceeds the seed cost. Since one-time crops are single-harvest, break-even is binary: you either harvest and profit, or the plant dies and you lose the seed cost.

| Crop | Seed Cost | Min Harvest Revenue (1 unit) | Break-even? |
|------|-----------|------------------------------|-------------|
| Wheat | $10 | $25 | Yes, always (if harvested) |
| Carrot | $20 | $35 | Yes, always (if harvested) |
| Tomato | $50 | $60/unit | Yes after 1st yield |
| Strawberry | $100 | $120/unit | Yes after 1st yield |
| Melon | $80 | $250/unit (min 1) | Yes, always (if harvested) |

### 1.5 Risk Profile (Sunk Cost of Death)

If a plant turns into a weed (2 consecutive unwatered days), you lose:
- **Wheat**: $10 seed + all turns spent watering/moving
- **Carrot**: $20 seed + turns
- **Tomato**: $50 seed + turns (higher risk since 8 days before first yield)
- **Strawberry**: $100 seed + turns (10 days before first yield — very high risk)
- **Melon**: $80 seed + turns (10 days before first yield — high risk, but high reward)

**Key insight from source**: `consecutive_unwatered` starts at 1 on planting day. If you plant and don't water that same day, by end-of-day refresh `consecutive_unwatered` increments to 2 and the plant becomes a weed immediately. **You must water on planting day.**

### 1.6 Fertilizer Impact

Fertilizer costs $100 to buy, or can be collected free from animals (1/animal/day via `COLLECT_FERTILIZER`). Fertilizing a plant doubles the per-day bonus for 3 days (source: `fertilized_until_day = max(current, day + 2)`, so active for days `day`, `day+1`, `day+2`).

**Value by crop:**
- **Wheat**: +2 extra units over 3 days in window (days 2-4), so +2 units = +$50 at base price. ROI on bought fertilizer: -$50 net loss. Only worth it if fertilizer is free (from animals).
- **Carrot**: Window is only 2 days. +2 extra units (but capped at 4). Actually: window days 2-3, fertilize day 2 → day 2 gets +2 instead of +1, day 3 gets +2 instead of +1 → total 1+4=5 capped at 4. So +1 extra unit = +$35. Not worth buying fertilizer for.
- **Melon**: Already hits cap at day 10 without fertilizer. With fertilizer, hits cap at day 8. Value = 2 days earlier harvest = 2 days of tile availability. Worth it if you have free fertilizer and can use those 2 days.
- **Tomato**: Each fertilized+watered production day yields 2 instead of 1. Up to +4 extra over the 4 production days. +$240 at base price. Very strong ROI even on bought fertilizer.
- **Strawberry**: Each fertilized+watered production day yields 2 instead of 1. But productions are every 2 days (days 10,12,14,16), so a single fertilizer application (3 days) covers at most 2 production days. +2 units = +$240 at base price. Strong ROI.

### 1.7 Comparison Table: All Revenue Sources

| Resource | Seed/Buy Cost | Infra Cost | Total Investment | Max Revenue (base price) | Best Profit/Tile/Day | Days to First Revenue | Notes |
|----------|---------------|------------|------------------|--------------------------|----------------------|----------------------|-------|
| Wheat | $10 | $0 | $10 | $100-150 | $18-28 | 2 | Fast, low risk, feeds animals |
| Carrot | $20 | $0 | $20 | $105-140 | $21-30 | 2 | Fast, moderate price |
| Melon | $80 | $0 | $80 | $1500 | $129-158 | 10 | Highest profit/tile but CRASHES market |
| Tomato | $50 | $0 | $50 | $240-480 | $15-33 | 8 | Ongoing, decent |
| Strawberry | $100 | $0 | $100 | $480-960 | $21-48 | 10 | Ongoing, high base price |
| Goose/Egg | $300 | 1 turn (coop) | $300 | Infinite | ~$50/day | 4 | Indefinite, needs wheat feed |
| Cow/Milk | $400 | 1 turn (pasture) | $400 | Infinite | ~$80/2days | 8 | Indefinite, needs wheat feed, price crashes fast |
| Sheep/Wool | $500 | 1 turn (pasture) | $500 | Infinite | ~$67/3days | 6 | Indefinite, needs wheat feed, price crashes fast |

---

## 2. Time Management

### 2.1 Turn Budget

- **720 total turns** (24 turns/day x 30 days)
- Each farmer/hand gets exactly **1 action per turn**
- Market orders are separate: up to **10 market orders per turn** regardless of farmer actions

### 2.2 Action Turn Costs

Every action consumes exactly 1 turn:

| Action | Turn Cost | Notes |
|--------|-----------|-------|
| NORTH/SOUTH/EAST/WEST | 1 | Move 1 tile in cardinal direction |
| PLANT | 1 | Must be on empty tile, consumes seed |
| WATER | 1 | No-op if already watered today |
| HARVEST | 1 | Picks up all yield_units on tile |
| FERTILIZE | 1 | Consumes 1 fertilizer from inventory |
| FEED | 1 | Consumes 1 wheat from inventory |
| CARE | 1 | No-op if already cared today |
| COLLECT_FERTILIZER | 1 | Only if fertilizer_available |
| BUILD_COOP / BUILD_PASTURE | 1 | On empty tile |
| DIG | 1 | Removes weed/plant/empty structure |
| DROP | 1 | Dumps entire inventory to shed (must be adjacent) |
| PICKUP | 1 | Takes items from shed (must be adjacent) |
| PLACE | 1 | Places animal on structure or items to shed |
| PASS | 1 (wasted) | |

### 2.3 Movement Cost Analysis

The farmer spawns at (4,4) each day (NW shed-access tile). The NW quadrant covers tiles (0,0) to (4,4).

**Maximum distance from spawn to any NW tile**: Manhattan distance from (4,4) to (0,0) = 8 turns. Round trip = 16 turns. That leaves only 8 turns for actual work out of 24.

**Practical distances within NW quadrant:**
- Adjacent tiles to spawn (4,4): 1 turn each way
- Corner (0,0): 8 turns each way
- Average tile in NW: ~4 turns from spawn

**Key insight**: Movement is the biggest time sink. An agent that minimizes travel and clusters operations near the shed will vastly outperform one that wanders.

### 2.4 Opportunity Cost Framework

Every turn spent moving is a turn not spent watering, harvesting, or feeding. The opportunity cost of movement:

- Moving 1 tile costs 1 turn. If that turn could have been used to water a plant (preventing death of $10-$100 seed), the opportunity cost is the seed value.
- Moving 1 tile costs 1 turn. If that turn could have been used to harvest 6 melons at $250/each = $1500, the opportunity cost is $1500.

**Priority ordering by value-at-risk:**
1. FEED animals about to escape (sunk cost: $300-500 + structure + all accumulated care)
2. WATER plants about to die (sunk cost: seed + time invested)
3. HARVEST mature crops about to decay (yield decreasing every other turn once past max_lifespan)
4. PLANT on available tiles (start growth clock)
5. WATER plants not yet in danger (build toward bonus)
6. CARE for animals (bank yield bonus)
7. COLLECT_FERTILIZER (free resource)
8. Movement to next task

### 2.5 Farm Layout and Movement Efficiency

**Optimal layout**: Plant crops in a tight cluster near the shed (tiles adjacent to (4,4)). The 4 shed-adjacent tiles are (4,4), (5,4), (4,5), (5,5). The farmer can water/harvest all 4 without moving.

**NW quadrant usable tiles**: 25 tiles (5x5), but realistically the farmer can only service a subset per day due to movement overhead.

**Tiles serviceable per day**: With 24 turns and needing to water each tile once per day:
- Tiles touching the spawn path (distance 0-2): ~12 tiles serviceable (2 turns per tile: move + water)
- Tiles at distance 3-4: ~8 tiles serviceable
- Tiles at distance 5+: Barely serviceable without farm hands

### 2.6 Batching and Parallelization

- **Market orders**: Up to 10 per turn, processed simultaneously with farmer actions. Always batch buys/sells.
- **Farm hands**: Each hand acts independently each turn. A farmer + 2 hands = 3 actions/turn = 72 actions/day.
- **DROP**: Dumps entire inventory in 1 turn (vs PLACE which moves items one type at a time).

---

## 3. Farm Space Efficiency

### 3.1 Tiles Manageable Per Day

**Single farmer, single quadrant (25 tiles)**:
- Watering only (no harvest/plant): Each tile needs 1 WATER + movement. In a tight grid, movement averages ~0.5 turns per tile (adjacent moves). So ~16 tiles can be watered per day with 24 turns.
- With harvest/plant mixed in: ~10-12 tiles manageable per day.
- **Realistic maximum for one farmer: ~12-15 actively managed tiles.**

**With farm hands**: Each hand adds 24 turns/day. Two hands = 72 total turns = potentially 30+ tiles manageable.

### 3.2 Crop Density

All crops occupy exactly 1 tile. No spacing requirements exist — crops can be planted on every single available tile. **Optimal density = 100% fill** of all unlocked, non-weed tiles.

The only constraint is the farmer's ability to water/harvest them all.

### 3.3 Land Expansion Analysis

| Quadrant | Cost | New Tiles | Cost Per Tile | Cumulative |
|----------|------|-----------|---------------|------------|
| NW (free) | $0 | 25 | $0 | 25 tiles |
| NE ($1k) | $1,000 | 25 | $40 | 50 tiles |
| SW ($2k) | $2,000 | 25 | $80 | 75 tiles |
| SE ($4k) | $4,000 | 25 | $160 | 100 tiles |

**When is expansion worth it?**

NE quadrant ($1k): If you plant wheat on 10 new tiles, revenue = 10 * $90 profit = $900 per cycle. Wheat cycle = ~5 days, so $900/5 = $180/day. Pays for itself in ~6 days. **Worth it by day 5-10 if you have the workforce.**

SW quadrant ($2k): Similar math but $2k. Needs ~11 days to break even with wheat. Only worth it in the first half of the game, and only if you have farm hands to service the tiles.

SE quadrant ($4k): Needs ~22 days to break even. **Almost never worth it** unless you have a very specific late-game strategy. With only 30 days, this is a trap.

**Key consideration**: More land means more weed spawns and more movement overhead. Land is only valuable if you have the workforce to use it.

### 3.4 Weed Spawn Analysis

Weed spawn probability: 0.005 per empty unlocked tile per day.

| Unlocked Tiles | Empty Tiles (est.) | Expected Weeds/Day | Weeds Over 30 Days |
|----------------|--------------------|--------------------|---------------------|
| 25 (NW only) | 15 | 0.075 | 2.25 |
| 50 (NW+NE) | 30 | 0.15 | 4.5 |
| 75 (3 quadrants) | 40 | 0.20 | 6.0 |
| 100 (all) | 60 | 0.30 | 9.0 |

At 0.005 probability, weeds are a minor nuisance. Each weed costs 1 DIG turn + movement to reach. **[HYPOTHESIS]** Generally not worth proactively clearing unless they're blocking a planting tile you need. The expected cost is ~2-9 turns over the entire game depending on land size.

### 3.5 Shed Capacity

Shed cap: **100 items** (excluding seeds).

**When does this bottleneck?**
- 25 wheat tiles harvested at 4 units each = 100 items. Exactly at cap.
- 10 melon tiles at 6 units = 60 items. Comfortable.
- Animals producing eggs/milk/wool accumulate over time if not sold.

**Mitigation**: Sell frequently. Harvest → DROP → SELL cycle should happen every day or two. The end-of-day auto-drop from inventories to shed can cause overflow loss if the shed is near capacity.

**Critical source detail**: Animals bought via `BUY_ANIMAL` go to the shed (not directly to a tile), counting against the 100-item cap. Similarly, `BUY_PRODUCT` (wheat for feed) goes to the shed.

---

## 4. Workforce Scaling

### 4.1 Farm Hand Cost Structure

Cost = `farmHandCostMult * fib(n)` where n = number of hires already today. With default `farmHandCostMult = 1`:

| Hire # (today) | n | fib(n) | Cost | Cumulative Cost |
|----------------|---|--------|------|-----------------|
| 1st | 0 | 1 | $1 | $1 |
| 2nd | 1 | 1 | $1 | $2 |
| 3rd | 2 | 2 | $2 | $4 |
| 4th | 3 | 3 | $3 | $7 |
| 5th | 4 | 5 | $5 | $12 |
| 6th | 5 | 8 | $8 | $20 |
| 7th | 6 | 13 | $13 | $33 |
| 8th | 7 | 21 | $21 | $54 |

**Hands are extremely cheap.** The first two hands cost $1 each. Even 5 hands cost only $12/day total.

### 4.2 When Hiring Is Worth It

Each hand provides 24 additional actions/day. Even at the most conservative valuation (watering wheat worth $25 in eventual revenue per watering action), a hand that waters 10 tiles generates ~$250 in expected value for $1-$5 cost.

**Hiring 1-2 hands is ALWAYS worth it from day 1.** The cost is negligible. The only constraint is whether you have enough tiles for them to work on.

At 5 hands ($12/day), you have 144 actions/day. This can manage ~50-60 tiles, which requires 2+ quadrants.

### 4.3 Hand Spawn Mechanics (Source: `_spawn_hand`)

Hands spawn at shed-access tiles in NWSE preference order, picking the least-occupied tile. With the farmer at (4,4):
- 1st hand: (5,4) — NE quadrant (may be locked!)
- 2nd hand: (4,5) — SW quadrant (may be locked!)
- 3rd hand: (5,5) — SE quadrant (may be locked!)

**Important**: Hands CAN spawn on locked tiles. They can move off locked tiles onto unlocked ones. This costs 1+ movement turns at the start of the day.

### 4.4 End-of-Day Behavior

At end of day (source: `_end_of_day`):
1. All plant/animal daily refresh happens
2. All inventories (farmer + hands) auto-dump to shed (overflow discarded!)
3. Farmer resets to (4,4)
4. Hands disappear (must re-hire next day)
5. `hires_today` resets to 0

**Critical implication**: If a hand is carrying harvested goods and the shed is near capacity, those goods are LOST. Always have hands DROP inventory near the shed before end of day, or ensure shed has room.

### 4.5 Coordination Strategy

**Farmer**: Focus on time-sensitive tasks (harvesting mature crops, feeding animals about to escape). Stay near the shed for market operations (selling requires goods in shed).

**Hands**: Assign to watering routes. Each hand covers a zone of ~8-12 tiles. Hands don't need shed access since their inventory auto-drops at end of day.

**[HYPOTHESIS]** Optimal split: Farmer handles animals (feed, care, collect fertilizer, harvest) near the shed. Hands handle crop watering in assigned zones.

---

## 5. Market Dynamics

### 5.1 Price Function Deep Dive

```
price(inv) = base + sign * amp * f(|inv - I0|)
where:
  amp = target * base / f(T)
  f in {linear, sq, sqrt, log}
  Floored at $1, rounded to nearest dollar
```

The key insight: **each side of I0 has independent shape and target**. This creates asymmetric price responses.

### 5.2 Per-Resource Price Sensitivity

**Wheat** (base $25, T=400):
- Below I0: sqrt, target 0.80 → sells 400 units below I0 → price = $45. Gentle rise.
- Above I0: log, target 0.20 → sells 400 units above I0 → price = $20. Very resistant to glut.
- **Wheat is the safest sell.** Price barely drops even with massive oversupply.

**Carrot** (base $35, T=450):
- Below I0: log, target 0.20 → barely rises on scarcity ($42 at I0-T).
- Above I0: sqrt, target 0.70 → crashes hard. At I0+T: $10. At I0+2T: $1.
- **Carrot is vulnerable to oversupply.** Sell early and fast.

**Tomato** (base $60, T=200):
- Below I0: linear, target 0.40 → rises linearly ($84 at I0-T).
- Above I0: sqrt, target 0.60 → drops to $24 at I0+T, $9 at I0+2T.
- **Moderate sensitivity both ways.**

**Strawberry** (base $120, T=100):
- Below I0: sqrt, target 0.70 → rises to $204 at I0-T. Strong scarcity premium.
- Above I0: linear, target 1.60 → crashes linearly. At I0+T: $1 (floor!).
- **Extremely fragile.** Even selling ~100 units crashes to floor. T=100 is tiny.

**Melon** (base $250, T=300):
- Below I0: log, target 0.20 → rises gently ($300 at I0-T).
- Above I0: sq (quadratic!), target 3.60 → At I0+T: $1 (floor!).
- **The most volatile premium crop.** Quadratic above function means even small gluts destroy price. But T=300, so you need to sell ~300 units to move the price by `target*base`. However since sq is quadratic, the price drops catastrophically: selling just ~50-100 melons above I0 may already drive price near floor.

Let me compute: amp = 3.60 * 250 / (300^2) = 900 / 90000 = 0.01. Price at I0+x = 250 - 0.01 * x^2. Price = $1 when 0.01*x^2 = 249, x^2 = 24900, x ≈ 158. **Selling ~158 melons crashes melon to $1.**

**Egg** (base $50, T=332):
- Below I0: linear, target 0.40 → $70 at I0-T.
- Above I0: log, target 0.20 → $40 at I0+T. Very resistant to oversupply.
- **Eggs are extremely stable.** Almost as safe as wheat.

**Milk** (base $160, T=122):
- Below I0: sqrt, target 0.60 → $256 at I0-T.
- Above I0: linear, target 1.60 → $1 at I0+T (floor!).
- **Fragile.** Linear crash with high target = prices drop $1.60*160/122 ≈ $2.10 per unit sold. Selling ~76 units crashes to floor. Very sensitive.

**Wool** (base $200, T=105):
- Below I0: log, target 0.20 → $240 at I0-T.
- Above I0: sq (quadratic!), target 3.20 → crashes extremely fast.
- amp = 3.20 * 200 / (105^2) = 640 / 11025 ≈ 0.058. Price at I0+x = 200 - 0.058*x^2. Floor at x ≈ 59. **Selling ~59 wool crashes to $1.**

**Fertilizer** (base $100, T=200):
- Linear both sides, target 0.40. Symmetric. Predictable.

### 5.3 Units to Crash Each Market (Approximate units above I0 to hit $1 floor)

| Resource | Base | ~Units to Floor | Crash Speed |
|----------|------|-----------------|-------------|
| Wheat | $25 | Never practical (log absorbs) | Extremely slow |
| Carrot | $35 | ~900 (sqrt) | Moderate |
| Tomato | $60 | ~400 (sqrt) | Moderate |
| Strawberry | $120 | ~75 (linear) | Fast |
| Melon | $250 | ~158 (quadratic) | Very fast |
| Egg | $50 | Never practical (log absorbs) | Extremely slow |
| Milk | $160 | ~76 (linear) | Fast |
| Wool | $200 | ~59 (quadratic) | Fastest |

### 5.4 Town Demand (Market Drain)

**Town Center** (always active): Consumes 1 of each non-fertilizer product every 12 turns.
- Day 0-9: 1 per 12 turns = 2/day of each product = 16/day total across 8 products
- Day 10-19: 2 per 12 turns = 4/day of each product = 32/day total
- Day 20-29: 4 per 12 turns = 8/day of each product = 64/day total

**Shops** (unlock every 3 days, random selection): Each consumes 1 of each demanded product every 4 turns = 6/day. Single-product shops consume 2x = 12/day.

| Shop | Products | Drain/Day per product |
|------|----------|-----------------------|
| Bakery | Egg, Wheat | 6 each |
| Pizza Shop | Milk, Tomato, Wheat | 6 each |
| Brunch Spot | Egg, Wheat, Strawberry | 6 each |
| Yarn Store | Wool (2x) | 12 |
| Ice Cream Shop | Strawberry, Milk, Wheat | 6 each |
| Pet Cafe | Carrot (2x) | 12 |
| Smoothie Shop | Strawberry, Milk | 6 each |
| Farmers Market | Wheat, Carrot, Tomato, Strawberry | 6 each |

**Shop unlock schedule**: Days 3, 6, 9, 12, 15, 18, 21, 24 (every 3 days). All 8 shops unlock by day 24.

**Cumulative town demand per day on WHEAT** (appears in 4 shops: Bakery, Pizza Shop, Brunch Spot, Ice Cream Shop, Farmers Market = **5 shops**):
- By day 6 (2 shops unlocked): town center 2/day + shops ~12/day = ~14/day
- By day 12 (4 shops unlocked): town center 4/day + shops ~24/day = ~28/day
- By day 21 (7 shops unlocked): town center 8/day + shops ~30/day = ~38/day

**Over 30 days, town demand alone drains hundreds of units of each product from the market.** This steadily pushes prices UP (inventory decreasing below I0), benefiting sellers.

### 5.5 Price Floor Mechanics

From source (`_commit_unit`): When the sell price is $1 (floor), the unit is still sold (player gets $1), but **inventory does NOT increase**. This prevents the market from being permanently crashed — town demand continues to drain inventory, eventually pushing prices back up.

### 5.6 Concurrent Sell Order Mechanics

From source (`_process_market`): Both players' orders at the same position in their queues are processed in lockstep, one unit at a time. Both players see the same pre-commit price for each unit, then both units are committed simultaneously.

**Implication**: If both players sell melon simultaneously, each unit from both players hits the market. Prices drop twice as fast as expected. **[HYPOTHESIS]** If you detect your opponent is also selling melons (their farm shows melon plants), consider timing your sales to avoid overlap, or front-running their likely sell window.

### 5.7 Sell Timing Strategy

**Premium crops (melon, strawberry, milk, wool)**: Sell in small batches to avoid crashing the price. Melon at $250 base — selling 1 melon at $250 is worth more than selling 10 melons where the last ones are at $50.

**Stable crops (wheat, egg)**: Sell in bulk. Price barely moves. Wheat and eggs can be dumped en masse.

**Town demand creates natural price recovery**: Even if you crash a market, town consumption will slowly drain inventory back toward I0, restoring prices. But this takes many days.

---

## 6. Animal Operations

### 6.1 Animal Data (from source `ANIMALS` dict)

| Animal | Cost | Structure | first_yield_day | interval | max_held | Product |
|--------|------|-----------|-----------------|----------|----------|---------|
| Goose | $300 | COOP | 4 | 1 (daily) | 4 | EGG |
| Cow | $400 | PASTURE | 8 | 2 (every 2 days) | 6 | MILK |
| Sheep | $500 | PASTURE | 6 | 3 (every 3 days) | 6 | WOOL |

### 6.2 True Cost of Animal Operations

**Setup cost**: Animal purchase + 1 turn to BUILD structure + 1 turn to PLACE animal (need animal in inventory, which means PICKUP from shed + move to structure tile).

**Goose setup**: $300 (buy) + BUILD_COOP (1 turn) + PICKUP GOOSE (1 turn, must be shed-adjacent) + move to coop tile + PLACE GOOSE (1 turn) = $300 + 3-5 turns.

**Daily operating cost per animal**:
- 1 FEED turn (consumes 1 wheat from inventory — must carry wheat)
- 1 CARE turn (optional but valuable for bonus)
- 1 HARVEST turn (when yield_units > 0)
- 1 COLLECT_FERTILIZER turn (optional, gets free fertilizer)
- Movement to/from animal tile

**Wheat feed cost**: 1 wheat/day per animal. Wheat costs $10 (seed) to grow, but can also be bought at market price (~$25). If growing wheat to feed, you lose the ability to sell that wheat.

### 6.3 Daily Turn Budget Per Animal

Minimum viable (just feeding): 1 FEED turn + movement
With CARE: +1 turn
With HARVEST: +1 turn (only on yield days)
With COLLECT_FERTILIZER: +1 turn

**A single animal near the shed requires ~2-4 turns/day.** Multiple animals on adjacent tiles can be serviced more efficiently.

### 6.4 CARE Bonus Mechanics (Source: `_daily_refresh_animals`)

- At end of day: if fed AND cared that day, `pending_care_bonus` increments by 1.
- On production day: if fed, the entire banked bonus is added to yield, then bank resets to 0.
- If unfed on production day: base 1 unit produced, but bonus is NOT applied and bank resets.

**Goose (interval=1, daily production)**:
- Care bonus only banks for 0 days between productions (since it produces daily). The care bonus from day N is paid out on day N+1's production (the next day). So each CARE gives +1 egg on the next day's production. Effectively doubles production if you care daily (1 base + 1 care bonus = 2 eggs/day, capped at max_held=4).
- Wait — more precisely: care bonus increments at end of day, then production happens at end of day too. Looking at source order in `_daily_refresh_animals`: production check happens FIRST (`days_since_first` calculation, yield_units update), THEN the care bonus banking. So for a goose (interval=1): day N care bonus is banked at end of day N, and paid out at end of day N+1 when the next production fires. Net: +1 egg every other day from caring, since the bank resets each production.

**Cow (interval=2, every 2 days)**:
- Between productions, you can bank 1 care bonus per day for 2 days = +2 bonus on next production. So production = 1 + 2 = 3 milk every 2 days = 1.5 milk/day. But capped at max_held=6 for unharvested.

**Sheep (interval=3, every 3 days)**:
- Bank up to 3 care bonuses between productions = +3 bonus. Production = 1 + 3 = 4 wool every 3 days = 1.33 wool/day. Capped at max_held=6.

### 6.5 Animal Profitability Analysis (at base price, with care)

**Goose**:
- Revenue: ~1.5 eggs/day * $50 = $75/day (with daily care giving +1 every other day on average — actually need to trace more carefully)
- Let me re-analyze: Goose produces at intervals of 1 day. At end of day N, if it's a production day and fed: yield += 1 + pending_care_bonus, then reset. Then if fed AND cared: pending_care_bonus += 1. So: Day 4 (first production): yield += 1+0 = 1, then if cared: bonus=1. Day 5: yield += 1+1 = 2, bonus resets to 0, then if cared: bonus=1. Day 6: yield += 1+1 = 2, etc. So after the first day, it's 2 eggs/day with daily care.
- Revenue: 2 eggs/day * $50 = $100/day.
- Cost: $300 buy + $10/day wheat seed (growing it) or ~$25/day buying wheat. Let's use $10/day (growing).
- Net: $90/day after feed cost. Break-even: $300 / $90 ≈ 3.3 days after first production = day 7.3 total.
- **Over 30 days**: ~23 producing days * 2 eggs * $50 = $2300 revenue, minus $300 buy, minus ~$260 feed = **~$1740 profit** per goose.

**Cow**:
- With daily care: 3 milk every 2 days = 1.5 milk/day * $160 = $240/day.
- But milk crashes at ~76 units! So this rate is unsustainable for a single player.
- Cost: $400 buy + $10/day feed.
- Net at base: $230/day. Break-even: $400/$230 ≈ 1.7 days after first production = day 9.7.
- **Over 30 days**: ~11 production events * 3 milk * $160 = $5280 at base price. But price WILL crash.
- More realistically: First few sells at $160, then rapid decline. Maybe average $80/unit.
- Realistic: 33 milk * $80 = $2640 - $400 - $200 feed = **~$2040 profit**.

**Sheep**:
- With daily care: 4 wool every 3 days = 1.33 wool/day * $200 = $267/day at base.
- Wool crashes at ~59 units!! Very fragile.
- Cost: $500 buy + $10/day feed.
- Net at base: $257/day. Break-even: day 8.
- **Over 30 days**: ~8 production events * 4 wool * $200 = $6400 at base. But will crash.
- Realistic: maybe $100/unit average. 32 wool * $100 = $3200 - $500 - $240 = **~$2460 profit**. But very dependent on avoiding market crash.

### 6.6 Fertilizer Value

Fertilizer: base market price $100, collectible free from any surviving animal every day.

**Value use cases**:
1. **Sell**: At $100 (base price) per unit. If you have 3 animals producing fertilizer, that's $300/day in sellable fertilizer = significant income stream. But selling drives price down (linear, target 0.40 — moderate sensitivity).
2. **Use on crops**: Doubles watering bonus for 3 days. Best on tomato/strawberry (doubles per-production yield).
3. **Buy to use**: $100 cost. Only worth it on strawberry (saves $120+ per doubled yield) or tomato ($60 per doubled yield).

**[HYPOTHESIS]** Free fertilizer from animals is a hidden revenue stream. Even if you don't use it on crops, selling 1 fertilizer/day per animal at ~$80-100 each is meaningful.

### 6.7 Animals vs Crops Comparison

Over the full 30-day season:
- **Best wheat tile** (multiple cycles): ~5 cycles * $90 profit = $450/tile
- **Best melon tile**: 2 cycles * $1420 = $2840/tile (if price holds)
- **Goose**: ~$1740/tile (reliable, price-stable)
- **Cow**: ~$2040/tile (if price managed well)

**Animals win on per-tile profitability for long games**, but require more turns per tile per day (feed + care + harvest vs just water + harvest).

---

## 7. Opponent Interaction

### 7.1 Observable vs Hidden Information

**Observable (both players see):**
- Opponent's farm tiles (all crop/animal states, positions, watered_today, yield_units, etc.)
- Opponent's money balance
- Opponent's farmer position and hand positions
- Opponent's unlocked quadrants
- Opponent's hires_today count
- Market prices and inventory (shared)
- Town unlocked shops (shared)

**Hidden (only your own):**
- Shed contents (what items opponent is stockpiling)
- Seeds (what seeds opponent has purchased)
- Inventories (what farmer/hands are carrying)

### 7.2 Opponent Crop Choice Impact on Prices

Since both players sell to the same market, opponent's crop choice directly competes for price:
- If opponent grows melons too, both of you crash the melon market.
- If opponent grows wheat while you grow melons, you get the melon market to yourself.

**Reading opponent's farm**: You can see exactly what they've planted (tile data is public). On the first few days, check opponent's tiles for crop types to anticipate market competition.

### 7.3 First-Mover Advantage

**Melon/Wool/Milk/Strawberry**: Extreme first-mover advantage. The first player to sell gets high prices; subsequent selling crashes the market for both. Being the first to harvest and sell melons at $250 vs selling after your opponent has dumped 100 melons (price now at $1) is a massive difference.

**Wheat/Eggs**: Minimal first-mover advantage. Prices barely move.

### 7.4 Market Manipulation

**Deliberate crashing**: If you detect opponent is growing melons (visible on their farm), you could:
1. Also grow melons and sell first to crash the price before they harvest
2. Grow a different crop to avoid the crash zone
3. **[HYPOTHESIS]** Buy wheat to drive up its price (draining your own money but making opponent's feed costs higher — probably not worth it given starting money constraints)

**Counter-strategy**: If opponent is diversified, specialize in what they're not growing. If opponent is all-in on one premium crop, consider the same crop with earlier harvest timing.

### 7.5 Concurrent Sell Exploitation

When both players sell the same product in the same turn, they get the same pre-commit price for each unit. This means selling a large batch when you suspect the opponent is also selling causes maximum price damage to both players.

**[HYPOTHESIS]** Better to sell in small batches across many turns rather than one big dump, especially for premium goods.

---

## 8. Seasonal Timing

### 8.1 Growth Time vs Days Remaining

| Crop | Min Days to Harvest | Last Profitable Plant Day | Cycles Possible (30 days) |
|------|---------------------|---------------------------|---------------------------|
| Wheat | 2 (first_yield_day) | Day 27 (harvest day 29) | ~6 cycles |
| Carrot | 2 | Day 27 | ~7 cycles |
| Tomato | 8 | Day 21 (first yield day 29) | 1 cycle only |
| Strawberry | 10 | Day 19 (first yield day 29) | 1 cycle only |
| Melon | 10 | Day 19 (harvest day 29) | 2 cycles (plant day 0, harvest day 10, plant day 10, harvest day 20) |

**Note**: \"Last profitable plant day\" assumes minimum harvest (1 unit) to recover seed cost. For full yield, subtract more days.

### 8.2 Optimal Planting Windows

**Wheat**: Plant anytime. Last full-yield plant: day 25 (harvest day 29 with 4 yield units).
**Carrot**: Plant anytime. Last full-yield plant: day 26.
**Melon**: First plant day 0, harvest day 10. Second plant day 10, harvest day 20. Third plant day 20, harvest day 30 — but game ends at step 720 (end of day 29). So max 2 full melon cycles.
**Tomato**: Plant by day 0-2 to get all 4 yields. Plant by day 21 to get at least 1 yield.
**Strawberry**: Plant by day 0 to get all 4 yields (last yield day 16). Plant by day 19 to get at least 1 yield.

### 8.3 Town Demand Scaling Creates Price Opportunities

- **Day 10**: Town center demand doubles (2x). All non-fertilizer product prices start rising faster.
- **Day 20**: Town center demand quadruples (4x). 8 units/day of each product drained by town center alone.

**Strategy**: Stockpile goods in shed (up to 100 items) before day 10 and day 20, then sell into the rising prices. Town demand drains market inventory → prices rise → your goods sell at premium.

**Quantifying day-20 drain**: Town center: 8/day of each of 8 products = 64 items/day. Plus all unlocked shops (potentially 6-7 by day 20). Total drain could be 100+ units/day across all products. This is enormous.

### 8.4 Early/Mid/Late Game Strategy

**Early Game (Days 0-5)**:
- Plant wheat/carrot for quick cash flow
- Buy 1-2 melon seeds if affordable
- Hire 1-2 hands ($1-$2 total)
- Consider buying NE quadrant ($1k) if cash allows
- Build coop/pasture if going animal route
- **[HYPOTHESIS]** Optimal opening: Buy 5 wheat seeds ($50), hire 1 hand ($1), plant and water immediately

**Mid Game (Days 6-15)**:
- Harvest first melons (day 10)
- Animals start producing (goose day 4, sheep day 6, cow day 8)
- First shops unlocked (days 3, 6, 9, 12) — check which ones boost your products
- Day 10: town demand doubles. Sell accumulated goods.
- Start second melon cycle
- Transition from wheat to higher-value crops if cash allows

**Late Game (Days 16-29)**:
- Day 20: town demand quadruples. Major sell window.
- Last melon cycle harvests around day 20
- Switch to wheat/carrot for remaining days (fast turnaround)
- Sell everything. No point stockpiling past day 25.
- Animals continue producing — maximize care bonuses
- Don't plant anything that won't yield before day 30

---

## 9. Risk Management

### 9.1 Watering/Feeding Failure Consequences

**Source mechanics** (`_daily_refresh_plants`):
- `consecutive_unwatered` resets to 0 when watered, increments by 1 when not watered
- At `consecutive_unwatered >= 2`: tile becomes WEED
- New plants start with `consecutive_unwatered = 1`

**This means**:
- Plant day 0, don't water day 0 → consecutive_unwatered = 2 at end of day → WEED. **Plant dies in 1 day if never watered.**
- Plant day 0, water day 0, skip day 1 → consecutive_unwatered = 1 at end of day 1. Skip day 2 → consecutive_unwatered = 2 → WEED. **Can survive exactly 1 missed day after being watered.**

**Animals** (`_daily_refresh_animals`):
- Start with `consecutive_unfed = 0`
- `consecutive_unfed >= 2` → animal escapes, structure remains
- So a new animal survives its first day unfed (0→1), but escapes if unfed a second consecutive day (1→2).

### 9.2 Sunk Cost of Failures

| Resource Lost | Sunk Cost | Recovery |
|---------------|-----------|----------|
| Wheat plant dies | $10 + ~4 turns | Plant new one (cheap) |
| Carrot plant dies | $20 + ~4 turns | Plant new one |
| Melon plant dies | $80 + up to ~20 turns | Devastating if late-stage |
| Tomato plant dies | $50 + ~16 turns | Plant new one if early enough |
| Strawberry plant dies | $100 + ~20 turns | Major loss |
| Goose escapes | $300 + structure turn + feed | Structure remains, need new goose |
| Cow escapes | $400 + structure turn + feed | Structure remains, need new cow |
| Sheep escapes | $500 + structure turn + feed | Structure remains, need new sheep |

### 9.3 Diversification vs Specialization

**Specialization advantages**:
- Simpler movement patterns (all crops in one zone)
- Easier to time watering/harvest cycles
- Fewer seed types to buy

**Specialization risks**:
- Single market crash wipes out all revenue
- If opponent also specializes in the same crop, both suffer

**Diversification advantages**:
- Hedges against market crashes
- Can exploit whatever shops unlock
- Different harvest timing reduces turn pressure

**Diversification risks**:
- More complex movement (different crop locations)
- More seed types to manage
- Harder to optimize timing

**[HYPOTHESIS]** Best approach: Specialize in 1-2 high-value crops (melon + wheat), with wheat doubling as animal feed and a market-crash-proof fallback.

---

## 10. Action Priority Framework

### 10.1 Per-Turn Decision Hierarchy

Given all the analysis above, each turn an agent should evaluate actions in this priority order:

1. **FEED animals at consecutive_unfed=1** (prevent $300-$500 loss next day)
2. **WATER plants at consecutive_unwatered=1** (prevent seed loss + time investment loss)
3. **HARVEST crops in decay** (yield_units decreasing — every 2 turns past max_lifespan_step, 1 unit is lost)
4. **HARVEST mature crops at max yield** (free the tile for replanting)
5. **WATER plants in bonus window** (increase yield — each watering adds $25-$250 in eventual value)
6. **FEED animals (not critical)** (even if consecutive_unfed=0, need to feed daily)
7. **CARE for animals** (bank care bonus for next production)
8. **HARVEST animal products** (before hitting max_held cap)
9. **COLLECT_FERTILIZER** (free resource, $100 value each)
10. **PLANT on empty tiles** (start growth clocks)
11. **DROP inventory at shed** (make room, enable selling)
12. **MOVE toward highest-priority task**
13. **PASS** (only if nothing useful within reach)

### 10.2 Market Action Priority (per turn, up to 10 orders)

1. **SELL** goods at good prices (especially before opponent sells same product)
2. **BUY_SEED** for crops you plan to plant this day
3. **BUY_ANIMAL** if building animal infrastructure
4. **BUY_PRODUCT WHEAT** if you need feed and aren't growing enough
5. **HIRE** farm hands (extremely cheap, massive ROI)
6. **BUY_LAND** (only if you have workforce to use it)

### 10.3 Integrated Strategy Template

**Day 0 (setup)**:
- Market: BUY_SEED WHEAT 5, BUY_SEED MELON 2, HIRE
- Farmer: PLANT WHEAT
- Hand: PLANT WHEAT

**Days 1-4 (wheat ramp)**:
- Water all planted wheat
- Plant remaining seeds
- Harvest wheat on day 2+
- Sell wheat as harvested
- Buy melon seeds with wheat profits

**Days 5-9 (expansion)**:
- Melons growing, keep watering
- Wheat cycling for cash flow
- Consider NE quadrant purchase
- Build 1-2 coops if funds allow
- Hire 2 hands daily

**Days 10-15 (melon harvest + animal production)**:
- Harvest first melon batch — sell carefully (not all at once!)
- Animals producing — harvest and sell eggs
- Plant second melon cycle
- Sell into day-10 demand increase

**Days 16-24 (peak production)**:
- Second melon batch growing
- Animals at full production
- Wheat cycling for feed + cash
- Stockpile goods for day-20 price spike

**Days 25-29 (cash out)**:
- Sell everything
- Only plant wheat/carrot (fast turnaround)
- No new melon/strawberry plants
- Maximize animal harvests
- Final sell orders on last turns

---

## Appendix A: Key Source Code References

- **Crop definitions**: `CROPS` dict, line 11-17 of `kaggriculture.py`
- **Animal definitions**: `ANIMALS` dict, line 19-23
- **Market params**: `MARKET_PARAMS` dict, lines 41-51
- **Price function**: `market_price()`, lines 178-192
- **Watering bonus logic**: `_apply_unit_action()` op==\"WATER\", lines 375-388
- **Harvest logic**: `_apply_unit_action()` op==\"HARVEST\", lines 390-417
- **Plant decay**: `_decay_plants()`, lines 730-744
- **Daily refresh (plants)**: `_daily_refresh_plants()`, lines 747-780
- **Daily refresh (animals)**: `_daily_refresh_animals()`, lines 783-811
- **Town consumption**: `_town_consume()`, lines 705-727
- **Farm hand spawn**: `_spawn_hand()`, lines 510-518
- **End of day processing**: `_end_of_day()`, lines 838-868
- **Market order processing**: `_process_market()`, lines 521-605
- **Hire cost**: `_hire_cost()` / `_fib()`, lines 667-676

## Appendix B: Exact Price Computations

### Computing price at specific inventory levels

For reference, here is how to compute exact prices:

```
WHEAT at I0-100 (inventory=9900):
  f = sqrt, target = 0.80, base = 25, T = 400
  amp = 0.80 * 25 / sqrt(400) = 20 / 20 = 1.0
  price = 25 + 1.0 * sqrt(100) = 25 + 10 = 35

MELON at I0+50 (inventory=10050):
  f = sq, target = 3.60, base = 250, T = 300
  amp = 3.60 * 250 / (300^2) = 900 / 90000 = 0.01
  price = 250 - 0.01 * 50^2 = 250 - 25 = 225

MELON at I0+100 (inventory=10100):
  price = 250 - 0.01 * 100^2 = 250 - 100 = 150

MELON at I0+150 (inventory=10150):
  price = 250 - 0.01 * 150^2 = 250 - 225 = 25

MELON at I0+158 (inventory=10158):
  price = 250 - 0.01 * 158^2 = 250 - 249.64 = round(0.36) = $1 (floor)
```

### Revenue from selling N melons starting at I0

| Units Sold | Last Unit Price | Total Revenue | Average Price |
|------------|-----------------|---------------|---------------|
| 10 | $249 | ~$2,495 | $250 |
| 50 | $225 | ~$12,188 | $244 |
| 100 | $150 | ~$21,683 | $217 |
| 150 | $25 | ~$25,025 | $167 |
| 158 | $1 | ~$25,059 | $159 |
| 200 | $1 | ~$25,101 | $126 |

**Key takeaway**: The first 100 melons sold generate $21,683. The next 100 generate only $3,418. Selling too many melons is a massive waste.

### Revenue from selling N wheat starting at I0

| Units Sold | Last Unit Price | Total Revenue | Average Price |
|------------|-----------------|---------------|---------------|
| 100 | $24 | ~$2,430 | $24 |
| 400 | $20 | ~$8,760 | $22 |
| 1000 | $18 | ~$19,800 | $20 |

Wheat barely drops. Selling 1000 wheat still averages $20/unit.

## Appendix C: Town Demand Cumulative Market Drain

Assuming all 8 shops unlock by day 24 (at days 3,6,9,12,15,18,21,24):

**Wheat demand sources**: Town center + Bakery + Pizza Shop + Brunch Spot + Ice Cream Shop + Farmers Market = 5 shops want wheat (6/day each when unlocked) + town center.

**Approximate total wheat drain from market by day 30**:
- Town center: days 0-9 (2/day) + days 10-19 (4/day) + days 20-29 (8/day) = 20+40+80 = 140
- Bakery (unlocks day 3-ish): ~27 days * 6/day = 162 (if it's the first shop)
- Each additional wheat-demanding shop: similar but for fewer days

**Total wheat drain**: Potentially 300-600+ units over 30 days, depending on shop unlock order. This drives wheat price UP over time, making late-game wheat more valuable.

**For scarce products like wool** (only Yarn Store demands it):
- Town center: 140 units over 30 days
- Yarn Store (if unlocked): 12/day * remaining days
- Total: 140-300 units drained. Since wool crashes at ~59 units above I0, but town demand drains ~300 below I0, **wool price should naturally rise over time if nobody is selling it**.

## Appendix D: Animal Feed Wheat Requirements

Each animal consumes 1 wheat per day for feed. Wheat can be sourced by:
1. **Growing it**: $10 seed, 4 units per tile per ~5-day cycle = 0.8 wheat/tile/day. One wheat tile supports ~0.8 animals.
2. **Buying from market**: ~$25/unit at base price, rising with scarcity.

**Feed cost per animal per season** (30 days): ~26 feeding days (after placing) * 1 wheat = 26 wheat.
- If grown: 26 wheat / 4 per harvest = ~7 wheat tile-cycles. At $10/seed = $70 in seeds.
- If bought: 26 * $25 = $650.

**Growing wheat for feed is 9x cheaper than buying it.** Always grow your own feed wheat if possible.

## Appendix E: Optimal Tile Counts by Strategy

**Pure Wheat (25 tiles, NW only, 1 farmer + 1 hand)**:
- ~15 tiles actively farmed (limited by turns)
- 6 cycles * 15 tiles * 4 wheat * $22 avg = ~$7,920

**Pure Melon (25 tiles, NW only, 1 farmer + 2 hands)**:
- ~10 tiles actively farmed
- 2 cycles * 10 tiles * 6 melon * ~$167 avg (selling 120 total, price declines) = ~$12,024
- But: selling 120 melons crashes price hard. More like: first 60 at ~$225, next 60 at ~$50 = ~$16,500

**Goose Farm (8 geese, 1 farmer + 2 hands)**:
- 8 coops, 8 geese = $2,400 investment + 8 tiles
- ~23 days of 2 eggs/day/goose = 368 eggs. Eggs sell at ~$48 avg (very stable) = ~$17,664
- Minus investment ($2,400) and feed ($1,840 in grown wheat cost ~$460) = **~$14,800 profit**
- Plus fertilizer: 8 * 23 days = 184 fertilizer * ~$80 avg = $14,720
- **[HYPOTHESIS]** Goose + fertilizer farm may be one of the strongest strategies due to stable egg prices and fertilizer revenue.

**Mixed Melon + Goose**:
- 6 melon tiles + 4 goose coops
- Melons: 2 cycles * 6 * 6 * $200 avg = $14,400
- Eggs: 23 * 2 * 4 * $48 = $8,832
- Fertilizer: 4 * 23 * $80 = $7,360
- Total: ~$30,592 minus costs (~$3,500) = **~$27,000 profit**
- Requires careful tile management and multiple hands

---

*This analysis is based on the game engine source at `/Users/kyransinha/kaggriculture/.venv/lib/python3.11/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py` and the competition documentation at `/Users/kyransinha/kaggriculture/README.md`. All values were verified against source code unless marked [HYPOTHESIS].*
"},"caller":{"type":"direct"}}],"stop_reason":"tool_use","stop_sequence":null,"stop_details":null,"usage":{"input_tokens":1,"cache_creation_input_tokens":3357,"cache_read_input_tokens":37624,"output_tokens":16409,"server_tool_use":{"web_search_requests":0,"web_fetch_requests":0},"service_tier":"standard","cache_creation":{"ephemeral_1h_input_tokens":0,"ephemeral_5m_input_tokens":3357},"inference_geo":"","iterations":[],"speed":"standard"}},"requestId":"req_011CdkGMKj2U2AFEjiLqgQ2X","type":"assistant","uuid":"6486e42b-8335-46a2-9d43-28040ae8305b","timestamp":"2026-08-05T20:59:23.515Z","userType":"external","entrypoint":"cli","cwd":"/Users/kyransinha/kaggriculture","sessionId":"226da8c6-f6f2-414d-985d-3f419e11e823","version":"2.1.81","gitBranch":"HEAD","slug":"stateful-moseying-hanrahan"}
{"parentUuid":"6486e42b-8335-46a2-9d43-28040ae8305b","isSidechain":true,"promptId":"340ef00c-a6a8-4257-8e49-5d0b9b0ad74c","agentId":"a7b0677e858b06ae2","type":"user","message":{"role":"user","co

