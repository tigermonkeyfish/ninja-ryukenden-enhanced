"""Per-entry lag in GB DMG recordings: for every VCE entry, the longest run of
consecutive frames in which it differed from the table value of its RAM
colour (gameplay frames only), and where; also the same for the Original
recording against the raw RAM colour (the native game's own lag: locks,
colours written before they are queued). usage: lag.py DIR TAG_GB TAG_ORIG"""
import json
import sys
from pathlib import Path

from gbtools import RUN_NAMES


def longest(trace, key):
    run = [0] * 512
    best = (0, None, None)
    hist = {}
    for e in trace:
        bad = set()
        if e['master'] == 0:
            for a, b in e[key]:
                bad.update(range(a, b + 1))
        for i in range(512):
            if i in bad:
                run[i] += 1
                if run[i] > best[0]:
                    best = (run[i], i, e['f'])
            elif run[i]:
                hist[run[i]] = hist.get(run[i], 0) + 1
                run[i] = 0
    return best, hist


d, tg, to = sys.argv[1:4]
for name in RUN_NAMES:
    G = json.loads((Path(d) / f'{tg}-{name}.json').read_text())
    O = json.loads((Path(d) / f'{to}-{name}.json').read_text())
    (gl, gi, gf), gh = longest(G, 'gb')
    (ol, oi, of), oh = longest(O, 'raw')
    over8 = sum(v for k, v in gh.items() if k > 8)
    print(f'{name}: GB longest {gl} frames (entry {gi}, ending frame {gf}); stretches > 8 frames: {over8}; '
          f'Original longest {ol} (entry {oi}, frame {of})', flush=True)
