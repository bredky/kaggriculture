# Kaggriculture: Heuristic Agent Catalogue

This document defines 50 distinct heuristic agents for the Kaggriculture farming competition. Each agent is a precise behavioural specification — not code — detailed enough for a programmer to implement directly. Agents are organised into five tiers of strategic sophistication.

Key game facts informing all designs:
- 720 turns total (24/day, 30 days). Market orders are free (up to 10/turn). Farm hands cost $1/$1/$2/$3/$5/... per hire (Fibonacci), reset daily.
- Plants die if unwatered 2 consecutive days. New seeds start with consecutive_unwatered=1, so they MUST be watered on planting day.
- Premium crops (melon, strawberry, milk, wool) crash rapidly on oversupply. Wheat and eggs are price-stable.
- Town demand drains market inventory steadily, pushing prices up over time — especially after day 10 (2x) and day 20 (4x).
- Fertilizer: free from any animal daily via COLLECT_FERTILIZER. Worth buying only for tomato/strawberry.

---

## Tier 1: Simple Single-Crop Specialists (Agents 1-10)

---

### Agent 1: Wheat Grinder
**Tier:** 1
**Core Strategy:** Grow wheat on every available tile, sell continuously, rely on wheat's price stability for consistent income.
**Crop Focus:** Wheat only
**Decision Logic:**
- Day 0: Buy 20 wheat seeds, hire 1 hand. Each day thereafter buy enough seeds to fill all empty tiles.
- Farmer and hand both follow the same loop: PLANT any empty tile within reach, then WATER all planted tiles in ascending distance order from spawn (4,4).
- Harvest any wheat tile with yield_units > 0 and age >= 2 (first_yield_day). Prioritise tiles closest to decay (age >= 5).
- Sell all wheat in shed each turn via market orders (wheat price barely moves; no reason to hold).
- Replant immediately after harvest on the same tile.
- If a tile shows consecutive_unwatered=1 and farmer has no other pressing task, move to it and WATER before doing anything else.
**Market Behaviour:** Sell all wheat in shed every turn. Buy wheat seeds to maintain full tile coverage. Never buy wheat as product.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest tiles at age >= 5 (decay risk). 3) Harvest tiles at max yield. 4) Plant empty tiles. 5) Water tiles in bonus window (days 2-4). 6) Move toward furthest unwatered tile.
**Special Mechanics Used:** 1 farm hand hired daily ($1). No fertilizer, no animals, no land expansion.
**Weaknesses:** Low profit ceiling (~$18/tile/day). No market timing. Easily out-earned by melon or animal strategies in longer games.

---

### Agent 2: Carrot Sprinter
**Tier:** 1
**Core Strategy:** Exploit carrot's fast 3-day cycle and moderate price to turn tiles over as quickly as possible.
**Crop Focus:** Carrot only
**Decision Logic:**
- Day 0: Buy 15 carrot seeds, hire 1 hand.
- Plant all available tiles immediately. Water on planting day (mandatory) and every subsequent day.
- Harvest on day 3 (max_yield_day) — yield = 3 unfertilized. Never wait past day 4 (decay starts day 4).
- Immediately replant the harvested tile the same turn if seeds are in inventory.
- Keep a rolling seed order: buy enough seeds each day to have 15 in reserve at all times.
- If carrot price drops below $15 (approaching floor fast), switch remaining turns to wheat to avoid selling into a crashed market.
**Market Behaviour:** Sell all carrots immediately on harvest. Do not hold. If carrot market inventory > I0+200 (price ~$20), pause sells for 1 day to let town demand recover price slightly.
**Farmer Actions (priority):** 1) Water plants at consecutive_unwatered=1. 2) Harvest tiles at age 3+. 3) Plant empty tiles. 4) Water tiles in bonus window (days 2-3). 5) Move toward next task.
**Special Mechanics Used:** 1 farm hand. No fertilizer, no animals. No land expansion.
**Weaknesses:** Carrot price crashes with sqrt above-I0 function — if opponent also grows carrots, prices can hit $1 quickly. No late-game scaling.

---

### Agent 3: Melon Baron
**Tier:** 1
**Core Strategy:** Plant melons on every tile, harvest at exactly day 10 (maximum yield without fertilizer), sell in small batches to preserve price.
**Crop Focus:** Melon only
**Decision Logic:**
- Day 0: Buy 8 melon seeds ($640), hire 1 hand. Plant immediately on 8 tiles closest to spawn. Water on planting day.
- Water every tile every day without exception. Melon bonus window is days 6-12; each watered day in window adds 1 yield up to max 6.
- Harvest exactly on day 10 (yield = 6). Do not wait — decay begins day 11, losing 1 unit every 2 turns.
- After harvesting, immediately replant the tile with a new melon seed if days remaining >= 12 (need 10 days to harvest + 2 buffer). Stop replanting after day 18.
- After day 18, switch empty tiles to wheat for end-game cash flow.
- Sell at most 10 melons per day. Check current melon price before selling: if price < $100, hold melons in shed and wait for price recovery (town demand will pull it back).
**Market Behaviour:** Sell max 10 melons/day in individual SELL orders. Never dump entire inventory at once. Buy seeds each day to maintain supply for 8 tiles.
**Farmer Actions (priority):** 1) Water plants at consecutive_unwatered=1. 2) Harvest tiles at age 10+. 3) Plant empty tiles. 4) Water tiles in bonus window (days 6-10). 5) Move toward tasks.
**Special Mechanics Used:** 1-2 farm hands. No fertilizer, no animals, no land expansion.
**Weaknesses:** 10-day lead time means no income until day 10. Vulnerable to opponent front-running melon market. No income diversification.

---

### Agent 4: Tomato Perennial
**Tier:** 1
**Core Strategy:** Plant tomatoes at game start, harvest all 4 production days (days 8-11), then replant only if time allows.
**Crop Focus:** Tomato only
**Decision Logic:**
- Day 0: Buy 12 tomato seeds ($600), hire 1 hand. Plant all 12 immediately on tiles closest to spawn.
- Water every tile every day. Tomato produces at days 8, 9, 10, 11 — each yields 1 unit (unfertilized).
- Harvest as soon as yield_units > 0 (from day 8 onward). Do not let yield_units hit max_held=4 without harvesting; overflow is lost.
- After all 4 productions (day 11), the plant decays. DIG immediately on day 12, replant tomato only if day <= 17 (need 8 days before game ends for at least 1 yield). Otherwise plant wheat.
- Sell harvested tomatoes immediately. Tomato price is moderately stable (sqrt above, target 0.60).
- If fewer than 6 tomato tiles are producing, supplement with wheat on remaining tiles.
**Market Behaviour:** Sell tomatoes each turn as harvested. Buy tomato seeds to maintain 12-tile coverage. Buy wheat seeds for gap-fill tiles.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest tiles with yield_units > 0. 3) DIG decayed/weed tiles. 4) Plant empty tiles. 5) Water all tiles. 6) Move.
**Special Mechanics Used:** 1 farm hand. No fertilizer. No animals. No land expansion.
**Weaknesses:** Long 8-day wait before first income. Only 1 unit per production without fertilizer — low density. Tomato price drops significantly above I0.

---

### Agent 5: Strawberry Hedge
**Tier:** 1
**Core Strategy:** Plant strawberries at game start for high-base-price ongoing yields; harvest all 4 production days (days 10, 12, 14, 16).
**Crop Focus:** Strawberry only
**Decision Logic:**
- Day 0: Buy 8 strawberry seeds ($800). Hire 1 hand. Plant all 8 on nearest tiles. Water immediately.
- Water every tile every day — strawberry dies in 2 consecutive unwatered days same as any crop.
- Harvest on days 10, 12, 14, 16. Each harvest yields 1 unit at $120 base. Sell immediately; strawberry crashes very fast (linear above, target 1.60 — ~75 units to floor).
- After day 16 decay, DIG and replant only if day <= 18 (need 10+ days). Otherwise plant wheat for end-game.
- Never sell more than 4 strawberries per day — selling 8+ in rapid succession risks crashing below $60.
- Monitor opponent farm: if opponent also has strawberry tiles, sell 1 day earlier than planned to front-run their harvest.
**Market Behaviour:** Sell 1-4 strawberries per turn. Spread sales across turns. Hold if price < $80. Buy strawberry seeds and wheat seeds as needed.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest tiles with yield_units > 0. 3) DIG post-decay tiles. 4) Plant empty tiles. 5) Water bonus-window tiles. 6) Move.
**Special Mechanics Used:** 1 farm hand. No fertilizer. No animals. No land expansion.
**Weaknesses:** $800 seed investment means negative cash flow until day 10. Extremely fragile market. Must split attention between watering and harvesting on days 10-16.

---

### Agent 6: Egg Factory
**Tier:** 1
**Core Strategy:** Build 6 goose coops, fill them with geese, care daily, harvest eggs and sell them continuously (stable price).
**Crop Focus:** No crops — goose/egg only
**Decision Logic:**
- Day 0: Buy 3 geese ($900). Hire 1 hand. Build 3 coops on tiles (4,3), (3,4), (3,3) (near shed). PICKUP GOOSE from shed, move to coop, PLACE GOOSE. Water is not needed — FEED geese daily instead.
- Days 1-2: Buy 3 more geese ($1,200). Build 3 more coops. Place all geese.
- Allocate remaining tiles (not coops) to wheat for feed supply. Target: 3+ wheat tiles to produce feed wheat.
- Each day: FEED all geese (consumes 1 wheat each), CARE for all geese (banks +1 bonus for next egg yield), HARVEST geese with yield_units > 0. COLLECT_FERTILIZER if fertilizer_available.
- Sell collected fertilizer ($100 base, linear — moderate sensitivity). Sell eggs every day.
- Geese produce daily (interval=1). With daily CARE: 2 eggs/goose/day after first production day. 6 geese = 12 eggs/day = $600/day at base price.
**Market Behaviour:** Sell all eggs each day (egg price is very stable — log above function). Sell fertilizer in batches of 5 or fewer. Buy wheat product if wheat tiles can't cover feed needs.
**Farmer Actions (priority):** 1) FEED geese at consecutive_unfed=1. 2) FEED all other geese. 3) CARE all geese. 4) HARVEST geese with yield > 0. 5) COLLECT_FERTILIZER. 6) Water wheat tiles. 7) Harvest wheat. 8) Plant wheat.
**Special Mechanics Used:** 6 goose coops, 6 geese. Farm hands for watering wheat. No land expansion needed.
**Weaknesses:** $2,100 upfront investment takes time to recoup. Geese take 4 days to first yield. Requires wheat tiles for feed, reducing crop space. Vulnerable to missed feeds.

---

### Agent 7: Milk Machine
**Tier:** 1
**Core Strategy:** Build 4 cow pastures, manage milk production with daily care, sell milk carefully to avoid crashing the fragile milk market.
**Crop Focus:** No crops — cow/milk only, with wheat for feed
**Decision Logic:**
- Day 0: Buy 2 cows ($800). Build 2 pastures adjacent to shed. PICKUP COW, PLACE on pasture. Remaining money buys wheat seeds for feed tiles.
- Day 2: Buy 2 more cows ($800). Build 2 more pastures. Place cows.
- Allocate 4+ tiles to wheat for feed. Each cow needs 1 wheat/day.
- Each day: FEED all cows (priority), CARE all cows (banks 2 bonuses between productions = 3 milk every 2 days with daily care), HARVEST cows on production days (days 8, 10, 12, ...).
- Sell milk in micro-batches: no more than 5 units per day. Milk crashes at ~76 units above I0 (linear, 1.60 target). Monitor market inventory; if milk inventory > I0+30, hold for 1-2 days.
- COLLECT_FERTILIZER from each cow daily. Sell or use on wheat tiles.
**Market Behaviour:** Sell 1-5 milk per day maximum. Sell fertilizer in small batches. Buy wheat product if running low on feed. Never dump full milk inventory at once.
**Farmer Actions (priority):** 1) FEED cows at consecutive_unfed=1. 2) FEED all cows. 3) CARE cows. 4) HARVEST cows with yield > 0. 5) COLLECT_FERTILIZER. 6) Water/harvest wheat. 7) Plant wheat.
**Special Mechanics Used:** 4 cow pastures. Farm hand for wheat management. No land expansion.
**Weaknesses:** $1,600 investment plus wheat overhead. 8-day wait to first milk. Milk market crashes extremely fast — even one over-sell erodes prices.

---

