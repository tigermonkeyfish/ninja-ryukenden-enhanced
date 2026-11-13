#!/usr/bin/env python3
"""Turn a stalled beam leg into a fixed leg: the failed route (from the stage
start file) cut at frame T, plus hand segments, plus 'until landing' frames;
replace the leg in the plan by that fixed leg and a beam leg continuing the
same goal (follow from path frame F if the leg follows a path).
    rescue.py STAGE LEG T 'SEGMENTS_JSON' STEER_JSON [FROM_FRAME]
Diagnostic tooling for grid-found moves (all of it is button input)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastemu import Fast  # noqa: E402

stage, legname, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
extra, steer = json.loads(sys.argv[4]), json.loads(sys.argv[5])
from_frame = int(sys.argv[6]) if len(sys.argv) > 6 else None
ROOT = Path(__file__).resolve().parents[3]
pp = ROOT / f'research/longplay/plans/{stage}.json'
plan = json.loads(pp.read_text())
prev = 0
for l in plan['legs']:
    if l['name'] == legname:
        break
    src = l['segments'] if 'segments' in l else json.loads(Path(f'/workspace/build/longplay/legs/{stage}.{l["name"]}.json').read_text())['segments']
    prev += sum(n for n, _ in src)
segs = json.loads(Path(f'/workspace/build/longplay/legs/{stage}.{legname}.failed.json').read_text())['segments']
flat = []
for n, b in segs:
    flat += [b] * n
f = Fast()
f.load(next(Path('/workspace/build/longplay/states').glob('full-*.state')))
f.play([[1, b] for b in flat[:T]])
f.play(extra)
k = 0
while k < 300:
    f.step(1, steer)
    k += 1
    i = f.info()
    if i['state'] in (0, 1) and i['vy'] == 0 and k > 2:
        break
print('lands', k, i)
comp = []
for b in flat[prev:T]:
    if comp and comp[-1][1] == b:
        comp[-1][0] += 1
    else:
        comp.append([1, b])
comp += extra + [[k, steer]]
idx = [x['name'] for x in plan['legs']].index(legname)
old = plan['legs'][idx]
new_beam = dict(old['beam'])
if from_frame is not None and 'follow' in new_beam:
    fl = dict(new_beam['follow'])
    fl['from_frame'] = from_frame
    fl.pop('add_points', None)
    new_beam['follow'] = fl
plan['legs'][idx:idx + 1] = [{'name': legname + '-fix', 'segments': comp},
                             {'name': legname + '-b', 'beam': new_beam}]
pp.write_text(json.dumps(plan, indent=1) + '\n')
