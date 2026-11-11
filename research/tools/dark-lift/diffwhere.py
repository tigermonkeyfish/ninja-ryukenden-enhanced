"""Where two builds' record11.py recordings differ (research reference, not a
maintained tool): per mode and run, the frames whose picture, VCE or game
RAM differ, as ranges, against the run's end in the newer recording: the
first frame the visible stage changes ('load') or the first cinema frame
('cinema', $2240 != 0). The fade rule can change frames only from the
stage-end fade-out's last step (about 10 frames before that end) through
the load and the next stage's fade-in, or into the cinema's first frames:
the window is from 22 frames before the end to 95 frames after a load, or
to the recording's end after a cinema. A difference elsewhere is listed as
OUTSIDE.
usage: diffwhere.py REC OLD NEW modes(comma)"""
import json
import sys
from pathlib import Path

RUNS = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']
rec, old, new = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
modes = sys.argv[4].split(',')


def ranges(frames):
    out = []
    for f in frames:
        if out and out[-1][1] == f - 1:
            out[-1][1] = f
        else:
            out.append([f, f])
    return ' '.join(f'{a}-{b}' if a != b else str(a) for a, b in out)


outside_total = 0
for mode in modes:
    print(f'== {mode}')
    for run in RUNS:
        A = json.loads((rec / f'{old}-{mode}-{run}.json').read_text())
        B = json.loads((rec / f'{new}-{mode}-{run}.json').read_text())
        stage0 = B[0]['stage']
        load = next((i for i, e in enumerate(B) if e['stage'] != stage0), None)
        cinema = next((i for i, e in enumerate(B) if e['master'] != 0), None)
        end = min(x for x in (load, cinema, len(B)) if x is not None)
        lo, hi = end - 22, (end + 96 if load is not None and end == load else len(B))
        cells = []
        for k in ('png', 'vce', 'ram'):
            d = [i for i, (x, y) in enumerate(zip(A, B)) if x[k] != y[k]]
            out = [i for i in d if not lo <= i < hi]
            outside_total += len(out)
            cells.append(f'{k} {len(d)} [{ranges(d)}]' + (f' OUTSIDE {ranges(out)}' if out else ''))
        what = f'load at {load}' if load is not None and end == load else (f'cinema at {cinema}' if cinema is not None else 'no stage end')
        print(f'{run} ({what}; window {lo}-{hi - 1}): ' + '; '.join(cells))
print('frames differing outside the windows:', outside_total)
