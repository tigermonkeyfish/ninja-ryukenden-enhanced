"""Compare record.py traces (DIR/TAG-<run>.json).

identity TAG_A TAG_B: per run, the frames whose screenshot, VCE, sprite
  table, game RAM or gameplay fields differ (all must be 0 for identity).
due TAG [TAG_REF]: per run, the frames in which some VCE entry is not yet
  what the mode is due for its RAM colour ('bad'), the most entries at
  once, the longest run of consecutive frames one entry lags (gameplay
  frames, $2240 = 0) and where, frames with a full queue (8 entries); with
  TAG_REF (the same build in Original mode) also the gameplay fields that
  differ from it and the reference's own longest lag.
state TAG_OLD TAG_NEW: per run, the frames where the old build's $2100
  (options and, in bits 5-7, the palette module's state) differs from the new
  build's $2100 | $2104 (the state moved to $2104 bits 5-7), and the frames
  where the new $2100 has bits 5-7 set (it must not: SMS is not recorded by
  this check).
sms TAG TAG_ORIG: SMS on screen. From TAG_ORIG (the same build in Original
  mode) the 8 channel values the emulator shows for PC Engine levels 0-7;
  per run of TAG, the gameplay frames ($2240 = 0) with a VCE entry that is
  not one of the 64 SMS colours ('nonsms') or a pixel channel value other
  than those of levels 0, 2, 5 and 7 ('pix'), and the cinema frames with
  such pixels (counted apart: cinemas keep the original colours).
usage: analyse.py DIR identity TAG_A TAG_B | analyse.py DIR due TAG [TAG_REF]
       | analyse.py DIR state TAG_OLD TAG_NEW | analyse.py DIR sms TAG TAG_ORIG"""
import json
import sys
from pathlib import Path

from smstools import RUN_NAMES

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


def state(d, old, new):
    clean = True
    for name in RUN_NAMES:
        A, B = load(d, old, name), load(d, new, name)
        diff = [x['f'] for x, y in zip(A, B) if x['opts'] != y['opts'] | y['st']]
        high = [y['f'] for y in B if y['opts'] & 0xe0]
        clean = clean and not diff and not high and len(A) == len(B)
        print(name, json.dumps({'frames': (len(A), len(B)), 'state_differs': len(diff),
                                'at': stretches(diff)[:6], 'new_2100_bits_5_7': len(high)}), flush=True)
    print('same state' if clean else 'DIFFERENCES')


def sms(d, tag, orig):
    values = sorted({v for name in RUN_NAMES for e in load(d, orig, name) for v in e['pix']})
    if len(values) != 8:
        raise SystemExit(f'expected 8 channel values in {orig}, found {values}')
    allowed = {values[i] for i in (0, 2, 5, 7)}
    print('channel values for levels 0-7', values, '; SMS levels 0, 2, 5, 7:', sorted(allowed))
    clean = True
    for name in RUN_NAMES:
        T = load(d, tag, name)
        play = [e for e in T if e['master'] == 0]
        vce_bad = [e['f'] for e in play if e['nonsms']]
        pix_bad = [e['f'] for e in play if set(e['pix']) - allowed]
        cinema_pix = [e['f'] for e in T if e['master'] != 0 and set(e['pix']) - allowed]
        clean = clean and not vce_bad and not pix_bad
        print(name, json.dumps({'frames': len(T), 'gameplay_frames': len(play), 'nonsms_vce_frames': len(vce_bad),
                                'nonsms_vce_at': stretches(vce_bad)[:6], 'nonsms_pixel_frames': len(pix_bad),
                                'nonsms_pixel_at': stretches(pix_bad)[:6],
                                'cinema_frames': len(T) - len(play), 'cinema_frames_with_other_colours': len(cinema_pix)}),
              flush=True)
    print('every gameplay frame in SMS colours' if clean else 'NON-SMS COLOURS IN GAMEPLAY')


if __name__ == '__main__':
    d, mode = sys.argv[1], sys.argv[2]
    if mode == 'identity':
        identity(d, sys.argv[3], sys.argv[4])
    elif mode == 'state':
        state(d, sys.argv[3], sys.argv[4])
    elif mode == 'sms':
        sms(d, sys.argv[3], sys.argv[4])
    else:
        due(d, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
