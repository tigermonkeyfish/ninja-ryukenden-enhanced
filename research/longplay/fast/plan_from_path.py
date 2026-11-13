#!/usr/bin/env python3
"""Write a follow-path plan (one beam leg per area) from a recorded path.
    plan_from_path.py STAGE [--width 60] [--boss]
Reads research/longplay/paths/STAGE.json, writes research/longplay/plans/STAGE.json."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
stage = sys.argv[1]
width = int(sys.argv[sys.argv.index('--width') + 1]) if '--width' in sys.argv else 60
path = json.loads((ROOT / f'research/longplay/paths/{stage}.json').read_text())['path']
st0 = path[0][5]
spans, cur = [], None
for r in path:
    fr, area, stg = r[0], r[1], r[5]
    if stg != st0:
        break
    if cur is None or area != cur[0]:
        if cur:
            cur[2] = fr - 1
        cur = [area, fr, fr]
        spans.append(cur)
    cur[2] = fr
legs = []
for i, (area, lo, hi) in enumerate(spans):
    last = i == len(spans) - 1
    goal = {'stage_change': True} if last else {'area': spans[i + 1][0]}
    n = hi - lo + 1
    legs.append({'name': f'a{area}' if not any(l['name'] == f'a{area}' for l in legs) else f'a{area}-{i}',
                 'beam': {'follow': {'path': f'research/longplay/paths/{stage}.json', 'from_frame': lo,
                                     'to_frame': hi},
                          'goal': goal, 'width': width, 'max_frames': max(600, 2 * n),
                          'seconds': max(600, n)}})
plan = {'stage': stage,
        'notes': (f'The Level Select comparison run (research/comparison-runs/{stage}.json) is the guide: its path, '
                  'recorded on the original through Level Select (research/longplay/fast/runpath.py, '
                  f'research/longplay/paths/{stage}.json), gives beam waypoints (grounded/clinging points about '
                  'every 40 frames), one leg per area.'),
        'legs': legs}
out = ROOT / f'research/longplay/plans/{stage}.json'
out.write_text(json.dumps(plan, indent=1) + '\n')
print(out, [(l['name'], l['beam']['goal'], l['beam']['follow']['from_frame'], l['beam']['follow']['to_frame']) for l in legs])