### Agent 8: Wool Weaver
**Tier:** 1
**Core Strategy:** Build 3 sheep pastures, care for sheep daily, sell wool very slowly since wool crashes at only ~59 units above I0.
**Crop Focus:** No crops — sheep/wool only, with wheat for feed
**Decision Logic:**
- Day 0: Buy 2 sheep ($1,000). Build 2 pastures near shed. PICKUP SHEEP, PLACE. Buy wheat seeds for feed.
- Day 2: Buy 1 more sheep ($500). Build 1 more pasture. Place sheep.
- Allocate 4 tiles to wheat for feed supply (3 sheep = 3 wheat/day needed).
- Each day: FEED all sheep (prevent escape at consecutive_unfed >= 2), CARE all sheep (banks up to 3 bonuses over 3-day interval = 4 wool per production with full care), HARVEST on production days (days 6, 9, 12, ...).
- Wool price: base $200, sq function above I0, crashes at ~59 units. Sell maximum 3 wool per day. If wool price < $100, hold and let town demand (Yarn Store = 12/day) restore the price.
- COLLECT_FERTILIZER daily. Use on wheat or sell.
**Market Behaviour:** Sell at most 3 wool per day. Check wool market inventory before each sell — stop selling if inventory > I0+40. Sell fertilizer in batches of 3. Buy wheat product for feed gaps.
**Farmer Actions (priority):** 1) FEED sheep at consecutive_unfed=1. 2) FEED all sheep. 3) CARE sheep. 4) HARVEST sheep on yield days. 5) COLLECT_FERTILIZER. 6) Water/harvest/plant wheat.
**Special Mechanics Used:** 3 sheep pastures, 1 farm hand. No land expansion.
**Weaknesses:** $1,500 investment. Wool market implodes with even modest supply — hard to realise full value. Sheep have 3-day production interval so care management is complex.

---

### Agent 9: Wheat Feeder
**Tier:** 1
**Core Strategy:** Grow wheat exclusively but only to sell into late-game price spikes driven by town demand (wheat appears in 5 shops), holding inventory until after day 20.
**Crop Focus:** Wheat only, stockpile-focused
**Decision Logic:**
- Days 0-19: Plant wheat, water, harvest. Store ALL harvested wheat in shed — do not sell yet. Use shed capacity (100 items) as a holding buffer.
- After day 20, town center demand is 8/day and up to 5 wheat-consuming shops are active (potential 30-38 wheat/day drain). Wheat price rises above base.
- Begin selling on day 20: check current wheat price. If price > $28 (above base by 12%), sell up to 20/day. If price > $35, sell 50/day.
- Continue growing and immediately selling wheat from day 20 onward.
- Hire 2 hands from day 0 to maximise tile coverage and wheat accumulation.
**Market Behaviour:** Hold all wheat until day 20. Then sell aggressively based on price thresholds. Never buy wheat as product. Monitor wheat market inventory to gauge price direction.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest mature wheat (age >= 4). 3) DROP inventory to shed (keep shed topped up to 100). 4) Plant empty tiles. 5) Water bonus-window tiles. 6) Move.
**Special Mechanics Used:** 2 farm hands hired daily. No animals, no fertilizer, no land expansion.
**Weaknesses:** Near-zero income for first 20 days — must survive on $3,000 starting money. If both players hold wheat, selling competition after day 20 hurts both. Requires careful shed capacity management.

---

### Agent 10: Fertilizer Seller
**Tier:** 1
**Core Strategy:** Buy 5 geese purely for their daily fertilizer output, sell fertilizer at base price, supplement with wheat.
**Crop Focus:** Wheat for feed; goose fertilizer as primary revenue
**Decision Logic:**
- Day 0: Buy 3 geese ($900). Build 3 coops on tiles near shed. Place geese. Buy 5 wheat seeds.
- Day 1: Buy 2 more geese ($800). Build 2 coops. Place geese. 5 geese generate 5 fertilizer/day.
- Each day: FEED all 5 geese (consumes 5 wheat). COLLECT_FERTILIZER from every goose that has fertilizer_available=true. Sell fertilizer in shed.
- Fertilizer base price $100, linear both sides (target 0.40). Selling 5/day drives inventory up ~35/day. Price stays above $80 for many days. Aim to sell before inventory > I0+100 (price ~$80).
- Also HARVEST eggs from geese and CARE for geese to get 2 eggs/day/goose as secondary revenue.
- Wheat tiles: 4 tiles minimum to cover 5 geese. Plant wheat in remaining space, harvest for both feed and sale.
**Market Behaviour:** Sell all fertilizer daily (up to 5). Sell eggs daily. Sell wheat. Buy wheat seeds or product if feed is short.
**Farmer Actions (priority):** 1) FEED geese at consecutive_unfed=1. 2) FEED all geese. 3) COLLECT_FERTILIZER. 4) CARE geese. 5) HARVEST eggs. 6) Water/harvest wheat. 7) Plant wheat.
**Special Mechanics Used:** 5 goose coops. Farm hand. No land expansion.
**Weaknesses:** High upfront cost. Fertilizer market is moderate sensitivity — selling 50+ units drops price notably. Egg + fertilizer double revenue requires good turn management.

---

## Tier 2: Moderate Complexity — 2-Crop Mixes or Basic Market Timing (Agents 11-20)

---

### Agent 11: Wheat-Melon Alternator
**Tier:** 2
**Core Strategy:** Use wheat for early cash flow and continuous end-game income while melon cycles provide large periodic payouts.
**Crop Focus:** Wheat (early + late) and Melon (mid-game)
**Decision Logic:**
- Days 0-2: Plant 10 wheat tiles (near shed), hire 2 hands. Water all.
- Day 2: Buy 6 melon seeds. Plant on remaining 6 tiles closest to shed corner (tiles need 10 days of watering).
- Days 2-10: Water wheat daily, harvest wheat cycles, sell wheat. Water melons daily.
- Day 10: Harvest all 6 melon tiles (yield=6 each = 36 melons). Sell in batches of 6/day over 6 days.
- Replant wheat on melon tiles immediately after harvest. Keep wheat cycling through late game.
- Day 10-20: Second melon cycle — plant 6 melons on non-wheat tiles. Harvest day 20. Sell in batches.
- After day 20: All tiles become wheat. Sell everything. No more melon plants — not enough time.
- Hire 2 hands throughout for watering coverage.
**Market Behaviour:** Wheat: sell all immediately. Melon: sell max 6/day, check price first — stop if < $120. Buy wheat seeds continuously. Buy melon seeds before each planting wave.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest melon tiles at age 10+. 3) Harvest wheat at age 4+. 4) Plant empty tiles (melon or wheat per schedule). 5) Water bonus windows. 6) Move.
**Special Mechanics Used:** 2 farm hands. No animals, no fertilizer, no land expansion.
**Weaknesses:** Melon planting on day 10 requires careful fund management. If wheat profits are low, can't afford melon seeds. Two-crop timing requires precise scheduling.

---

### Agent 12: Carrot-Tomato Relay
**Tier:** 2
**Core Strategy:** Split tiles between fast-cycling carrots (cash flow) and tomatoes (ongoing yield), selling into complementary market windows.
**Crop Focus:** Carrot (12 tiles) and Tomato (8 tiles)
**Decision Logic:**
- Day 0: Buy 12 carrot seeds ($240) and 8 tomato seeds ($400). Hire 1 hand. Plant all.
- Carrot zone: 12 tiles closest to shed. 3-day cycle, replant immediately after harvest. Never stop cycling.
- Tomato zone: 8 tiles in the far half of the quadrant. Plant on day 0, water daily, harvest days 8-11.
- Carrot provides daily income from day 2 onward. Tomato provides burst income days 8-11.
- After tomato decay (day 12): DIG, plant tomato again only if day <= 21. Otherwise switch to carrot.
- If carrot price drops below $18, temporarily hold 1-2 days; tomato zone provides income buffer.
- Hire 1 additional hand on days 8-12 (tomato harvest period) to manage both zones simultaneously.
**Market Behaviour:** Sell carrots daily (all). Sell tomatoes as harvested each day. Monitor both prices; shift selling order to whichever is higher. Buy seeds to maintain both zones.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest ripe tiles (tomato days 8-11, carrot day 3+). 3) Plant empty tiles (carrot first if funds limited, tomato if day < 21). 4) Water bonus-window tiles. 5) Move.
**Special Mechanics Used:** 1-2 farm hands depending on workload. No animals, no fertilizer.
**Weaknesses:** $640 day-0 seed cost is large. Two-zone movement increases travel overhead. Tomato yields only 4 units total over 13 days vs carrot's faster turnover.

---

### Agent 13: Melon-Strawberry Premium Pair
**Tier:** 2
**Core Strategy:** Capture high base prices of both melon ($250) and strawberry ($120) by staggering harvest windows so sales don't overlap.
**Crop Focus:** Melon (8 tiles) and Strawberry (6 tiles)
**Decision Logic:**
- Day 0: Buy 8 melon seeds ($640) and 4 strawberry seeds ($400). Total $1,040. Hire 1 hand.
- Plant all melon immediately. Plant strawberries on day 2 (after securing cash from starting money).
- Melon harvests day 10: sell 3/day over 16 days (very slow drip to preserve price).
- Strawberry yields at days 10, 12, 14, 16 from planting — if planted day 2, yields days 12, 14, 16, 18. Sell 2/day.
- These stagger: strawberry fills gaps between melon sell days. Neither market gets fully crashed alone.
- After day 18: DIG strawberry, plant wheat on those tiles. Second melon cycle on melon tiles (harvest day 20).
- Sell second melon batch slowly days 20-29.
- Hire 2 hands from day 8 onward to manage the heavy harvest window.
**Market Behaviour:** Melon: sell max 3/day, pause if price < $150. Strawberry: sell max 2/day, pause if price < $80. Never sell both in same turn — alternate melon turn, strawberry turn.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest ready tiles. 3) Plant replacements. 4) Water bonus windows. 5) Move.
**Special Mechanics Used:** 2 farm hands (hired from day 8). No animals, no fertilizer.
**Weaknesses:** $1,040 day-0 cost strains starting $3,000. Very low cash flow days 0-10. If opponent also targets premium crops, coordinated selling crashes both markets.

---

### Agent 14: Wheat Flood + Market Timing
**Tier:** 2
**Core Strategy:** Grow as much wheat as possible, but sell only when wheat price is above $30 (scarcity zone), holding during low-price periods.
**Crop Focus:** Wheat only, with active price monitoring
**Decision Logic:**
- Days 0-29: Always have maximum wheat tiles planted (all 25 NW tiles). Hire 2 hands daily for coverage.
- Harvest all wheat at max yield (day 4). DO NOT SELL immediately — store in shed.
- Each turn, check wheat market price. If price >= $30: sell up to 30/day. If price >= $35: sell up to 60/day. If price < $25: hold.
- When holding, watch wheat market inventory: if inventory < I0-200 (price rising due to town demand), begin selling.
- Hard sell rule: on day 28-29, sell everything regardless of price — unsold goods score nothing.
- Monitor when wheat-consuming shops unlock (Bakery, Pizza Shop, Brunch Spot, Ice Cream Shop, Farmers Market). Each unlock boosts demand and pushes price up.
**Market Behaviour:** Price-gated selling. Target sell above $30. Bulk sell on days 28-29. Never buy wheat as product.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest age >= 4. 3) DROP to shed (keep inventory flowing). 4) Plant empty tiles. 5) Water bonus window. 6) Move.
**Special Mechanics Used:** 2 farm hands. No animals, no fertilizer, no land expansion.
**Weaknesses:** Shed capacity (100 items) limits stockpiling. Holding wheat risks opponent selling first and lowering price. Requires memory of shop unlock schedule to time well.

---

### Agent 15: Early Bird Melon
**Tier:** 2
**Core Strategy:** Plant melons with fertilizer to harvest 2 days early (day 8 instead of day 10) and sell before opponent melons hit the market.
**Crop Focus:** Melon only, fertilizer-enhanced
**Decision Logic:**
- Day 0: Buy 8 melon seeds ($640), buy 3 fertilizer ($300). Hire 1 hand. Total $940 of $3,000. Plant all 8 melons.
- Days 0-7: Water all melons daily. On day 5 (start of fertilizer bonus window to hit cap by day 8): FERTILIZE each melon tile one per turn. Fertilizing day 5 covers days 5,6,7 (2 bonus/day instead of 1). Melon reaches yield=6 at day 8 (1 + 2+2+2+2 = 9 capped at 6 — actually hits cap faster). Harvest day 8.
- Sell all 48 melons (8 tiles x 6) starting day 8, before opponent's unfertilized melons mature on day 10. Sell in batches of 8/day over 6 days.
- Replant melons day 8 (cycle 2, no fertilizer needed — harvest day 18). Sell days 18-25.
- After day 18 second harvest: switch to wheat for remaining days.
**Market Behaviour:** Sell 8 melons/day starting day 8. Front-run any opponent melon harvest. If price < $150 at day 8, hold 1 day and check again. Sell everything by day 25.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) FERTILIZE melon tiles on day 5 (use PICKUP fertilizer from shed first). 3) Harvest melon at age 8+. 4) Plant empty tiles. 5) Water bonus window. 6) Move.
**Special Mechanics Used:** Fertilizer (bought). 1 farm hand. No animals.
**Weaknesses:** $940 day-0 cost. Fertilizer timing must be precise — fertilize too early and the 3-day window is wasted; fertilize too late and cap isn't reached by day 8. Opponent may also use fertilizer.

---

