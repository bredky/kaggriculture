# Analyze Replay

Analyze the most recent Kaggriculture replay with full turn-by-turn detail.

## Steps

1. Run this command to extract full turn-by-turn actions from replay.json:
```
python3.11 -c "
import json
with open('replay.json') as f:
    data = json.load(f)
steps = data['steps']
n = len(steps[0])
print(f'Steps: {len(steps)}, Players: {n}')
print(f'Final: ' + ' | '.join(f'P{i}=\${steps[-1][i][\"reward\"]:.0f}' for i in range(n)))
print()

for pid in range(n):
    print(f'=== P{pid} ALL NON-PASS ACTIONS ===')
    prev_money = None
    prev_shed = {}
    for idx, step in enumerate(steps):
        obs = step[pid].get('observation', {})
        if not obs: continue
        day, hour = obs.get('day',0), obs.get('hour',0)
        farms = obs.get('farms', [])
        if not farms or pid >= len(farms): continue
        farm = farms[pid]
        money = farm.get('money', 0)
        fx, fy = farm.get('farmer', [0,0])
        tiles = farm.get('tiles', [])
        private = obs.get('private', {}) or {}
        shed = private.get('shed', {}) or {}
        seeds = (private.get('seeds', {}) or {})
        market_price = ((obs.get('market',{}) or {}).get('prices',{}) or {}).get('MELON', 0)
        action = step[pid].get('action', {})
        farmer_act = action.get('farmer', ['PASS'])
        market_act = action.get('market', [])
        plants_on_farm = [(r,c,t) for r,row in enumerate(tiles) for c,t in enumerate(row) if isinstance(t,dict) and t.get('kind')=='PLANT']

        # Detect shed changes
        shed_changes = []
        for crop, qty in shed.items():
            diff = qty - prev_shed.get(crop, 0)
            if diff > 0:
                shed_changes.append(f'HARVESTED {diff} {crop} (shed now={qty})')

        # Detect money changes
        money_change = ''
        if prev_money is not None and money - prev_money > 100:
            money_change = f' [SOLD +\${money-prev_money:.0f} @ melon=\${market_price}]'
        elif prev_money is not None and money - prev_money < -50:
            money_change = f' [SPENT \${prev_money-money:.0f}]'

        is_interesting = (
            farmer_act != ['PASS'] or
            market_act or
            shed_changes or
            money_change
        )

        if is_interesting:
            plants_str = f'plants={len(plants_on_farm)}@{[(r,c) for r,c,t in plants_on_farm]}'
            seeds_str = f'seeds={seeds.get(\"MELON\",0)}'
            print(f'  D{day}h{hour}(s{idx}): pos=({fx},{fy}) {farmer_act} | market={market_act} | {plants_str} {seeds_str} \${money:.0f}{money_change}', end='')
            for sc in shed_changes:
                print(f' [{sc}]', end='')
            print()

        prev_money = money
        for c,q in shed.items(): prev_shed[c]=q
    print()
"
```

2. Based on the extracted turn-by-turn data, give a detailed analysis structured as:

**Cycle-by-cycle breakdown for each player:**
- Exact turn each action happened (D{day}h{hour} step {s})
- What the farmer did and where (position, action)
- When seeds were bought, how many
- When each plant went in the ground and at which tile
- Which hours were spent moving vs acting
- When harvests happened and yield
- When sells happened and at what price
- How many turns were wasted (PASS or idle movement)

**Head-to-head comparison:**
- First productive action each cycle
- Time from cycle start to all plants in ground
- Time from planting to harvest
- Total turns wasted per cycle
- Revenue per cycle

**What's costing turns:**
- Identify the specific hours where the agent is moving without purpose or PASSing
- Pinpoint exact inefficiencies with step numbers

Be precise and exhaustive. Use exact numbers. No vague summaries.
