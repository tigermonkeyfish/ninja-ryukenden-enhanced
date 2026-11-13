"""exit-frames: the per-area-change table of docs/validation/exit-frames.md.

    table.py UNMOD ON OFF V110 PT3 [PT2]     (probe.py --area output directories)

Per area change: the transition-start frame (first $2E63 = $0A), the split's BYR write (scanline.dot;
late = after scanline 64), the line at which the native palette save (TII $F718) starts, and the
picture verdict of that frame against the unmodified ROM (ON / OFF: same frame number; 1.10 / pt3 /
pt2: their own transition-start frame, compared by split position only).
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from startframe import rows                                            # noqa: E402
from analyze import lines                                              # noqa: E402

STAGE = {11343: '2-1 a1', 12421: '2-1 a2', 12546: '2-1 a3', 14030: '2-2 a1', 14671: '2-2 a2', 55309: '4-1 a1',
         55429: '4-1 a2', 60708: '4-3 a1', 61795: '4-3 a2', 63544: '4-3 a3', 74531: '5-2 a1', 75459: '5-2 a2',
         76157: '5-2 a3', 77972: '5-3 a1', 78669: '5-3 a2', 79287: '5-3 a3', 80296: '5-3 a4', 80630: '5-3 a5',
         80887: '5-3 a6', 90754: '6-2 a1', 91716: '6-2 a2', 91820: '6-2 a3', 92931: '6-2 a4', 94460: '6-3 a1',
         94579: '6-3 a2', 96625: '6-3 a3'}


def pix(da, db, ev, f):
    """Differing pixels of frame f, with ' S' when any visible line's latched BXR / BG Y differs."""
    a, b = np.load(Path(da) / f'ev-{ev}.npz'), np.load(Path(db) / f'ev-{ev}.npz')
    n = int((a[f'img{f}'] != b[f'img{f}']).any(2).sum())
    la, lb = lines(a, f), lines(b, f)
    return '%d%s' % (n, ' S' if any(la[v] != lb.get(v) for v in la) else '')


def cell(r, ref=None):
    if r is None:
        return '-'
    v, h = r['byr'][0]
    s = '%d.%03d' % (v, h) + (' **late**' if r['late'] else '')
    if r.get('tii_line') is not None:
        s += ' (TII %.1f)' % r['tii_line']
    return s


def main():
    dirs = sys.argv[1:]
    R = [rows(d) for d in dirs]
    hdr = ['UNMOD', 'ON (new)', 'OFF (new)', '1.10', 'pt3', 'pt2'][:len(dirs)]
    print('| Event | Area | Start frame | ' + ' | '.join(hdr) + ' | px vs UNMOD, ON / OFF (S = scroll differs) |')
    print('|' + ' --- |' * (4 + len(dirs)))
    for ev in sorted(R[0]):
        u = R[0][ev]
        f = u['frame']
        pon = pix(dirs[0], dirs[1], ev, f); poff = pix(dirs[0], dirs[2], ev, f)
        print('| %d | %s | %d | %s | %s / %s |' % (ev, STAGE[ev], f, ' | '.join(cell(r.get(ev)) for r in R), pon, poff))


if __name__ == '__main__':
    main()