### Agent 16: Goose-Wheat Dual Income
**Tier:** 2
**Core Strategy:** Combine stable egg revenue from geese with wheat cycling to fund operations and provide market-crash-proof baseline income.
**Crop Focus:** Wheat (feed + sale) and Goose/Egg
**Decision Logic:**
- Day 0: Buy 2 geese ($600), build 2 coops adjacent to shed, place geese. Buy 10 wheat seeds. Plant wheat on remaining tiles. Hire 1 hand.
- Day 3: Buy 2 more geese ($800), build 2 more coops, place. Total 4 geese = 4 eggs + 4 fertilizer/day.
- Wheat cycles fund ongoing goose purchases and seed costs. Geese provide daily egg income from day 4.
- CARE for all geese daily = 2 eggs/goose/day after day 4 = 8 eggs/day = $400/day at base price.
- COLLECT_FERTILIZER daily (4/day). Apply 1 fertilizer to each wheat tile during bonus window (days 2-4) for +2 extra wheat per tile. Sell remaining fertilizer.
- Sell eggs immediately every day (stable price). Sell wheat as harvested. Sell fertilizer in batches.
**Market Behaviour:** Sell all eggs daily. Sell all wheat daily. Sell fertilizer in groups of 3-4/day. Buy wheat seeds and wheat product (if needed for feed). Hire 1-2 hands daily.
**Farmer Actions (priority):** 1) FEED geese. 2) CARE geese. 3) HARVEST geese. 4) COLLECT_FERTILIZER. 5) FERTILIZE wheat tiles (during window). 6) Water wheat. 7) Harvest wheat. 8) Plant wheat. 9) Move.
**Special Mechanics Used:** 4 goose coops. Farm hand. Fertilizer applied to wheat. No land expansion.
**Weaknesses:** $1,400 goose investment reduces initial crop capacity. Requires careful turn allocation to service both geese and wheat. Fertilizer on wheat gives marginal ROI ($50 value at base price).

---

### Agent 17: Tomato Fertilizer Maximizer
**Tier:** 2
**Core Strategy:** Grow tomatoes and apply fertilizer on each of the 4 production days to double yield to 8 total units per plant.
**Crop Focus:** Tomato (fertilizer-doubled yield)
**Decision Logic:**
- Day 0: Buy 10 tomato seeds ($500), buy 5 fertilizer ($500). Hire 1 hand. Plant all 10 tomatoes.
- Water daily. On day 7 (one day before first production on day 8): FERTILIZE each tomato tile (covers days 7,8,9). This covers 3 of 4 production days. On day 10, FERTILIZE again (covers days 10,11). Each fertilized+watered production day yields 2 instead of 1.
- Total yield with this approach: days 8,9,10,11 all fertilized = 2+2+2+2 = 8 units per plant. 10 plants = 80 tomatoes vs 40 unfertilized.
- Buy fertilizer from shed or market as needed (2 fertilizer per plant = 20 fertilizer total). If market fertilizer price > $120, skip second fertilization.
- Harvest daily on days 8-11. Sell tomatoes at moderate pace (10-15/day). After decay, DIG and replant tomato only if day <= 17, else wheat.
**Market Behaviour:** Buy fertilizer on day 6-7 (before first application). Sell tomatoes in batches of 10-15/day. Sell remaining fertilizer if unused.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) FERTILIZE tomato tiles on days 7 and 10 (PICKUP fertilizer from shed, move to tile, FERTILIZE). 3) Harvest tiles with yield_units > 0. 4) Water all tiles. 5) DIG decayed tiles. 6) Replant. 7) Move.
**Special Mechanics Used:** Fertilizer (bought). 1 farm hand. No animals.
**Weaknesses:** $1,000 day-0 cost. Fertilizer logistics (PICKUP, carry, FERTILIZE) consumes turns. If tomato price drops significantly, extra yield doesn't compensate for fertilizer cost.

---

### Agent 18: NE Quadrant Expander
**Tier:** 2
**Core Strategy:** Buy the NE quadrant on day 5, double tile count, and run wheat on all 50 tiles with hired hands, maximizing total throughput.
**Crop Focus:** Wheat (primary), using all 50 tiles post-expansion
**Decision Logic:**
- Days 0-4: Grow wheat on 15 NW tiles. Hire 2 hands. Sell wheat. Accumulate toward $1,000 for NE quadrant.
- Day 5: Issue BUY_LAND for NE quadrant ($1,000). Now have 50 tiles.
- Days 5 onward: Hire 3 hands daily ($4 total). Farmer covers NW. 3 hands cover NE quadrant and further NW tiles.
- Assign hands to zones: Hand 1 covers NW rows 0-2, Hand 2 covers NW rows 3-4 + NE edge, Hand 3 covers NE interior.
- Each hand's daily loop: PLANT empty tiles near their zone, WATER all tiles in zone, HARVEST mature tiles, DROP at shed (must be adjacent), then repeat.
- With 50 tiles and 4 units (farmer + 3 hands): 96 actions/day. Can service ~35-40 tiles actively.
- Sell all wheat daily. Wheat price is very stable so no need to time sales.
**Market Behaviour:** Sell all wheat every day. Buy wheat seeds to fill 50 tiles. Hire 3 hands daily. Buy NE quadrant on day 5.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest mature tiles. 3) Plant empty tiles. 4) Water bonus-window tiles. 5) Move within NW zone.
**Special Mechanics Used:** 3 farm hands daily. BUY_LAND (NE quadrant on day 5). No animals, no fertilizer.
**Weaknesses:** $1,000 land cost + $4/day hands reduces ROI vs simply optimizing 25 tiles. NE quadrant has higher movement overhead. Wheat income ceiling limits upside vs premium crops.

---

### Agent 19: Late-Game Strawberry Spike
**Tier:** 2
**Core Strategy:** Plant strawberries early, sell all 4 yields into the day-20 town demand spike when the town center consumes 4x more product.
**Crop Focus:** Strawberry (planted early, sold late)
**Decision Logic:**
- Day 0: Buy 10 strawberry seeds ($1,000), hire 1 hand. Plant all 10. Water immediately.
- Days 0-9: Water daily, grow wheat on 3-5 extra tiles for cash flow. Hire hand daily ($1).
- Day 10: First strawberry yield. DO NOT SELL — store in shed. Continue watering.
- Day 12: Second yield. Store. Day 14: Third. Store. Day 16: Fourth. Store.
- Day 18: DIG all decayed strawberry tiles, plant wheat.
- Day 20: Town center demand hits 4x. Begin selling strawberry stockpile: sell 3/day (strawberry crashes easily — linear above, target 1.60). Check price each day.
- If strawberry price > $150 (scarcity due to town drain), sell 5/day.
- Sell all strawberries by day 28. Final 2 days sell wheat.
**Market Behaviour:** Hold strawberries days 10-19. Sell 3-5/day from day 20 onward. Sell wheat daily throughout. Buy strawberry and wheat seeds on day 0.
**Farmer Actions (priority):** 1) Water tiles at consecutive_unwatered=1. 2) Harvest strawberry yield_units > 0 (store, don't sell yet). 3) Harvest wheat. 4) DROP to shed. 5) Plant empty tiles. 6) Water bonus windows. 7) Move.
**Special Mechanics Used:** 1-2 farm hands. No animals, no fertilizer.
**Weaknesses:** $1,000 seed cost day 0. Shed capacity (100 items) limits stockpile — 10 plants x 4 yields = 40 strawberries (fine). Zero strawberry revenue until day 20.

---

### Agent 20: Carrot-Wheat Market Watcher
**Tier:** 2
**Core Strategy:** Dynamically allocate tiles between wheat and carrot each cycle based on current market prices, always favouring whichever is more profitable per turn.
**Crop Focus:** Wheat and Carrot (dynamic allocation)
**Decision Logic:**
- Day 0: Buy 10 wheat seeds and 5 carrot seeds. Hire 1 hand.
- Each planting decision: compute expected profit/turn for wheat (price x 4 units / 5 days = price x 0.8/day) vs carrot (price x 3 units / 4 days = price x 0.75/day). If wheat_score > carrot_score: plant wheat. Else: plant carrot.
- Example: wheat at $25 = score 20; carrot at $35 = score 26.25 — plant carrot. If carrot drops to $20: wheat score 20 > carrot score 15 — switch to wheat.
- Rebalance each planting cycle: after harvesting, plant the currently higher-scoring crop on that tile.
- Check prices every turn. If carrot price < $20 (market dumped), immediately switch all new plantings to wheat.
- Sell everything immediately on harvest. No holding.
- Hire 1-2 hands based on tile count active (hire 2nd hand only if > 15 active tiles).
**Market Behaviour:** Sell harvested goods immediately. Buy seeds each day based on current allocation plan. Hire 1-2 hands.
**Farmer Actions (priority):** 1) Water at consecutive_unwatered=1. 2) Harvest mature tiles. 3) Plant using current scoring allocation. 4) Water bonus windows. 5) Move.
**Special Mechanics Used:** 1-2 farm hands. Dynamic crop switching. No animals, no fertilizer.
**Weaknesses:** Switching crops requires buying different seeds — seed inventory management complexity. Market scoring model is simple and may not account for future price trajectory.

---

## Tier 3: Multi-System Strategies (Agents 21-30)

---

### Agent 21: Goose Fertilizer Melon Engine
**Tier:** 3
**Core Strategy:** Use goose fertilizer to enable early melon harvests, creating a reinforcing loop: geese produce fertilizer, fertilizer accelerates melon cycles, melon cash buys more geese.
**Crop Focus:** Melon (primary), Goose/Egg (secondary), Wheat (feed)
**Decision Logic:**
- Day 0: Buy 2 geese ($600), build 2 coops, place. Buy 8 melon seeds ($640). Hire 2 hands. Plant 8 melons. Plant 2 wheat tiles for feed.
- Days 1-3: Water melons. FEED, CARE geese daily. COLLECT_FERTILIZER starting day 1 (2/day free).
- Day 5: Apply fertilizer to 4 melon tiles (PICKUP fertilizer from shed, walk to tile, FERTILIZE). By day 8, those 4 tiles hit max yield (6). Harvest day 8. Free 4 tiles.
- Days 8-10: Replant those 4 tiles with melon. Other 4 melon tiles (unfertilized) harvest day 10.
- Day 10 onward: rolling melon pipeline with 2-day stagger between batches.
- Sell harvested melons in batches of 4-6/day. Sell eggs daily (stable price). Use accumulated fertilizer to enable early harvests in each cycle.
- Buy 2 more geese on day 5 with early melon profits. 4 geese = 4 fertilizer/day → can fertilize more tiles.
**Market Behaviour:** Sell 4-6 melons/day starting day 8. Sell eggs daily. Sell excess fertilizer at $90+ only. Buy melon seeds every 8-10 days. Buy wheat for feed if needed.
**Farmer Actions (priority):** 1) FEED geese. 2) CARE geese. 3) HARVEST geese. 4) COLLECT_FERTILIZER. 5) FERTILIZE melon tiles on day 5 per batch. 6) Water melons at consecutive_unwatered=1. 7) Harvest melons. 8) Water all melons. 9) Plant empty tiles. 10) Move.
**Special Mechanics Used:** 2-4 goose coops. Farm hands (2). Fertilizer from animals. Staggered melon cycles. No land expansion.
**Weaknesses:** Complex multi-system turn allocation. COLLECT_FERTILIZER and FERTILIZE both cost turns. If geese escape (missed feed), fertilizer supply collapses. High day-0 cost ($1,240+).

---

### Agent 22: Cow Milk Drip Seller
**Tier:** 3
**Core Strategy:** Run 3 cows with daily care (3 milk/2 days per cow), sell milk in micro-batches across the full season while growing wheat for feed and using cow fertilizer on crops.
**Crop Focus:** Wheat (feed + fertilizer target), Cow/Milk (primary revenue)
**Decision Logic:**
- Day 0: Buy 2 cows ($800). Build 2 pastures near shed. Place. Buy 10 wheat seeds. Hire 2 hands.
- Day 4: Buy 1 more cow ($400). Build pasture. Place. Total 3 cows.
- Dedicate 6 wheat tiles to feed (3 cows x 1 wheat/day but wheat cycles 4/5 days = need 4-5 tiles for steady supply). Remaining tiles grow wheat for sale.
- Daily: FEED all 3 cows. CARE all 3 cows (bank 2 bonuses per 2-day interval = 3 milk per production). HARVEST on production days. COLLECT_FERTILIZER (3/day).
- Milk sell rule: sell exactly 3 units/day spread across 3 separate SELL orders in consecutive turns. Milk crashes at ~76 units (linear, 1.60 target) — 3/day = 90 units/month = risky. Monitor: if milk inventory > I0+25, sell only 1/day.
- Apply collected fertilizer to wheat tiles during bonus window to increase wheat yield. Sell unused fertilizer.
**Market Behaviour:** Sell 1-3 milk/day (price-gated). Sell wheat daily. Sell fertilizer in batches of 3. Buy wheat seeds and cows. Hire 2 hands daily.
**Farmer Actions (priority):** 1) FEED cows. 2) CARE cows. 3) HARVEST milk. 4) COLLECT_FERTILIZER. 5) FERTILIZE wheat tiles (days 2-4 per cycle). 6) Water wheat. 7) Harvest wheat. 8) Plant wheat. 9) Move.
**Special Mechanics Used:** 3 cow pastures. 2 farm hands. Fertilizer used on wheat. No land expansion.
**Weaknesses:** Milk market is volatile — even careful selling can crash prices if opponent also sells milk. Three cows plus wheat tiles require significant movement across the farm.

---

