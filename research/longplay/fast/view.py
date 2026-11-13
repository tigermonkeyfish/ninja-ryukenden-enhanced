#!/usr/bin/env python3
"""Play segments from a state and save a screenshot (and the state) at frame N (diagnostic).
    view.py STATE SEGMENTS.json N OUT.png [--path]"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastemu import Fast  # noqa: E402

st, sf, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
f = Fast(); f.load(st)
segs = json.loads(Path(sf).read_text())['segments']
t, last = 0, None
for c, b in segs:
    for _ in range(c):
        if t >= n:
            break
        f.step(1, b); t += 1
        if '--path' in sys.argv and t % 8 == 0:
            i = f.info(); print(t, i['area'], i['x'], i['y'], i['health'], i['state'], b)
f.step(1, render=True)
print(t, f.info())
f.screenshot(out)
Path(out + '.state').write_bytes(f.save())
