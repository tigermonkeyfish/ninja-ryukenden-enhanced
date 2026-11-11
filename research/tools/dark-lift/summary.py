"""Compact summary of record11.py recordings of two builds (research
reference, not a maintained tool): per mode, over the 11 stored runs,
- the frames whose picture, VCE, sprite table, game RAM or gameplay fields
  differ between the builds (per run);
- the frames in which a VCE entry is not yet what the mode is due for its
  RAM colour (each recording against the tables of the scripts that made
  it), for both builds, and the longest lag;
- the gameplay fields and sprite table against the same build in Original;
- SMS: gameplay frames with a VCE entry outside the 64 colours or a pixel
  channel value other than levels 0, 2, 5, 7, for both builds.
usage: summary.py REC OLD NEW [modes]   (recordings REC/<OLD|NEW>-<mode>-<run>.json)"""
import json
import sys
from pathlib import Path

RUNS = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']
FIELDS = ('png', 'vce', 'sat', 'ram')
GAMEPLAY = ('ryu', 'timer', 'cam', 'area', 'stage', 'lives', 'health', 'master', 'boss')
rec, old, new = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
modes = sys.argv[4].split(',') if len(sys.argv) > 4 else ['orig', 'gb', 'sms', 'hell', 'nesa', 'nesb']


def load(tag, mode, run):
    return json.loads((rec / f'{tag}-{mode}-{run}.json').read_text())


def longest(trace):
    run, best = {}, 0
    for e in trace:
        bad = set()
        if e['master'] == 0:
            for a, b in e['bad']:
                bad.update(range(a, b + 1))
        run = {i: run.get(i, 0) + 1 for i in bad}
        best = max([best] + list(run.values()))
    return best


levels = None
for mode in modes:
    print(f'\n== {mode}')
    total = 0
    for run in RUNS:
        A, B = load(old, mode, run), load(new, mode, run)
        O = B if mode == 'orig' else load(new, 'orig', run)
        total += len(B)
        diff = {k: sum(1 for x, y in zip(A, B) if x[k] != y[k]) for k in FIELDS}
        diff['gameplay'] = sum(1 for x, y in zip(A, B) if any(x[k] != y[k] for k in GAMEPLAY))
        vs_orig = {k: sum(1 for x, y in zip(B, O) if x[k] != y[k]) for k in GAMEPLAY + ('sat',)}
        vs_orig = {k: v for k, v in vs_orig.items() if v}
        due = [sum(1 for e in T if e['bad'] and e['master'] == 0) for T in (A, B)]
        line = (f'{run}: frames {len(A)}/{len(B)}; differ {old}->{new}: ' +
                ' '.join(f'{k} {v}' for k, v in diff.items()) +
                f'; not due {old} {due[0]} {new} {due[1]}, longest lag {longest(A)}/{longest(B)}; '
                f'gameplay vs Original: {vs_orig or "identical"}')
        if mode == 'sms':
            if levels is None:
                values = sorted({v for r in RUNS for e in load(new, 'orig', r) for v in e['pix']})
                levels = {values[i] for i in (0, 2, 5, 7)}
            cells = []
            for T in (A, B):
                play = [e for e in T if e['master'] == 0]
                cells.append(f"{sum(1 for e in play if e['nonsms'])} VCE / {sum(1 for e in play if set(e['pix']) - levels)} pixel")
            line += f'; gameplay frames with non-SMS colours {old} {cells[0]}, {new} {cells[1]}'
        print(line, flush=True)
    print(f'{mode}: {total} frames')