### Agent 23: Three-Crop Rotation
**Tier:** 3
**Core Strategy:** Run wheat, carrot, and melon simultaneously in three dedicated zones, cycling each independently on its own schedule.
**Crop Focus:** Wheat (8 tiles), Carrot (8 tiles), Melon (6 tiles), NW quadrant + NE if affordable
**Decision Logic:**
- Farm layout: tiles (4,0)-(4,4) = wheat zone (5 tiles along shed column). Tiles (0,0)-(2,4) = carrot zone (10 tiles). Tiles (3,0)-(4,2) = melon zone (6 tiles).
- Day 0: Buy seeds for all three zones. Plant all. Hire 2 hands. Assign Hand 1 to wheat zone, Hand 2 to carrot zone, Farmer covers melon zone + shed duties.
- Each zone runs its own cycle: wheat harvests day 4 (replant immediately), carrot harvests day 3 (replant immediately), melon harvests day 10 (replant for cycle 2).
- Sell carrots and wheat daily as harvested. Melon: sell 3/day in batches.
- If any zone price crashes below half base (carrot < $17, wheat < $12, melon < $125), temporarily pause sells on that product, switch turns to harvest the other zones faster.
- Buy NE quadrant on day 8 if money >= $1,500 (earned from early wheat/carrot cycles). Expand all zones.
**Market Behaviour:** Sell wheat and carrot daily. Sell melon at 3/day. Price-gated pauses on any market crash. Buy seeds for all three crop types. Buy NE land on day 8 if affordable.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1 tiles. 2) Harvest mature melons (highest value). 3) Harvest mature carrots. 4) Harvest mature wheat. 5) Plant empties by zone. 6) Water bonus windows. 7) Move.
**Special Mechanics Used:** 2 farm hands with zone assignments. Land expansion (conditional). No animals, no fertilizer.
**Weaknesses:** Zone-based layout requires movement between zones. 3 different seed types to buy/manage. Melon zone is small (6 tiles), limiting melon revenue. Hand zone assignment requires careful pathing.

---

### Agent 24: Sheep Wool + Wheat Synergy
**Tier:** 3
**Core Strategy:** Run 4 sheep for wool revenue, use their fertilizer on wheat to increase wheat yield, and sell wool very slowly to avoid crashing the fragile wool market.
**Crop Focus:** Sheep/Wool (primary), Wheat (feed + fertilizer-enhanced)
**Decision Logic:**
- Day 0: Buy 2 sheep ($1,000). Build 2 pastures near shed. Place. Buy 8 wheat seeds. Hire 2 hands.
- Day 3: Buy 2 more sheep ($1,000). Build 2 pastures. Place. Total 4 sheep.
- 4 sheep need 4 wheat/day. 8 wheat tiles (cycle 4 every 5 days) = 6.4 wheat/day — sufficient. Sell surplus wheat.
- Daily: FEED all 4 sheep. CARE all 4 sheep (banks 3 bonuses per 3-day interval = 4 wool per production). HARVEST on production days. COLLECT_FERTILIZER (4/day).
- Wool sell rule: maximum 2 wool/day. Wool crashes at ~59 units (sq function). 2/day x 24 days = 48 units — stays below crash threshold. Monitor wool market inventory. If inventory > I0+30, sell 1/day.
- Apply 2 fertilizer/day to wheat tiles during bonus window (doubles wheat yield for those tiles).
- Sell wheat daily, sell fertilizer surplus at $90+.
**Market Behaviour:** Sell 2 wool/day max. Sell wheat daily. Sell excess fertilizer. Buy sheep and wheat seeds. Hire 2 hands daily.
**Farmer Actions (priority):** 1) FEED sheep. 2) CARE sheep. 3) HARVEST wool. 4) COLLECT_FERTILIZER. 5) FERTILIZE wheat (during bonus window). 6) Water wheat. 7) Harvest wheat. 8) Plant wheat. 9) Move.
**Special Mechanics Used:** 4 sheep pastures. 2 farm hands. Fertilizer on wheat. No land expansion.
**Weaknesses:** $2,000 sheep investment very high. Wool market collapses easily — slow 2/day selling means wool accumulates in shed (takes ~20 days to sell 40 units). Requires 8 wheat tiles to feed all 4 sheep.

---

### Agent 25: Strawberry-Egg Cafe Exploit
**Tier:** 3
**Core Strategy:** Target the Brunch Spot and Ice Cream Shop town buildings which demand both eggs and strawberries, increasing demand for both — then sell into that boosted demand.
**Crop Focus:** Strawberry (ongoing), Goose/Egg (ongoing), Wheat (feed)
**Decision Logic:**
- Day 0: Buy 6 strawberry seeds ($600). Buy 2 geese ($600). Build 2 coops. Place geese. Buy 4 wheat seeds. Hire 2 hands.
- Plant strawberries on 6 tiles. Plant wheat on 4 tiles. Water all.
- Days 0-9: FEED and CARE geese. Water/harvest wheat for feed. Water strawberries.
- Monitor town shop unlocks each day. Track which shops have unlocked. When Brunch Spot or Ice Cream Shop unlocks, increase both strawberry and egg sell rate (higher demand raises prices).
- Day 10: First strawberry yield. Sell 2 strawberries/day. Egg production since day 4 (sell all daily).
- Adjust strawberry sell rate based on active shop count: 1 shop = sell 2/day, 2 shops = sell 3/day, 3+ shops = sell 4/day.
- Hire 3rd hand on days 10-16 to manage simultaneous strawberry harvests and goose duties.
**Market Behaviour:** Sell eggs daily (stable, price doesn't matter much). Sell strawberries at rate based on active shop count (1-4/day). Sell fertilizer at $80+. Buy seeds and geese as needed.
**Farmer Actions (priority):** 1) FEED geese. 2) CARE geese. 3) HARVEST geese. 4) COLLECT_FERTILIZER. 5) Water strawberries at consecutive_unwatered=1. 6) Harvest strawberry yields. 7) Water all tiles. 8) Harvest/plant wheat. 9) Move.
**Special Mechanics Used:** 2 goose coops. 2-3 farm hands. Town shop monitoring. No fertilizer on crops. No land expansion.
**Weaknesses:** Shop unlock is random — may not get Brunch Spot or Ice Cream Shop until late. Strawberry market is fragile; selling even 4/day can crash it. High upfront cost ($1,200+).

---

### Agent 26: Land Baron
**Tier:** 3
**Core Strategy:** Buy NE and SW quadrants aggressively, hire 5+ hands, and run high-density wheat across all 75 tiles for massive throughput.
**Crop Focus:** Wheat on 3 quadrants (75 tiles)
**Decision Logic:**
- Days 0-4: Grow wheat on 15 NW tiles. Hire 3 hands. Sell wheat. Accumulate cash.
- Day 5: Buy NE quadrant ($1,000). Hire 4 hands ($7). Assign each hand to a quadrant sector.
- Day 10: Buy SW quadrant ($2,000). Now 75 tiles. Hire 5 hands ($12). Each hand covers 12-15 tiles.
- Farmer stays near shed for market operations. Hands handle all planting, watering, harvesting.
- Hand assignment: Hand 1-2 cover NW, Hand 3-4 cover NE, Hand 5 covers SW perimeter, Farmer covers SW tiles near shed.
- Each hand's daily loop: plant empty tiles, water consecutive_unwatered=1 tiles, water bonus-window tiles, harvest mature tiles, return to shed-adjacent tile to drop inventory before day end.
- 75 tiles x 4 wheat x $22 avg / 5 days = $13,200/cycle = $2,640/day revenue at 3 cycles/15 days.
**Market Behaviour:** Sell all wheat daily. Buy wheat seeds each day to fill 75 tiles. Buy NE and SW land. Hire 5 hands daily from day 10. Hire 3-4 from days 5-9.
**Farmer Actions (priority):** 1) Sell via market orders. 2) Buy seeds and land. 3) Water nearby tiles at risk. 4) Harvest nearby tiles. 5) Move to next task.
**Special Mechanics Used:** BUY_LAND (NE + SW). 5 farm hands hired from day 10. No animals, no fertilizer.
**Weaknesses:** SW quadrant barely breaks even ($2,000 cost, ~24 days to recoup on wheat). Hand management across 3 quadrants complex. SE quadrant ($4,000) is never worth it. Weed spawns increase with unlocked empty tiles.

---

### Agent 27: Melon-Goose Portfolio
**Tier:** 3
**Core Strategy:** Combine 2 melon cycles for large payouts with 4 geese for stable daily income and free fertilizer to accelerate melon cycles.
**Crop Focus:** Melon (10 tiles, 2 cycles), Goose/Egg (4 coops), Wheat (feed)
**Decision Logic:**
- Day 0: Buy 2 geese ($600), build 2 coops near shed. Buy 6 melon seeds ($480). Buy 3 wheat seeds. Hire 2 hands. Plant melons. Plant wheat.
- Day 2: Buy 2 more geese ($800). Build 2 more coops. Place. Total 4 geese + 6 melons + 3 wheat.
- Days 1-5: Water melons, FEED/CARE all 4 geese, COLLECT_FERTILIZER (4/day).
- Day 5: Apply fertilizer to 4 melon tiles (one per turn). Collect 4 more fertilizer next day, apply to remaining 2 + save 2. By day 8: 4 fertilized melons hit max yield (6). Harvest.
- Day 8-10: Sell first 24 melons slowly (3/day). Replant 4 tiles with melon (cycle 2). Remaining 2 melon tiles harvest day 10 (unfertilized). Sell those.
- Day 10 onward: 4 geese producing 2 eggs/day each = 8 eggs/day. Sell eggs daily.
- Day 18: Second melon harvest (4 tiles, fertilized = day 16; 2 tiles unfertilized = day 20). Sell slowly.
**Market Behaviour:** Sell 3 melons/day starting day 8. Sell all eggs daily. Sell fertilizer at $90+. Buy wheat for feed if needed.
**Farmer Actions (priority):** 1) FEED all geese. 2) CARE geese. 3) HARVEST geese. 4) COLLECT_FERTILIZER. 5) FERTILIZE melon tiles on day 5 per batch. 6) Water melons (consecutive_unwatered=1 first). 7) Harvest melons at max. 8) Plant empty tiles. 9) Water wheat. 10) Move.
**Special Mechanics Used:** 4 goose coops. Fertilizer from animals applied to melons. 2 farm hands. Staggered melon cycles. No land expansion.
**Weaknesses:** Complex multi-system — highest single-turn priority mistake (e.g., missing a goose feed) can cascade. Day-0 cost $1,080+ leaves thin cash buffer. 10+ melon tiles require 2 hands for watering coverage.

---

### Agent 28: Shop-Responsive Diversifier
**Tier:** 3
**Core Strategy:** Monitor town shop unlocks at days 3, 6, 9, 12, 15, 18 and dynamically plant whichever crops/animals have the most upcoming demand boosts.
**Crop Focus:** Dynamic — responsive to shop unlocks (any of: wheat, carrot, tomato, strawberry, egg, milk, wool)
**Decision Logic:**
- Day 0: Start with 10 wheat + 5 carrot tiles (safe defaults). Hire 2 hands.
- Each day, check obs["town"]["unlocked_shops"]. Maintain a demand score per product: base = 1, +2 per shop that demands it, +4 if it is a 2x shop (Pet Cafe for carrot, Yarn Store for wool).
- When a new shop unlocks, immediately buy seeds for the highest-demand-score crop that is plantable within remaining game time. If score ties, choose the one with higher base market price.
- Replanting rule: when any tile becomes available after harvest, plant the currently highest-scoring crop.
- Hard constraints: only plant melon if day <= 18, only plant strawberry if day <= 18, only plant tomato if day <= 20.
- Maintain at least 3 wheat tiles at all times for feed/cash buffer.
- Check market price alongside shop demand: if a high-demand crop also has a rising market price (inventory below I0), prioritize it even more.
**Market Behaviour:** Sell all harvested crops immediately. Monitor all prices each turn. Buy seeds for highest-demand crop after each shop unlock.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest mature tiles. 3) Plant tile with current top-scored crop. 4) Water bonus windows. 5) Move.
**Special Mechanics Used:** 2 farm hands. Town shop monitoring. Dynamic replanting. No animals or fertilizer.
**Weaknesses:** Reactive strategy means some tiles are planted with suboptimal crops until new shops unlock. Demand score is a heuristic and may not reflect actual price. Complex seed inventory management.

---

