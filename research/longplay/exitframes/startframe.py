"""exit-frames: the transition-start frame of every area change, per probe.py output directory.

    startframe.py DIR [DIR ...]

For each event file: the first frame in the window whose $2E63 is $0A (the update that ran $8490/$849B,
the area change's first update), its split BYR write (scanline, dot), whether it is late (scanline > 64),
the scanline of the native palette save (TII at $F718: from the hit's clock, relative to the vblank
handler's entry that ended the previous frame, 1365 master clocks a line, the vblank IRQ at line 257),
Ryu's position $2E81/$2E82 and the camera (to check the game state against another ROM).
"""
import sys
from pathlib import Path
import numpy as np


def rows(dirn):
    out = {}
    for f in sorted(Path(dirn).glob('ev-*.npz'), key=lambda p: int(p.stem[3:])):
        d = np.load(f); m = d['meta']; h = d['hits']; names = list(d['knames']); vw = d['vw']
        k = np.nonzero(m[:, 6] == 10)[0]
        if not len(k):
            out[int(f.stem[3:])] = None; continue
        fr = int(m[k[0], 0])
        w = vw[(vw['frame'] == fr) & (vw['pc'] == 0xFD3B)]
        byr = [(int(x['vpos']), int(x['hpos'])) for x in w]
        vb = h[(h['which'] == names.index('vbl')) & (h['frame'] == fr - 1)]
        tii = h[(h['which'] == names.index('tii')) & (h['frame'] == fr)] if 'tii' in names else []
        tl = None
        if len(vb) and len(tii):
            tl = round(257 + (int(tii['clk'][0]) - int(vb['clk'][-1])) / 1365 - 263, 2)
        ryu = (int(m[k[0], 11]), int(m[k[0], 12])) if m.shape[1] > 12 else None
        out[int(f.stem[3:])] = dict(frame=fr, byr=byr, late=any(v > 64 for v, _ in byr), tii_line=tl, ryu=ryu,
                                    cam=int(m[k[0], 1]))
    return out


def main():
    res = [rows(d) for d in sys.argv[1:]]
    for ev in sorted(res[0]):
        print(ev, ' | '.join(str(r.get(ev)) for r in res))


if __name__ == '__main__':
    main()
