"""Compare record.py traces (DIR/TAG-<run>.json).

identity TAG_A TAG_B: per run, the frames whose screenshot, VCE, sprite
  table, game RAM or gameplay fields differ (all must be 0 for identity).
due TAG [TAG_REF]: per run, the frames in which some VCE entry is not yet
  what the mode is due for its RAM colour ('bad'), the most entries at
  once, the longest run of consecutive frames one entry lags (gameplay
  frames, $2240 = 0) and where, frames with a full queue (8 entries); with
  TAG_REF (the same build in Original mode) also the gameplay fields that
  differ from it and the reference's own longest lag.
usage: analyse.py DIR identity TAG_A TAG_B | analyse.py DIR due TAG [TAG_REF]"""
import json
import sys
from pathlib import Path

from helltools import RUN_NAMES

GAMEPLAY = ('ryu', 'timer', 'cam', 'area', 'stage', 'lives', 'health', 'master', 'boss')


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
    clean = True
    for name in RUN_NAMES:
        A, B = load(d, a, name), load(d, b, name)
        row = {'frames': (len(A), len(B))}
        for key in ('png', 'vce', 'sat', 'ram') + GAMEPLAY:
            diff = [x['f'] for x, y in zip(A, B) if x[key] != y[key]]
            row[key] = len(diff)
            if diff:
                row[key + '_at'] = stretches(diff)[:6]
                clean = False
        clean = clean and len(A) == len(B)
        print(name, json.dumps(row), flush=True)
    print('identical' if clean else 'DIFFERENCES')


def longest(trace):
    run, best = [0] * 512, (0, None, None)
    for e in trace:
        bad = set()
        if e['master'] == 0:
            for a, b in e['bad']:
                bad.update(range(a, b + 1))
        for i in range(512):
            run[i] = run[i] + 1 if i in bad else 0
            if run[i] > best[0]:
                best = (run[i], i, e['f'])
    return best


def due(d, tag, ref=None):
    worst = (0, None)
    for name in RUN_NAMES:
        T = load(d, tag, name)
        bad = [e['f'] for e in T if e['bad'] and e['master'] == 0]
        most = max((sum(b - a + 1 for a, b in e['bad']) for e in T if e['master'] == 0), default=0)
        lag, entry, at = longest(T)
        row = {'frames': len(T), 'frames_not_due': len(bad), 'stretches': len(stretches(bad)), 'most_at_once': most,
               'longest_lag': lag, 'lag_entry': entry, 'lag_ends_frame': at,
               'full_queue_frames': [e['f'] for e in T if e['qn'] >= 8][:10]}
        if lag > worst[0]:
            worst = (lag, f'{name} entry {entry} ending frame {at}')
        if ref:
            R = load(d, ref, name)
            row['gameplay_differs'] = {k: sum(1 for x, y in zip(T, R) if x[k] != y[k]) for k in GAMEPLAY + ('sat',)}
            row['ref_longest_lag'] = longest(R)[0]
            row['ref_full_queue_frames'] = [e['f'] for e in R if e['qn'] >= 8][:10]
        print(name, json.dumps(row), flush=True)
    print('longest lag over all runs', worst)


if __name__ == '__main__':
    d, mode = sys.argv[1], sys.argv[2]
    if mode == 'identity':
        identity(d, sys.argv[3], sys.argv[4])
    else:
        due(d, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