### Agent 29: Fertilizer Arbitrageur
**Tier:** 3
**Core Strategy:** Buy 6 geese for fertilizer, collect 6 fertilizer/day, sell at base price $100 as primary income, supplement with egg sales and wheat.
**Crop Focus:** Goose/Egg (6 coops), Fertilizer (sell), Wheat (feed)
**Decision Logic:**
- Day 0: Buy 3 geese ($900). Build 3 coops near shed. Place geese. Buy 6 wheat seeds. Hire 1 hand.
- Days 1-2: Buy 3 more geese ($1,200). Build 3 more coops. Place. Total 6 geese.
- Daily: FEED all 6 geese, CARE all geese, COLLECT_FERTILIZER from all 6 (6/day). HARVEST eggs.
- Fertilizer revenue: 6/day at $100 = $600/day base, but selling 6/day drives inventory up 42/day (6x7). Over 25 days = 1,050 units above I0. Fertilizer uses linear both sides (target 0.40): amp = 0.40*100/200 = 0.20. Price at I0+1050: 100 - 0.20*1050 = 100-210 = floor $1. Will crash hard.
- Revised rule: sell maximum 4 fertilizer/day. Track fertilizer inventory. If market inventory > I0+300 (price ~$40): sell only 2/day. Use remaining fertilizer on crops.
- Apply fertilizer to tomato tiles (6 tiles): doubles tomato yield from 4 to 8 per plant.
- Wheat for feed: 6 tiles minimum. Remaining tiles: tomato (6 tiles).
**Market Behaviour:** Sell 2-4 fertilizer/day (price-gated). Sell eggs daily. Sell tomatoes daily. Buy wheat seeds. Buy goose animals. Hire 1-2 hands.
**Farmer Actions (priority):** 1) FEED geese. 2) CARE geese. 3) COLLECT_FERTILIZER. 4) HARVEST geese. 5) FERTILIZE tomato tiles on days 7 and 10. 6) Water tomatoes. 7) Harvest tomatoes. 8) Water/harvest wheat. 9) Plant. 10) Move.
**Special Mechanics Used:** 6 goose coops. Fertilizer as income stream. Fertilizer applied to tomatoes for 2x yield. Farm hand. No land expansion.
**Weaknesses:** $2,100 goose investment is very high. Fertilizer market sensitive to oversupply. 6 geese + 6 tomato + 6 wheat tiles = 18 tiles fully committed; movement overhead is significant.

---

### Agent 30: Opponent Crop Mirror
**Tier:** 3
**Core Strategy:** Observe what the opponent is growing on day 1-2, then plant a completely different crop set to avoid price competition.
**Crop Focus:** Dynamic — the opposite of whatever opponent is growing
**Decision Logic:**
- Day 0: Plant 5 wheat tiles (safe hold while observing). Hire 1 hand.
- Day 1: Read obs["farms"][opponent_id]["tiles"]. Count crop types: if opponent has melon tiles > 3, classify opponent as "melon farmer". If carrot > 5, "carrot farmer". If tomato > 5, "tomato farmer". If ongoing structures visible, "animal farmer".
- Based on classification, choose avoidance strategy:
  - Opponent = melon farmer → plant tomato + carrot (avoid melon market)
  - Opponent = carrot farmer → plant melon + wheat (avoid carrot market)
  - Opponent = tomato farmer → plant carrot + melon (avoid tomato market)
  - Opponent = animal farmer → plant melon + strawberry (no animal market overlap)
  - Opponent = wheat/undecided → plant melon (best ROI with no competition)
- Day 2: Buy seeds per chosen strategy. Plant immediately. Rip up day-0 wheat tiles if they conflict.
- Continuously re-check opponent farm every 3 days. If opponent pivots to your crop, switch to the next-best non-competing crop.
**Market Behaviour:** Sell all goods immediately on harvest. Buy seeds matching chosen anti-mirror strategy. Monitor opponent money to gauge if their strategy is working.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest mature crops. 3) Plant per anti-mirror allocation. 4) Water bonus windows. 5) Move. 6) Observe and re-classify opponent every 72 turns (3 days).
**Special Mechanics Used:** Opponent farm observation. Dynamic crop switching. 1-2 farm hands. No animals initially (unless opponent-reactive).
**Weaknesses:** Day-0 wheat is wasted if pivoting. Classification error (misreading opponent intent) leads to competing anyway. Opponent may deliberately confuse with early decoy plantings.

---

## Tier 4: Full Game Exploitation — Opponent-Reactive, Adaptive, Multi-System (Agents 31-40)

---

### Agent 31: Melon Price Sniper
**Tier:** 4
**Core Strategy:** Grow melons, then sell the entire batch in a single turn before the opponent has any market orders — front-running by exploiting the concurrent order processing rule.
**Crop Focus:** Melon only
**Decision Logic:**
- Day 0: Buy 10 melon seeds ($800). Hire 2 hands. Plant all 10 melons. Water immediately.
- Days 0-9: Water all melons every day. Track opponent farm: if opponent has melons, note their planted_day to predict their harvest day.
- Harvest day calculation: if opponent planted melons on day 0, they harvest day 10. If on day 1, they harvest day 11, etc.
- Sell timing rule: if agent and opponent both harvest day 10, both will sell simultaneously — this halves effective price per unit since both sell concurrently. To front-run: use fertilizer on all 10 tiles starting day 4 (covers days 4,5,6 — each watered day adds 2). Check if yield hits 6 by day 8. If yes, harvest day 8, sell day 8 — 2 days before opponent day-10 harvest.
- If fertilizer front-run not viable (no funds): sell the first 20 melons on turn 1 of day 10 in one market order burst (10 SELL MELON 2 orders = 20 units). At I0 price this yields ~$4,900 before opponent sells even 1.
- After first batch: sell remainder 3/day.
**Market Behaviour:** Issue all 10 market sell orders simultaneously on the first turn of harvest day. Then sell 3/day. Buy fertilizer if affordable (day 3). Sell all remaining melons by day 20.
**Farmer Actions (priority):** 1) FERTILIZE melon tiles days 4-9 (one per turn, 10 tiles = 10 turns). 2) Water consecutive_unwatered=1. 3) Harvest all mature melons in one sweep. 4) Replant immediately. 5) Water bonus windows. 6) Move.
**Special Mechanics Used:** Fertilizer timing for early harvest. 2 farm hands. Opponent harvest-day prediction. Melon sell burst on first turn of harvest day.
**Weaknesses:** If opponent also uses fertilizer and harvests day 8, front-running fails. Fertilizer cost ($300 for 3 units) strains budget. 10 melon tiles is large and watering all requires 2 hands.

---

### Agent 32: Adaptive Income Maximizer
**Tier:** 4
**Core Strategy:** Maintain three income streams simultaneously (wheat cycling, melon cycles, geese), dynamically re-allocating tiles and hands based on current bank balance and market conditions.
**Crop Focus:** Wheat (feed + income), Melon (primary premium), Goose/Egg (stable baseline)
**Decision Logic:**
- Day 0: Buy 4 geese ($1,200), build 4 coops. Buy 6 melon seeds ($480). Buy 5 wheat seeds. Hire 2 hands. Plant all. ($680 left).
- Income phases: Phase 1 (days 0-9) = wheat cash flow + goose eggs. Phase 2 (days 10-20) = melon harvests + eggs. Phase 3 (days 21-29) = wheat cycling + eggs + second melon batch.
- Dynamic reallocation: every 5 days, compute income/day from each active stream. If wheat income/day > egg income/day: plant more wheat on free tiles. If melon income is above $2,000 in next 3 days: hold all sell orders for melons until harvest.
- Threshold rules: if bank balance < $500: hire 0 hands, sell everything immediately, buy only wheat seeds. If bank balance > $2,000: hire 3 hands, expand to melon + goose simultaneously.
- Shed capacity management: if shed > 80 items, stop harvesting non-critical crops until sold down.
- On day 25: liquidate everything. Sell all goods. Stop planting melon.
**Market Behaviour:** Sell wheat and eggs daily. Sell melons at 4/day. Sell fertilizer at $85+. Dynamically adjust sell amounts based on bank balance thresholds.
**Farmer Actions (priority, always re-evaluated):** 1) FEED geese (never miss). 2) CARE geese. 3) HARVEST geese. 4) COLLECT_FERTILIZER. 5) Water melon at consecutive_unwatered=1. 6) Harvest mature melon. 7) Water all melons. 8) Harvest/plant/water wheat. 9) Move.
**Special Mechanics Used:** 4 goose coops. 2-3 farm hands. Fertilizer collection. Dynamic tile reallocation. Phase-based strategy switching. No land expansion.
**Weaknesses:** Complexity creates more failure points. Three simultaneous systems require near-perfect turn allocation. Day-0 cost ($1,680+) leaves almost no buffer.

---

### Agent 33: Town Demand Predictor
**Tier:** 4
**Core Strategy:** Before each game, compute the expected shop unlock sequence and pre-plant crops in the order that will have maximum supply ready when demand peaks.
**Crop Focus:** Dynamic based on predicted shop unlocks — typically strawberry + milk/egg
**Decision Logic:**
- All 8 shops unlock by day 24 (every 3 days). Compute expected demand score per crop across the season assuming random but sequential unlocks.
- Strawberry appears in: Brunch Spot, Ice Cream Shop, Smoothie Shop, Farmers Market = 4 shops (6/day each = 24/day at peak, plus town center 8/day = 32/day drain by day 20). Strawberry also has the highest base price with scarcity premium ($204 at I0-T).
- Milk appears in: Pizza Shop, Ice Cream Shop, Smoothie Shop = 3 shops (18/day + 8/day town = 26/day drain).
- Strategy: plant strawberries at game start (first yield day 10, aligns with day-10 town demand doubling). Plant strawberries again on day 18 for late yields.
- Build 2 cow pastures on day 0 for milk (first yield day 8). Sell milk starting day 8 as town demand ramps.
- Grow wheat for feed. Hire 3 hands.
- Check which shops have unlocked by day 9. If 2+ milk-demanding shops are active by day 12: increase cows to 3. If 3+ strawberry-demanding shops by day 15: plant more strawberry tiles.
**Market Behaviour:** Sell strawberries at rate = 1 + active_strawberry_shops per day (max 4). Sell milk at rate = 1 + active_milk_shops per day (max 3). Sell wheat daily. Buy seeds and animals to match demand scale.
**Farmer Actions (priority):** 1) FEED cows. 2) CARE cows. 3) HARVEST milk. 4) Water strawberries at consecutive_unwatered=1. 5) Harvest strawberry yields. 6) Water all strawberries. 7) Water/harvest wheat. 8) Plant. 9) Move.
**Special Mechanics Used:** Town demand prediction. 2-3 cow pastures. 3 farm hands. No fertilizer. Dynamic scaling based on shop unlock observation.
**Weaknesses:** Shop unlocks are random — may not get the predicted shops until late. High investment in cows + strawberry seeds day 0. Milk market crashes extremely fast if both players are supplying it.

---

### Agent 34: Price Momentum Seller
**Tier:** 4
**Core Strategy:** Track a rolling 6-turn price history for melon. Sell aggressively into rising momentum, hold during falling prices, and switch to wheat when melon price is chronically depressed.
**Crop Focus:** Melon (primary), Wheat (fallback)
**Decision Logic:**
- Day 0: Buy 8 melon seeds ($640), hire 1 hand, plant all 8 melons. Plant 3 wheat tiles for early income.
- Each turn, record current melon price in a circular buffer of length 6. Compute momentum = (price[-1] - price[-4]) / 3 (average change over last 3 observations).
- Momentum sell rules: if momentum >= +5/turn ("rising"): sell all melons in shed immediately (price is peaking, extract now). If momentum <= -5/turn ("falling"): hold all melons in shed (price recovering, do not sell into trough). If -5 < momentum < +5 ("stable"): sell at most 4 melons/day.
- Hard floor rule: if melon price < $80 for 3+ consecutive checks, declare a crash and pivot — DIG melon tiles progressively and replant with wheat. Do not replant melons.
- Season-end rule: day 27+, sell everything regardless of momentum.
- Harvest decision is decoupled from sell decision: always harvest at max yield or when decay is imminent, regardless of price. Accumulate in shed; only shed-to-market orders are momentum-gated.
**Market Behaviour:** Issue SELL orders based on momentum state. Rising: sell all. Stable: sell 4/day. Falling: hold. Crash: pivot to wheat, sell any remaining melons at floor price. Buy melon seeds for initial 8 tiles only.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest melons at max yield or age 11+. 3) Plant empty tiles (melon if day <= 18, wheat otherwise). 4) Water bonus-window tiles. 5) Move.
**Special Mechanics Used:** Price history buffer (6 turns). Momentum threshold logic. Wheat fallback on crash. 1 farm hand.
**Weaknesses:** 6-turn buffer is short — momentum signal can lag actual price turns. Rising momentum sell-all can self-crash the market if shed is full. Wheat fallback on crash concedes late-game melon upside.

---

### Agent 35: Compound Goose Empire
**Tier:** 4
**Core Strategy:** Buy geese as fast as cash allows, reinvesting all egg and fertilizer revenue into more geese and coops, until hitting the 25-tile limit for a full 25-goose empire.
**Crop Focus:** Goose/Egg (all available tiles), Wheat only for feed (bought from market)
**Decision Logic:**
- Day 0: Buy 4 geese ($1,200). Build 4 coops on nearest tiles. Place all 4. Use remaining $1,800: buy 50 wheat product ($1,250 at $25 each) for feed buffer. Put in shed.
- Each day: FEED all geese (consumes wheat from shed). CARE all geese (daily care = 2 eggs/goose/day). HARVEST all geese with yield > 0. COLLECT_FERTILIZER from all.
- Sell all eggs each day. Sell all fertilizer each day. Reinvest 80% of daily revenue: buy new geese and build coops as tiles free up.
- Goose purchase target: +2 geese every 3 days until 20 geese total.
- At 20 geese: 40 eggs/day * $50 = $2,000/day + 20 fertilizer/day * $80 = $1,600/day = $3,600/day.
- Reserve 5 tiles for wheat to supplement feed (reduce market wheat purchases). 20 geese = 20 wheat/day; wheat tiles produce 4/5 days per tile = need 25 wheat tiles. Not possible alone — must buy wheat.
- From day 15 onward: buy 20 wheat product/day from market to feed 20 geese.
**Market Behaviour:** Sell all eggs and fertilizer daily. Buy wheat product daily (20 units) as primary expense. Reinvest in geese up to 20. No crop seeds needed (wheat is bought).
**Farmer Actions (priority):** 1) FEED all geese (any with consecutive_unfed approaching 2 first). 2) CARE all geese. 3) HARVEST geese with yield > 0. 4) COLLECT_FERTILIZER. 5) BUILD_COOP on empty tiles. 6) PICKUP goose from shed, PLACE on coop. 7) DROP inventory. 8) Move.
**Special Mechanics Used:** Up to 20 goose coops. 2-3 farm hands for coop building and harvesting. Wheat bought from market for feed. No crops except structural wheat. No land expansion (25 tiles sufficient).
**Weaknesses:** Reinvesting in geese while also buying wheat requires careful cash flow. Egg market is stable but 40 eggs/day from 20 geese may drift prices slightly. Setup cost is enormous — break-even is slow.

