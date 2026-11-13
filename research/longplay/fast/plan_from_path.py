#!/usr/bin/env python3
"""Write a follow-path plan from a recorded path: one beam leg per area, long
areas cut into chunks of about --chunk path frames that end on a grounded path
point (so a solved chunk is cached and a retry only redoes the chunk that
failed).
    plan_from_path.py STAGE [--width 60] [--chunk 500]
Reads research/longplay/paths/STAGE.json, writes research/longplay/plans/STAGE.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
stage = sys.argv[1]
opt = lambda k, d: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
width, chunk = opt('--width', 60), opt('--chunk', 500)
pfile = f'research/longplay/paths/{stage}.json'
path = json.loads((ROOT / pfile).read_text())['path']
st0 = path[0][5]
spans, cur = [], None
for r in path:
    fr, area, stg = r[0], r[1], r[5]
    if stg != st0:
        break
    if cur is None or area != cur[0]:
        cur = [area, fr, fr]
        spans.append(cur)
    cur[2] = fr
legs = []
for i, (area, lo, hi) in enumerate(spans):
    last = i == len(spans) - 1
    final_goal = {'stage_change': True} if last else {'area': spans[i + 1][0]}
    # chunk boundaries on grounded points
    cuts, at = [], lo
    while hi - at > chunk * 1.5:
        cands = [r for r in path if at + chunk - 200 <= r[0] <= at + chunk + 200 and r[1] == area
                 and len(r) > 6 and r[6] in (0, 1)]
        if not cands:
            break
        c = min(cands, key=lambda r: abs(r[0] - (at + chunk)))
        cuts.append(c)
        at = c[0]
    bounds = [lo] + [c[0] for c in cuts] + [hi]
    for k in range(len(bounds) - 1):
        a, b = bounds[k], bounds[k + 1]
        if k < len(cuts):
            c = cuts[k]
            goal = {'near': [c[2], c[3], 12, 6], 'in_area': area}
        else:
            goal = final_goal
        n = b - a + 1
        legs.append({'name': f'a{area}-{i}-{k}',
                     'beam': {'follow': {'path': pfile, 'from_frame': a, 'to_frame': b},
                              'goal': goal, 'width': width, 'max_frames': max(900, 3 * n),
                              'seconds': max(900, 3 * n)}})
plan = {'stage': stage,
        'notes': (f'The Level Select comparison run (research/comparison-runs/{stage}.json) is the guide: its path, '
                  'recorded on the original through Level Select (research/longplay/fast/runpath.py, '
                  f'{pfile}), gives beam waypoints (standing/walking/clinging points about every 40 frames), '
                  f'one leg per area, long areas in chunks of about {chunk} path frames.'),
        'legs': legs}
out = ROOT / f'research/longplay/plans/{stage}.json'
out.write_text(json.dumps(plan, indent=1) + '\n')
print(out, [(l['name'], l['beam']['goal'], l['beam']['follow']['from_frame'], l['beam']['follow']['to_frame']) for l in legs])
