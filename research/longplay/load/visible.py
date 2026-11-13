"""Per-frame visibility around a frame range (load-exact; diagnostic, emulator only).

    visible.py ROM STATE STATE_FRAME RECORDING FIRST LAST [--png DIR]

Replays from STATE to FIRST, then renders FIRST..LAST: per frame the number of non-black pixels
of the frame buffer, the number of non-zero VCE colours, the update counter; --png writes each
frame (needs PIL) for frames with any non-black pixel, plus an md5 of each frame.
"""
import hashlib, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402


def frames(rom, state, sf, rec, first, last, png=None, tag=''):
    t = W(rom, None)
    t.load(Path(state).read_bytes())
    inp = inputs(rec)
    f = sf
    while f < first:
        t.press(inp[f - 1]); t.step(1); f += 1
    out = []
    for fr in range(first, last + 1):
        t.press(inp[fr - 1])
        t.lib.gx_run(1, 1)
        img = lx.frame_rgb(t)
        nb = int((img.max(axis=2) > 0).sum())
        col = lx.vce(t)
        md5 = hashlib.md5(img.tobytes()).hexdigest()[:10]
        out.append((fr, nb, int((col != 0).sum()), t.r(0x2000)[0], md5, img))
        if png and nb:
            from PIL import Image
            Path(png).mkdir(parents=True, exist_ok=True)
            Image.fromarray(img).save(Path(png) / f'{tag}{fr}.png')
    return out


if __name__ == '__main__':
    a = sys.argv
    png = a[a.index('--png') + 1] if '--png' in a else None
    for fr, nb, nc, cnt, md5, _ in frames(a[1], a[2], int(a[3]), a[4], int(a[5]), int(a[6]), png):
        print(fr, 'nonblack px', nb, 'vce nonzero', nc, 'cnt', cnt, md5)