---

### Agent 36: Nearest-Task Greedy
**Tier:** 4
**Core Strategy:** Every turn, build a list of all pending tasks across the entire farm, sort by (task_priority_class, manhattan_distance), and execute the nearest highest-priority task. No lookahead — pure proximity-greedy routing.
**Crop Focus:** Melon (primary) + Wheat (gap fill)
**Decision Logic:**
- Day 0: Buy 10 melon seeds ($800), hire 2 hands. Plant all 10 on tiles nearest spawn. Plant wheat on remaining empty tiles.
- Task classes (priority descending): 0 = WATER consecutive_unwatered=1 (urgent — dies tomorrow), 1 = HARVEST at max yield or decay, 2 = WATER in bonus window (days 6-10 for melon), 3 = PLANT empty tile with seed in hand, 4 = HARVEST yield >= 2, 5 = WATER all other planted tiles, 6 = DIG weed tiles.
- Each turn: scan all 25 tiles. For every tile, compute all applicable tasks and their class. Sort candidates by (class, |dx| + |dy| from farmer). Execute the lowest-class (highest-priority) candidate. If tied class: take the nearest tile.
- If already standing on the target tile: execute the action. Else: step one tile toward it via NORTH/SOUTH/EAST/WEST (Manhattan greedy).
- Hands: each hired hand runs the same nearest-task algorithm independently. No explicit zone assignment. Hand 1 picks the task nearest its spawn tile; Hand 2 picks the next nearest remaining task.
- Market: sell melons at 4/day if price >= $120. Sell all wheat immediately. Buy seeds to maintain 10 melon + 5 wheat tiles.
**Market Behaviour:** Sell melon at 4/day when price >= $120. Sell wheat all. Buy melon and wheat seeds. Hire 2 hands daily.
**Farmer Actions:** Nearest-task greedy from priority class list above, Manhattan distance tiebreak.
**Special Mechanics Used:** Per-turn tile scan and sort. 2 farm hands (also greedy). No fertilizer, no animals.
**Weaknesses:** Greedy routing can oscillate between two equidistant tasks on opposite sides of the farm. No planning across multiple turns means farmer may re-water a tile it just left. Low throughput compared to zone-assigned hands.

---

### Agent 37: Dual-Quadrant Melon Specialist
**Tier:** 4
**Core Strategy:** Buy NE quadrant on day 4, run melon on all 50 tiles with 4 farm hands, sell two staggered melon batches to avoid self-crashing the market.
**Crop Focus:** Melon on 50 tiles (NW + NE quadrants)
**Decision Logic:**
- Day 0: Buy 15 melon seeds ($1,200). Hire 3 hands. Plant 15 tiles in NW. Water all immediately.
- Day 4: Buy NE quadrant ($1,000) using early revenue from wheat cycle. Buy 12 more melon seeds ($960). Plant NW remaining tiles + NE tiles. Total ~25 melon tiles active.
- Stagger planting: NW melons planted day 0 → harvest day 10. NE melons planted day 4 → harvest day 14. This staggers sell waves.
- Day 10: Harvest NW batch (25 tiles x 6 = 150 melons). Sell 6/day for 25 days → 25*6 = 150 units total. Start immediately. 150 melons starting at I0 = revenue ~$25,000 total but price crashes to $1 at unit 158. Sell 6/day = price when 6*t units sold at day t. Price floor at day 26 (after 156 units). Acceptable.
- Day 14: Harvest NE batch. But melon price already crashed from NW batch. NE batch must be sold after price recovers from town demand.
- Recovery rule: after melon price drops below $50, stop selling. Wait for price recovery (town center drains ~2 melon/day, slowly recovering price). Resume when price > $150.
- Replant NW tiles (harvest day 10) with wheat for end-game.
**Market Behaviour:** Sell 6 melons/day from NW batch days 10-35. Monitor melon price. Pause if price < $50. Resume when > $150. Sell NE batch into any recovered price window.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest mature melons (age 10+). 3) Plant empty tiles. 4) Water bonus-window tiles. 5) Move (prioritize tiles nearest shed).
**Special Mechanics Used:** BUY_LAND (NE quadrant). 3-4 farm hands. No animals. No fertilizer. Market price monitoring with hold/resume logic.
**Weaknesses:** $2,200 day-4 investment requires early revenue. 50 melon tiles requires 4 hands — very expensive ($7/day). Self-crashing risk remains even with 6/day drip sell. NE quadrant hand spawn on locked tile wastes 1 movement turn.

---

### Agent 38: Wheat-Egg Steady State
**Tier:** 4
**Core Strategy:** Establish a minimal, stable production loop: 15 wheat tiles + 4 geese. Wheat feeds geese; goose fertilizer goes onto wheat to increase yield; eggs and surplus wheat are sold daily. No complexity, no pivots — just the optimal steady-state parameters for this two-system combination.
**Crop Focus:** Wheat (15 tiles), Goose/Egg (4 coops)
**Decision Logic:**
- Day 0: Buy 2 geese ($600). Build 2 coops on tiles (0,0) and (1,0) (corner, away from wheat zone). Place geese. Buy 15 wheat seeds ($150). Plant all 15 on the remaining NW tiles. Hire 1 hand. Total spend: $750.
- Daily goose loop: FEED all 4 geese first (priority — 4 wheat/day consumed from shed). CARE all geese. HARVEST geese with yield > 0. COLLECT_FERTILIZER.
- Day 2: Buy 2 more geese ($800). Build 2 more coops. Place. 4 geese total = 4 eggs/2 days (with daily care = 2 eggs/goose/day after day 4) + 4 fertilizer/day.
- Wheat feed requirement: 4 geese x 1 wheat/day = 4 wheat/day. 15 wheat tiles produce ~12 wheat/day (4 yield x 15 tiles / 5 days). Surplus ~8 wheat/day sold.
- Fertilizer application: each day apply 2 fertilizer to the 2 wheat tiles in their bonus window (days 2-4 of their growth cycle). This adds 2 extra yield to those tiles (+$50 value). Store remaining fertilizer in shed.
- Sell surplus fertilizer: if shed fertilizer > 10, sell 3/day. Sell all eggs daily. Sell all surplus wheat daily.
- Do not plant anything other than wheat. Do not hire additional hands after day 2.
**Market Behaviour:** Sell all eggs daily. Sell 3 fertilizer/day when shed > 10. Sell surplus wheat daily. Buy wheat seeds to keep all 15 tiles planted. Buy 2 more geese on day 2.
**Farmer Actions (priority):** 1) FEED geese (consecutive_unfed first). 2) FEED all geese. 3) CARE all geese. 4) HARVEST geese. 5) COLLECT_FERTILIZER. 6) FERTILIZE 2 wheat tiles in bonus window. 7) Water wheat at consecutive_unwatered=1. 8) Harvest mature wheat. 9) Plant empty wheat tiles. 10) Move.
**Special Mechanics Used:** 4 goose coops. Fertilizer on wheat. 1 farm hand. No land expansion, no animals beyond 4 geese.
**Weaknesses:** Low peak revenue — 15 wheat tiles at $25 average + eggs cap income around $600-800/day. No premium crop upside. 4 geese consume 4 wheat/day, so wheat surplus is smaller than it appears. Agent is intentionally simple — acts as a reliable baseline, not a high-scorer.

---

### Agent 39: Late-Game Cash Surge
**Tier:** 4
**Core Strategy:** Deliberately sacrifice early income to maximize day-20-to-29 revenues by stockpiling premium goods, using post-day-20 demand surge and price recovery.
**Crop Focus:** Melon (cycle 1 sell late, cycle 2), Strawberry (stored), Egg (ongoing)
**Decision Logic:**
- Day 0: Buy 6 melon seeds, 4 strawberry seeds, 2 geese. Plant all. Build 2 coops. Place geese. Hire 1 hand.
- Days 0-19: Run on minimum sells. Sell only eggs (small daily drip) for operating cash. Store all melons and strawberries in shed.
- Day 10: Harvest 6 melons (36 units) + strawberry yields. Store all in shed.
- Day 16: All 4 strawberry yields complete. Shed now has up to 36 melon + 16 strawberry = 52 items. Second melon cycle: plant 6 new melons.
- Day 20: Town demand quadruples (8 units/day of each product from town center). Prices rise as market inventory drains. Begin selling: 4 melons/day + 2 strawberries/day. Egg revenue ongoing.
- Calculate price at day 20: town has been draining melon market for 20 days at 2/day (days 0-9) + 4/day (days 10-19) = 60 units below I0. Melon price at I0-60: 250 + amp*sqrt(60)... check formula (below I0, log function for melon). Amp = 0.20*250/log(1+300) = 50/5.71 = 8.76. Price = 250 + 8.76*log(61) = 250 + 8.76*4.11 = $286.
- Day 22-25: Second melon batch harvests. Sell into high price.
- Day 25-29: Sell everything. Full liquidation.
**Market Behaviour:** Minimal selling days 0-19 (eggs only). Aggressive selling days 20-29 (melon 4/day, strawberry 2/day, eggs all). Monitor prices — increase rate if price unexpectedly drops.
**Farmer Actions (priority):** 1) FEED geese. 2) CARE geese. 3) HARVEST geese. 4) COLLECT_FERTILIZER. 5) Water melons at consecutive_unwatered=1. 6) Water strawberries. 7) Harvest ripe crops (store, don't sell). 8) Plant. 9) Move.
**Special Mechanics Used:** 2 goose coops. Farm hand. Shed as storage buffer (manage capacity carefully). Day-20 demand surge exploitation. No fertilizer, no land expansion.
**Weaknesses:** Near-zero income for days 0-19 — must survive on starting money. Shed capacity (100 items) is tight: 36 melon + 16 strawberry + eggs fills it fast. Opponent may out-earn early and win even if late-game surge works.

---

### Agent 40: Opponent Money Watcher
**Tier:** 4
**Core Strategy:** Track opponent's money delta each day. If opponent earns faster than you over the last 3 days, reduce your own sell rate (assume shared markets are being crashed by their volume). If opponent loses money or stalls, increase your sell rate to capture the gap.
**Crop Focus:** Melon (primary), Wheat (steady baseline)
**Decision Logic:**
- Day 0: Buy 8 melon seeds ($640), hire 1 hand. Plant all 8. Plant 5 wheat tiles.
- Each day, record opponent_money (visible in obs["farms"][opp]["money"]). Compute opponent_3day_gain = opponent_money_today - opponent_money_3_days_ago. Similarly compute own_3day_gain.
- Rate adjustment rules:
  - If opponent_3day_gain > own_3day_gain + $500: opponent is beating you — they are selling into the same market or an uncrowded one. Cut own melon sell rate to 2/day (avoid crashing further), increase wheat sells to 20/day.
  - If opponent_3day_gain < own_3day_gain - $500: you are outperforming — stay aggressive. Sell 6 melons/day.
  - If rates within $500 of each other: sell 4 melons/day.
- Pivot rule: if opponent money never increases for 5+ consecutive days (they are stuck or crashing), interpret this as their market being saturated. Sell your melons aggressively now — the market is not crowded by them.
- Season-end (day 27+): ignore opponent signal, sell all.
- Wheat is sold daily regardless of rate — it is the stable fallback revenue.
**Market Behaviour:** Sell melons at rate determined by opponent gain comparison (2/4/6 per day). Sell all wheat daily. Buy melon seeds for 8 tiles only. Monitor opponent money field each turn.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest melons at max yield or age 11+. 3) Plant empty tiles (melon if day <= 18, wheat else). 4) Water bonus windows. 5) Move.
**Special Mechanics Used:** Opponent money field reading. 3-day gain comparison. Dynamic sell rate. 1 farm hand.
**Weaknesses:** Opponent money delta conflates multiple signals (they may earn from a completely different crop, so reducing your own rate is wrong). 3-day lag means the signal is always slightly stale. Opponent money is only updated once per day, limiting granularity.

---

## Tier 5: Focused Variants and Edge-Case Specialists (Agents 41-50)

---

