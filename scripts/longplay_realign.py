#!/usr/bin/env python3
"""Re-aligned replay helper (secondary diagnostic, emulator evidence only).

    build  ORIG.json ADJ.json OUT.json [--upto STAGE --slack N]
        ADJ.json is a list of {"frame": F, "frames": +-N, "handover": text}: F is the frame of the
        ORIGINAL recording at which the idle (no button) stretch ends and the next stage's
        gameplay input starts; N idle frames are added (+) or removed (-) at the END of that
        stretch. Only the idle-segment length changes; gameplay inputs and their order do not.
        Stage markers and the end marker are shifted to the new frame numbers. --upto cuts the
        recording N frames after that stage's (shifted) start marker, for quick partial runs.
    starts RAWDIR TAG
        Prints the first gameplay frame (stage byte, master flags 0) of each stage.
"""
import argparse, array, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from comparison_video import STAGE_NAMES  # noqa: E402


def build(orig, adjs, upto=None, slack=600):
    adjs = sorted(adjs, key=lambda a: a['frame'])
    shift = lambda x: x + sum(a['frames'] for a in adjs if a['frame'] <= x)
    segs = [[n, list(b)] for n, b in orig['segments']]
    pos = 0
    starts = []
    for n, b in segs:
        starts.append(pos); pos += n
    for a in adjs:
        i = starts.index(a['frame'])           # segment that starts at F; the idle stretch is segment i-1
        j = i - 1
        assert segs[j][1] == [], f'no idle segment before frame {a["frame"]}'
        segs[j][0] += a['frames']
        assert segs[j][0] >= 0
    run = json.loads(json.dumps(orig))
    run['segments'] = [[n, b] for n, b in segs if n > 0]
    run['adjustments'] = adjs
    run['based_on'] = 'full.json (idle frames in hand-over stretches only)'
    for s in run['stages']:
        for k in ('start_frame', 'end_frame'):
            s[k] = shift(s[k])
    run['end'] = dict(run['end'], frame=shift(run['end']['frame']))
    run['frames'] = sum(n for n, _ in run['segments'])
    if upto:
        names = [s['name'] for s in run['stages']]
        k = names.index(upto)
        cut = run['stages'][k]['start_frame'] + slack
        out, left = [], cut
        for n, b in run['segments']:
            if left <= 0: break
            out.append([min(n, left), b]); left -= n
        run['segments'] = out
        run['stages'] = run['stages'][:k + 1]
        run.pop('end'); run['frames'] = cut
    return run


def starts(raw, tag):
    stg = array.array('B'); stg.frombytes((Path(raw) / f'{tag}.stg.bin').read_bytes())
    mas = array.array('B'); mas.frombytes((Path(raw) / f'{tag}.mas.bin').read_bytes())
    res = {}
    for f in range(1, len(stg) + 1):
        if mas[f - 1] == 0 and stg[f - 1] not in res.values() and stg[f - 1] < len(STAGE_NAMES):
            res[f] = stg[f - 1]
    return {STAGE_NAMES[v]: f for f, v in res.items()}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('orig'); b.add_argument('adj'); b.add_argument('out')
    b.add_argument('--upto'); b.add_argument('--slack', type=int, default=600)
    s = sub.add_parser('starts'); s.add_argument('raw'); s.add_argument('tag')
    a = ap.parse_args()
    if a.cmd == 'build':
        r = build(json.load(open(a.orig)), json.load(open(a.adj)), a.upto, a.slack)
        json.dump(r, open(a.out, 'w'))
        print('frames', r['frames'], 'stages', len(r['stages']))
    else:
        print(starts(a.raw, a.tag))
