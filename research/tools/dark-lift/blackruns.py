"""Black frames of the stored runs in SMS and HELL, from record11.py
recordings (research reference, not a maintained tool). In Original mode
the whole picture is black for some frames at a stage's end (the fade-out's
end, the load); SMS and HELL show black as $000 too, so in those frames a
mapped mode's picture must be the very same picture (the same PNG hash).
Per build and mode, over the 11 runs: the frames in which Original's
picture is that black picture and the mode's is not, split into those
before the mode's picture is first black (the fade-out arriving late) and
those after (a flash); and the VCE entries not yet due at the first frame of
the next stage (the load, which holds the lock).
usage: blackruns.py REC TAG[,TAG..] [modes]   (REC/TAG-<mode>-<run>.json; default modes sms,hell)"""
import json
import sys
from collections import Counter
from pathlib import Path

RUNS = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']
rec, tags = Path(sys.argv[1]), sys.argv[2].split(',')
modes = sys.argv[3].split(',') if len(sys.argv) > 3 else ['sms', 'hell']


def load(tag, mode, run):
    return json.loads((rec / f'{tag}-{mode}-{run}.json').read_text())


for tag in tags:
    orig = {run: load(tag, 'orig', run) for run in RUNS}
    # The black picture: the commonest picture among the 20 frames after a stage change.
    seen = Counter()
    for run, O in orig.items():
        change = next((i for i, e in enumerate(O) if e['stage'] != O[0]['stage']), None)
        if change is not None:
            seen.update(e['png'] for e in O[change:change + 8])
    black = seen.most_common(1)[0][0]
    for mode in modes:
        late = flash = total = 0
        lit = []
        detail = []
        for run in RUNS:
            O, M = orig[run], load(tag, mode, run)
            in_span, was_black, l, f = False, False, 0, 0
            for o, m in zip(O, M):
                inside = o['png'] == black and o['master'] == 0 and m['master'] == 0
                if inside and not in_span:
                    was_black = False
                if inside:
                    total += 1
                    if m['png'] == black:
                        was_black = True
                    elif was_black:
                        f += 1
                    else:
                        l += 1
                in_span = inside
            late += l
            flash += f
            change = next((i for i, e in enumerate(M) if e['stage'] != M[0]['stage']), None)
            if change is not None:
                n = sum(b - a + 1 for a, b in M[change]['bad'])
                lit.append(n)
                detail.append(f'{run}: late {l}, flash {f}, not due at the load {n}')
            elif l or f:
                detail.append(f'{run}: late {l}, flash {f}')
        print(f'{tag} {mode}: {total} frames in which Original is black; the mode not black: {late} before its first '
              f'black (late), {flash} after (flash); entries not due at the load: {lit}')
        print('   ' + '; '.join(detail))