### Agent 41: Staggered Melon Pipeline
**Tier:** 5
**Core Strategy:** Plant 3 melons every 3 days starting day 0, creating a continuous harvest conveyor that yields 3 melons every 3 days from day 10 onward, avoiding large single-day market dumps.
**Crop Focus:** Melon only
**Decision Logic:**
- Day 0: Buy 3 melon seeds ($240), plant on tiles (4,0), (3,0), (2,0). Hire 1 hand. Remaining money buys 5 wheat seeds for cash flow.
- Day 3: Buy 3 more melon seeds, plant on next 3 tiles. Day 6: Buy 3 more, plant. Day 9: Buy 3 more, plant. Total 12 melon tiles, planted in 4 waves of 3.
- Wave harvest schedule: Wave 1 (planted day 0) → harvest day 10. Wave 2 (planted day 3) → harvest day 13. Wave 3 (planted day 6) → harvest day 16. Wave 4 (planted day 9) → harvest day 19.
- Each wave yields 3 tiles x 6 units = 18 melons. Sell 6/day over 3 days. Then next wave arrives.
- Market effect: never sell more than 6 melons/day, pipeline keeps price from recovering-then-crashing pattern.
- After all waves harvested (by day 21): switch all tiles to wheat for remaining days.
- Replant rule: only replant wave 1 tiles if day <= 17 (need 10 days). Wave 2-4 tiles: no replant (not enough time).
**Market Behaviour:** Sell 6 melons/day continuously days 10-21. Sell all wheat daily. Buy 3 melon seeds every 3 days. Buy wheat seeds to fill non-melon tiles.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest mature melons. 3) Plant per wave schedule. 4) Water bonus windows. 5) Harvest/plant wheat. 6) Move.
**Special Mechanics Used:** 1 farm hand. Wave-planting schedule. No animals, no fertilizer, no land expansion.
**Weaknesses:** Requires careful per-wave seed budget planning — may run low on cash between day-0 and day-3 melon purchase if wheat tiles aren't producing yet. Waves 3-4 yield during late game when melon may already be depressed.

---

### Agent 42: Carrot-Rush-to-Melon
**Tier:** 5
**Core Strategy:** Exploit carrot's 3-day cycle for 9 days to build cash, then pivot to melon on day 9. Carrot funds the melon seeds; melon provides the late-game payout.
**Crop Focus:** Carrot (days 0-9), Melon (days 9-29)
**Decision Logic:**
- Day 0: Buy 20 carrot seeds ($400), hire 2 hands. Plant all 20 tiles. Water.
- Days 3, 6, 9: Harvest carrot wave, immediately replant. Sell all harvested carrots.
- Day 9: Stop buying carrot seeds. Use accumulated cash to buy 15 melon seeds ($1,200). On each tile where carrot is harvested (day 9), DIG (carrots are non-ongoing so they just expire/get harvested), replant with melon.
- Days 9-18: Water all 15 melon tiles. Hire 2 hands throughout.
- Day 19: Harvest first melon wave (15 tiles x 6 = 90 melons). Sell 6/day for 15 days.
- After day 19 harvest: switch all tiles to wheat (no time for another melon cycle).
**Market Behaviour:** Sell all carrots daily (days 0-9). Buy 15 melon seeds on day 9. Sell 6 melons/day from day 19. Sell all wheat from day 21 onward.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest mature crops (carrot age 3+, melon age 10+). 3) Plant per current phase. 4) Water bonus windows. 5) Move.
**Special Mechanics Used:** 2 farm hands. Phase pivot on day 9. No animals, no fertilizer.
**Weaknesses:** Carrot income stops abruptly on day 9. If carrot price crashed during days 0-9, cash for melon seeds may be short. One melon wave at day 19 leaves only 10 days to sell 90 melons.

---

### Agent 43: Four-Hand Wheat Blitz
**Tier:** 5
**Core Strategy:** Hire 4 farm hands every day and use all 5 units (farmer + 4 hands) solely on wheat. Maximum turn density on a single crop — no animals, no premium crops, no market timing.
**Crop Focus:** Wheat (all 25 tiles)
**Decision Logic:**
- Day 0: Buy 20 wheat seeds ($200), hire 2 hands ($2). Plant all 20. Water immediately.
- Day 1 onward: hire 4 hands every day ($7 Fibonacci: 1+1+2+3 = $7). 5 units x 24 turns = 120 turns/day.
- Action budget: 25 tiles, each needing water (1 turn) + harvest (1 turn) + plant (1 turn) = 3 turns/tile/cycle. 25 tiles x 3 = 75 turns every 5 days = 15 turns/day. With 120 turns/day available, easily covers all tiles with significant idle time.
- Use idle turns for: watering bonus-window tiles twice (extra yield doesn't happen with wheat but routine minimizes risk), moving to keep coverage tight, dropping harvested wheat at shed.
- Sell all wheat every day. Never hold. Wheat's low price sensitivity means maximum volume = maximum revenue.
- Do not buy anything except wheat seeds and 4 hands. No animals, no fertilizer, no land purchase.
- Hand zone assignment: Hand 1-2 cover rows 0-2 (top zone), Hand 3-4 cover rows 3-4 (bottom zone), Farmer floats to wherever consecutive_unwatered=1 is detected.
**Market Behaviour:** Sell all wheat daily. Buy 25 wheat seeds/day to replace harvested. Hire 4 hands daily.
**Farmer Actions:** Float to any tile with consecutive_unwatered=1 first. Then harvest mature tiles. Then plant empties. Then water bonus tiles.
**Special Mechanics Used:** 4 farm hands daily. Zone-based assignment. No other systems.
**Weaknesses:** Hand hire cost ($7/day) is $210 over the season. At wheat base $25 x 4 units x 25 tiles / 5 days = $500/day gross, $7/day hand cost is 1.4% overhead — very efficient. However, wheat price may drift down if market inventory builds. Revenue ceiling is ~$500/day, well below premium crop peaks.

---

### Agent 44: Melon Micro-Seller
**Tier:** 5
**Core Strategy:** Grow 10 melon tiles, then sell exactly 1 melon per turn (24 per day) over the entire harvest window. Never crash the price. Accept lower total revenue in exchange for a guaranteed high-per-unit price.
**Crop Focus:** Melon only (sell rate minimised)
**Decision Logic:**
- Day 0: Buy 10 melon seeds ($800). Hire 1 hand. Plant all 10. Water.
- Days 0-10: Water all melons daily. Plant 5 wheat tiles on remaining space for cash flow.
- Day 10: First harvest (10 tiles x 6 = 60 melons). Begin selling: 1 SELL MELON 1 order per turn, every turn that farmer is adjacent to shed (market orders are turn-free, so issue 1 per turn throughout).
- Since 24 turns/day x 1 unit = 24 melons/day is actually fast for melon — revise: issue 1 sell order every 3 turns = 8 melons/day. This is significantly slower than standard drip.
- Monitor melon market inventory each turn. If inventory > I0 + 30: pause selling for the turn (price has dropped). Resume when inventory <= I0 + 10.
- After first batch (60 units) is sold (~7.5 days at 8/day): harvest cycle 2. Plant 10 melons on day 10, harvest day 20. Sell same micro-rate.
- Day 27: increase rate to all-in — sell remaining melons regardless.
**Market Behaviour:** Sell 1 melon per 3 turns (8/day target), pausing when market inventory rises above I0+30. Monitor market inventory each turn to gate sells. Buy 10 melon seeds twice (day 0 and day 10). Sell wheat daily.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest melons at max yield or age 11+. 3) Replant. 4) Water bonus windows. 5) Harvest wheat. 6) Move.
**Special Mechanics Used:** Per-turn market inventory monitoring. 1 farm hand. Self-imposed rate limit. No fertilizer, no animals.
**Weaknesses:** 8/day sell rate means 60 melons takes 7.5 days to sell — dangerously close to season end. Very low early income (wheat only for first 10 days). Micro-selling advantage depends on opponent NOT also being a micro-seller (combined volume still crashes price).

---

### Agent 45: Fertilized Wheat via Geese
**Tier:** 5
**Core Strategy:** Keep exactly 2 geese for free fertilizer, apply all fertilizer to wheat tiles in their bonus window (days 2-4 after planting), doubling those tiles' yield. No eggs, no milk — geese are purely a fertilizer engine.
**Crop Focus:** Wheat (20 tiles, fertilized), Goose (2 coops, fertilizer only)
**Decision Logic:**
- Day 0: Buy 2 geese ($600). Build 2 coops at corners (0,0) and (1,0). Place geese. Buy 20 wheat seeds ($200). Plant all 20 on remaining tiles. Hire 1 hand. Total: $800.
- Daily goose loop: FEED both geese (2 wheat/day). CARE both geese (bank egg bonus — eggs are bonus, not goal). HARVEST geese (collect eggs, sell daily). COLLECT_FERTILIZER (2/day).
- Fertilizer application: every turn, check if any wheat tile is at planted_day + 2 or +3 or +4 (bonus window). If yes, PICKUP fertilizer from shed, move to that tile, FERTILIZE. Fertilizing in window adds +1 yield/day during window. Two fertilizer per tile over 3 days = +3 yield (normally 4, now 7 — but capped at max_yield = 4 for wheat). Actually at max_yield = 4, fertilizing may not help beyond cap. Recalculate: wheat max_yield = 4. Fertilizing doubles watered-day yield: +1 per watered-fertilized day, capped at max_yield. So the net gain is +1 or +2 units at most.
- If fertilizer is not useful on wheat (cap prevents gain), sell all fertilizer at $95+ instead. Pivot strategy: 2 geese purely for egg + fertilizer income, 20 wheat tiles for feed + sale.
- Sell eggs daily. Sell fertilizer at $95+. Sell all wheat daily. Never buy additional geese.
**Market Behaviour:** Sell all eggs daily. Sell fertilizer at $95+ (else store). Sell all wheat daily. Buy wheat seeds. Hire 1 hand.
**Farmer Actions (priority):** 1) FEED geese. 2) CARE geese. 3) COLLECT_FERTILIZER. 4) FERTILIZE wheat tiles in bonus window. 5) HARVEST geese. 6) Water wheat consecutive_unwatered=1. 7) Harvest wheat. 8) Plant wheat. 9) Move.
**Special Mechanics Used:** 2 goose coops. Fertilizer on wheat. 1 farm hand. No land expansion.
**Weaknesses:** Wheat yield cap may neutralize fertilizer gain. 2 geese consume 2 wheat/day = $50/day in feed cost for marginal fertilizer value. If fertilizer can't be applied efficiently (agent too far from bonus-window tiles), turns are wasted. Agent is honest about the potentially low ROI.

---

### Agent 46: Day-6 Melon Planter
**Tier:** 5
**Core Strategy:** Intentionally wait until day 6 to plant melons, aligning the day-16 harvest with the town demand doubling window (day 10 onward at 2x, day 20 at 4x). Use days 0-5 to build cash via wheat.
**Crop Focus:** Wheat (days 0-5), Melon (planted day 6, harvested day 16)
**Decision Logic:**
- Days 0-5: Plant all 20 available tiles with wheat. Hire 2 hands. Harvest and sell wheat cycles (2 cycles: day 4 and day 8 partial). Accumulate cash toward melon seed budget.
- Day 6: Sell all wheat immediately. DIG any wheat at age < 4 (pre-harvest). Buy 12 melon seeds ($960). Plant 12 tiles. Let remaining 8 tiles continue wheat (never DIG mature or near-mature wheat — harvest it).
- Days 6-15: Water all 12 melons daily. Harvest and sell remaining wheat cycles.
- Day 16: Harvest first melon batch (12 x 6 = 72 melons). Town demand at 2x since day 10 means melon market inventory is lower than day 0 baseline — price should be higher. Sell 5/day.
- Day 20: Town demand hits 4x. Continue selling melon at 5/day into higher-drain market.
- Replant only if day <= 18 and cash allows. Otherwise plant wheat on freed tiles.
**Market Behaviour:** Sell wheat daily (days 0-8). Sell 5 melons/day from day 16. Buy 12 melon seeds on day 6. Hire 2 hands throughout.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest mature tiles. 3) Plant per current phase (wheat or melon). 4) Water bonus windows. 5) Move.
**Special Mechanics Used:** 2 farm hands. Phase delay (intentional 6-day wheat buffer). No animals, no fertilizer.
**Weaknesses:** DIG cost on wheat tiles on day 6 wastes turns and loses wheat yield. Harvest window is days 16-29 = 13 days to sell 72 units at 5/day = possible if no competitor crashes the market. Market may already be depressed if opponent sold into it earlier.

---

### Agent 47: Tomato Two-Wave
**Tier:** 5
**Core Strategy:** Plant 10 tomatoes on day 0 (harvest days 8-11) and another 10 on day 13 (harvest days 21-24), creating two back-to-back tomato waves. Between waves, grow wheat on freed tiles.
**Crop Focus:** Tomato (two waves), Wheat (between waves)
**Decision Logic:**
- Day 0: Buy 10 tomato seeds ($500), hire 1 hand. Plant all 10. Water. Buy 5 wheat seeds for remaining tiles.
- Days 8-11: Harvest tomatoes daily (yield_units > 0). Sell immediately. Tomato plants are ongoing — DO NOT DIG. They continue producing.
- But tomato only produces 4 times (days 8, 9, 10, 11) then decays on day 12. DIG all on day 12. Plant 10 wheat seeds immediately.
- Days 12-12: 10 tiles become wheat. Harvest wheat on day 16 (4-day cycle). Sell.
- Day 13: Replant 10 tomatoes on the now-dug tiles (buy new tomato seeds $500). Plant immediately. Water.
- Days 21-24: Second tomato wave harvests. Sell daily.
- After day 24: DIG or wait for decay. Plant wheat. Sell remaining tomatoes aggressively by day 29.
**Market Behaviour:** Sell tomatoes as harvested (days 8-11 and 21-24). Sell wheat between waves. Buy tomato seeds twice (day 0 and day 13). Hire 1 hand throughout.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1. 2) Harvest tomato yield_units > 0. 3) DIG decayed tiles (day 12). 4) Plant empty tiles per phase. 5) Water bonus windows. 6) Move.
**Special Mechanics Used:** 1 farm hand. Two-wave tomato planting. Wheat gap fill. No animals, no fertilizer.
**Weaknesses:** Second wave harvest on days 21-24 is very late — only 5 days to sell those tomatoes. Tomato price may crash if both waves sell into the same market window. DIG cost on day 12 wastes several turns for farmer and hand.

