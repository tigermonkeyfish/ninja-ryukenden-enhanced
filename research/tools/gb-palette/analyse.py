"""Compare record.py traces.

identity A B: per run, frames whose screenshot / VCE / SAT / gameplay fields /
  RAM hash differ between two recordings (TAG_A-<run>.json, TAG_B-<run>.json).
gb TAG: per run, frames whose VCE differs from the GB table value of the
  RAM palette, grouped into stretches; for each stretch its length and the
  queue state at its start, and the longest stretch; frames with a full
  queue (8 entries at the frame boundary); the gameplay comparison with an
  Original-mode recording if TAG_ORIG is given.
usage: analyse.py DIR identity TAG_A TAG_B | analyse.py DIR gb TAG [TAG_ORIG]"""
import json
import sys
from pathlib import Path

from gbtools import RUN_NAMES

GAMEPLAY = ('ryu', 'timer', 'cam', 'area', 'stage', 'lives', 'health', 'sat', 'master', 'boss')


def load(d, tag, name):
    return json.loads((Path(d) / f'{tag}-{name}.json').read_text())


def stretches(frames):
    out = []
    for f in frames:
        if out and out[-1][1] == f - 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return out


def identity(d, a, b):
    total = {}
    for name in RUN_NAMES:
        A, B = load(d, a, name), load(d, b, name)
        row = {'frames': (len(A), len(B))}
        for key in ('png', 'vce', 'sat', 'ram') + GAMEPLAY:
            diff = [x['f'] for x, y in zip(A, B) if x[key] != y[key]]
            if diff or key in ('png', 'vce'):
                row[key] = (len(diff), stretches(diff)[:6])
        total[name] = row
        print(name, json.dumps(row), flush=True)
    return total


def gb(d, tag, orig=None):
    for name in RUN_NAMES:
        T = load(d, tag, name)
        bad = [e['f'] for e in T if e['gb']]
        st = stretches(bad)
        lengths = [b - a + 1 for a, b in st]
        full = [e['f'] for e in T if e['qn'] >= 8]
        maxq = max(e['qn'] for e in T)
        row = {'frames': len(T), 'mismatch_frames': len(bad), 'stretches': len(st),
               'longest': max(lengths, default=0), 'longest_at': st[lengths.index(max(lengths))] if st else None,
               'max_queue': maxq, 'full_queue_frames': full[:10]}
        if orig:
            O = load(d, orig, name)
            row['gameplay_differs'] = {k: sum(1 for x, y in zip(T, O) if x[k] != y[k]) for k in GAMEPLAY}
            row['orig_full_queue_frames'] = [e['f'] for e in O if e['qn'] >= 8][:10]
            row['orig_max_queue'] = max(e['qn'] for e in O)
        print(name, json.dumps(row), flush=True)


if __name__ == '__main__':
    d, mode = sys.argv[1], sys.argv[2]
    if mode == 'identity':
        identity(d, sys.argv[3], sys.argv[4])
    else:
        gb(d, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
