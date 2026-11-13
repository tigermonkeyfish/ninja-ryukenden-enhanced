"""Survey table: events of REF (unmodified) against other runs (load-exact; diagnostic, emulator only).

    survey_cmp.py REF.npz TAG=A.npz [TAG=B.npz ...]

One row per load / area change of REF: frame, stage, area, REF's vblanks and clocks left before the
next vblank for the event's update, and the smallest margin of the event's window (4 updates before
to 8 after); for each other run the same numbers for the event at the same frame and whether its
window's vblank pattern equals REF's. Rows within 20,000 clocks of a vblank are flagged (*).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import survey                                                          # noqa: E402


def main():
    ref = survey.events(sys.argv[1])
    # events are paired in order (a build one frame behind still has the same events)
    others = [(a.split('=')[0], survey.events(a.split('=')[1])) for a in sys.argv[2:]]
    hdr = '| Event | Frame | Stage | Original: vblanks / left / window min | ' + ' | '.join(
        f'{t}: vblanks / left / window min / pattern' for t, _ in others) + ' |'
    print(hdr)
    print('|' + ' --- |' * (4 + len(others)))
    for t, o in others:
        if len(o) != len(ref):
            print(f'<!-- {t}: {len(o)} events against {len(ref)} -->')
    bad = 0
    for i, e in enumerate(ref):
        mn = min(m for m in e['wmargin'] if m >= 0)
        row = [e['kind'], str(e['frame']), f"{e['stage']} a{e['area']}", f"{e['nv']} / {e['margin']:,} / {mn:,}"]
        for t, o in others:
            x = o[i] if i < len(o) and o[i]['kind'] == e['kind'] and o[i]['stage'] == e['stage'] else None
            if x is None:
                row.append('missing'); bad += 1; continue
            xm = min(m for m in x['wmargin'] if m >= 0)
            same = x['window'] == e['window']
            bad += not same
            flag = '*' if xm < 20000 else ''
            shift = x['upd_frame'] - e['upd_frame']
            row.append(f"{x['nv']} / {x['margin']:,} / {xm:,}{flag} / {'equal' if same else 'DIFFERENT ' + ''.join(map(str, x['window']))}"
                       + (f' ({shift:+d} fr)' if shift else ''))
        print('| ' + ' | '.join(row) + ' |')
    print(f'\nevents {len(ref)}; differing or missing {bad}')


if __name__ == '__main__':
    main()