---

### Agent 48: Goose Snowball
**Tier:** 5
**Core Strategy:** Start with 1 goose. Reinvest every dollar of egg and fertilizer revenue into new geese and coops, snowballing to 12 geese by day 15. Grow wheat purely to cover feed.
**Crop Focus:** Goose/Egg (scaling from 1 to 12), Wheat (feed only)
**Decision Logic:**
- Day 0: Buy 1 goose ($300). Build 1 coop at (0,0). Place goose. Buy 6 wheat seeds. Plant. Hire 0 hands. ($2,394 remaining).
- Each day: FEED goose (1 wheat). CARE goose. HARVEST goose. COLLECT_FERTILIZER. Sell eggs ($50 base) + fertilizer ($100 base) = ~$150/day.
- Reinvest rule: every time cash crosses a goose purchase threshold, buy the next goose immediately. Goose prices: $300, $400, $500, $600, $700, $800, $900, $1000, $1100, $1200, $1300, $1400 (Fibonacci: 300 + 100*n roughly). By day 10 with reinvestment, should have 5-6 geese.
- Wheat tiles: always keep enough wheat tiles to cover current goose count. Add 1 wheat tile per new goose (buy 1 wheat seed per goose added). Wheat cycles fund the gaps between goose revenue.
- By day 15: 10-12 geese, ~20 eggs/day at $50 = $1,000/day + 10 fertilizer/day at $80 = $800/day = $1,800/day.
- Hire 1 hand on day 5 ($1). Hire 2nd hand on day 10 ($2) to manage expanded goose operations.
- Sell all eggs and fertilizer daily throughout.
**Market Behaviour:** Sell all eggs daily. Sell all fertilizer daily. Reinvest cash immediately into next goose whenever threshold crossed. Buy wheat seeds incrementally. Hire 1-2 hands.
**Farmer Actions (priority):** 1) FEED all geese (priority by consecutive_unfed). 2) CARE all geese. 3) HARVEST all geese. 4) COLLECT_FERTILIZER. 5) BUILD_COOP on empty tile (when new goose purchased). 6) PICKUP/PLACE goose. 7) Water wheat. 8) Harvest wheat. 9) Plant wheat. 10) Move.
**Special Mechanics Used:** Incremental goose building. Reinvestment trigger logic. 1-2 farm hands. Wheat scaling with goose count. No crops, no fertilizer on crops.
**Weaknesses:** Early game (days 0-4) is very low income — 1 goose produces only $150/day. Snowball is slow — 12 geese by day 15 = only 14 days of peak income. Each new goose requires a new coop built (BUILD_COOP takes 1 turn + movement). Egg market stable but 12 geese x 2 eggs/day = 24 eggs/day may drift prices slightly.

---

### Agent 49: Wheat-Tomato Split
**Tier:** 5
**Core Strategy:** Dedicate exactly 12 tiles to wheat (continuous cycling) and 10 tiles to tomato (ongoing), running both crops independently with no pivots. Simple, dual-crop steady state.
**Crop Focus:** Wheat (12 tiles), Tomato (10 tiles, ongoing)
**Decision Logic:**
- Day 0: Buy 10 tomato seeds ($500) and 12 wheat seeds ($120). Hire 2 hands. Plant tomatoes on the 10 tiles closest to spawn, wheat on the 12 remaining tiles. ($2,380 left).
- Tomato zone (10 tiles): water daily. Harvest yield_units >= 2 from day 8 onward. Tomato ongoing — do not DIG after harvest. Never replant (ongoing crop keeps producing).
- Wheat zone (12 tiles): water daily. Harvest age >= 4. Replant immediately. Sell all wheat daily.
- Hand 1 assigned to tomato zone. Hand 2 assigned to wheat zone. Farmer floats to wherever consecutive_unwatered=1 is detected.
- Sell tomatoes at 8/day (stable enough given 10 plants x 1 unit/day ongoing after day 8 = 10/day max throughput). Sell wheat all daily.
- Seeds: buy 12 wheat seeds/day to keep wheat cycling. No tomato seeds needed after day 0 (ongoing).
- Hiring: 2 hands from day 0. Do not hire more.
**Market Behaviour:** Sell tomatoes at 8/day. Sell all wheat daily. Buy 12 wheat seeds/day. No other purchases.
**Farmer Actions (priority):** 1) Water consecutive_unwatered=1 (any zone). 2) Harvest tomato yield_units >= 2. 3) Harvest mature wheat. 4) Plant empty wheat tiles. 5) Water bonus windows. 6) Move.
**Special Mechanics Used:** 2 farm hands with zone assignment. No animals, no fertilizer, no land expansion.
**Weaknesses:** Tomato price is moderate — 10 plants x 1 unit/day x $60 = $600/day peak, much lower than melon. Wheat adds ~$300/day. Combined ~$900/day is solid but not exceptional. Tomato market may be crowded by opponent growing tomatoes simultaneously.

---

### Agent 50: Melon Bail-Out
**Tier:** 5
**Core Strategy:** Grow 8 melons as primary strategy, but monitor melon price every day. If melon price drops below $100 for 2 consecutive checks, immediately bail out: harvest everything, DIG, and replant all tiles with wheat for the remainder of the game.
**Crop Focus:** Melon (primary), Wheat (bail-out fallback)
**Decision Logic:**
- Day 0: Buy 8 melon seeds ($640), hire 1 hand. Plant all 8. Plant 5 wheat tiles for early income.
- Each day, record melon_price. If melon_price < $100 for the last 2 consecutive day-checks: trigger BAIL_OUT.
- BAIL_OUT procedure: next turn, harvest any mature melons (collect what you can). DIG all immature melon tiles immediately (forfeit seed investment). Plant wheat on every freed tile. Buy 20 wheat seeds. Switch all future market orders to wheat.
- If bail-out triggered before day 10 (melons not yet mature): lose all seed investment, but recover board space for wheat cycling. With 20 days left at $300/day wheat, can still earn $6,000.
- If bail-out triggered after day 15 (most melons already harvested): mostly irrelevant, just plant wheat anyway.
- If no bail-out by day 10: harvest melons, sell normally at 4/day. Replant for cycle 2 only if day <= 18.
- Normal sell (no bail-out): 4 melons/day with price >= $120 gate. Hold below $120.
**Market Behaviour:** Normal mode: sell 4 melons/day at $120+. Bail-out mode: sell all melons immediately (best price you can get), then sell all wheat daily. Buy wheat seeds on bail-out trigger.
**Farmer Actions (priority):** Normal: 1) Water consecutive_unwatered=1. 2) Harvest at max. 3) Plant melon if day <= 18. 4) Water bonus windows. 5) Harvest wheat. 6) Move. Bail-out: 1) Harvest any mature melons. 2) DIG immature melons. 3) Plant wheat. 4) Water wheat. 5) Move.
**Special Mechanics Used:** Daily price monitoring with bail-out trigger. DIG for emergency replanting. 1 farm hand. No animals, no fertilizer.
**Weaknesses:** Bail-out sacrifices all seed investment ($640) and turns spent watering. Price threshold ($100) may trigger too early if melon is temporarily low but recovering. If opponent causes a price dip and you bail while they hold, they benefit from your exit.

---

## Summary Table

| # | Name | Tier | Core Focus | Key Mechanic |
|---|------|------|-----------|--------------|
| 1 | Wheat Grinder | 1 | Wheat | Continuous cycling |
| 2 | Carrot Sprinter | 1 | Carrot | 3-day cycle speed |
| 3 | Melon Baron | 1 | Melon | Batch sell at day 10 |
| 4 | Tomato Perennial | 1 | Tomato | 4-yield ongoing harvest |
| 5 | Strawberry Hedge | 1 | Strawberry | High base price ongoing |
| 6 | Egg Factory | 1 | Goose/Egg | Daily stable egg income |
| 7 | Milk Machine | 1 | Cow/Milk | Care-boosted milk drip |
| 8 | Wool Weaver | 1 | Sheep/Wool | Slow sell to preserve price |
| 9 | Wheat Feeder | 1 | Wheat | Stockpile for day-20 surge |
| 10 | Fertilizer Seller | 1 | Goose/Fertilizer | Fertilizer as revenue |
| 11 | Wheat-Melon Alternator | 2 | Wheat + Melon | Cash flow + periodic payout |
| 12 | Carrot-Tomato Relay | 2 | Carrot + Tomato | Fast + ongoing relay |
| 13 | Melon-Strawberry Premium Pair | 2 | Melon + Strawberry | Staggered premium sells |
| 14 | Wheat Flood + Timing | 2 | Wheat | Price-gated selling |
| 15 | Early Bird Melon | 2 | Melon + Fertilizer | Fertilize for day-8 harvest |
| 16 | Goose-Wheat Dual Income | 2 | Wheat + Goose | Feed loop + stable baseline |
| 17 | Tomato Fertilizer Maximizer | 2 | Tomato + Fertilizer | 2x yield via fertilizer |
| 18 | NE Quadrant Expander | 2 | Wheat | Land expansion throughput |
| 19 | Late-Game Strawberry Spike | 2 | Strawberry | Hold and sell at day-20 |
| 20 | Carrot-Wheat Market Watcher | 2 | Carrot + Wheat | Price-based dynamic allocation |
| 21 | Goose Fertilizer Melon Engine | 3 | Melon + Goose | Free fertilizer for early harvest |
| 22 | Cow Milk Drip Seller | 3 | Wheat + Cow | Fertilizer on wheat + milk |
| 23 | Three-Crop Rotation | 3 | Wheat+Carrot+Melon | Zone-based multi-crop |
| 24 | Sheep Wool + Wheat | 3 | Sheep + Wheat | Fertilized wheat + slow wool |
| 25 | Strawberry-Egg Cafe Exploit | 3 | Strawberry + Goose | Shop demand targeting |
| 26 | Land Baron | 3 | Wheat (3 quadrants) | 75-tile wheat empire |
| 27 | Melon-Goose Portfolio | 3 | Melon + Goose | Fertilizer pipeline to melon |
| 28 | Shop-Responsive Diversifier | 3 | Dynamic | Town shop unlock following |
| 29 | Fertilizer Arbitrageur | 3 | Goose + Fertilizer + Tomato | Fertilizer income + 2x tomato |
| 30 | Opponent Crop Mirror | 3 | Dynamic (opposite of opponent) | Anti-competition crop choice |
| 31 | Melon Price Sniper | 4 | Melon | Front-run opponent harvest |
| 32 | Adaptive Income Maximizer | 4 | Wheat + Melon + Goose | Phase-based multi-stream |
| 33 | Town Demand Predictor | 4 | Strawberry + Cow | Pre-position for shop demand |
| 34 | Price Momentum Seller | 4 | Melon | Rolling price momentum gates sells |
| 35 | Compound Goose Empire | 4 | Goose (up to 20) | Reinvest into geese |
| 36 | Nearest-Task Greedy | 4 | Melon + Wheat | Per-turn Manhattan-distance task sort |
| 37 | Dual-Quadrant Melon Specialist | 4 | Melon (50 tiles) | Staggered harvest, land expansion |
| 38 | Wheat-Egg Steady State | 4 | Wheat + Goose | Minimal stable two-system loop |
| 39 | Late-Game Cash Surge | 4 | Melon + Strawberry + Goose | Max day-20 surge exploitation |
| 40 | Opponent Money Watcher | 4 | Melon + Wheat | Adjust sell rate from opponent gain delta |
| 41 | Staggered Melon Pipeline | 5 | Melon | 3-melon waves every 3 days |
| 42 | Carrot-Rush-to-Melon | 5 | Carrot → Melon | Early carrot funds late melon wave |
| 43 | Four-Hand Wheat Blitz | 5 | Wheat | Max hands on single crop |
| 44 | Melon Micro-Seller | 5 | Melon | 1 unit per 3 turns, inventory-gated |
| 45 | Fertilized Wheat via Geese | 5 | Wheat + Goose | 2 geese as fertilizer engine for wheat |
| 46 | Day-6 Melon Planter | 5 | Wheat → Melon | Late planting targets day-20 demand |
| 47 | Tomato Two-Wave | 5 | Tomato | Two sequential tomato plantings |
| 48 | Goose Snowball | 5 | Goose | Reinvest egg income into more geese |
| 49 | Wheat-Tomato Split | 5 | Wheat + Tomato | 12+10 fixed split, steady state |
| 50 | Melon Bail-Out | 5 | Melon → Wheat | Price-triggered emergency pivot |
