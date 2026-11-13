"""Before/after picture of a load's first visible frames (load-exact; diagnostic, emulator only).

    pic.py TAG REC FIRST LAST A_ROM A_STATE A_FRAME B_ROM B_STATE B_FRAME [--mode M] [--png DIR] [--rec-b REC]

Renders FIRST..LAST in both builds from their states (saved before *_FRAME's step; the state carries
the mode). The first visible frame = the first frame from which every frame for 5 frames has a
non-black pixel. Prints both first visible frames, whether the frames from there on are equal pixel
for pixel (A frame v_a + k against B frame v_b + k, k over the rest of the range), VRAM and VCE
equality at the first visible frames, and the frames with non-black pixels before them (flashes).
"""
import hashlib, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402


def render(rom, state, sf, inp, first, last):
    t = W(rom, None)
    t.load(Path(state).read_bytes())
    f = sf
    while f < first:
        t.press(inp[f - 1]); t.step(1); f += 1
    out = []
    for fr in range(first, last + 1):
        t.press(inp[fr - 1])
        t.lib.gx_run(1, 1)
        img = lx.frame_rgb(t)
        out.append(dict(frame=fr, img=img, nb=int((img.max(axis=2) > 0).sum()), vram=lx.vram(t), vce=lx.vce(t)))
    return out


def first_visible(fr):
    for i in range(len(fr) - 5):
        if all(fr[i + k]['nb'] for k in range(5)):
            return i
    return None


def main():
    a = sys.argv
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    tag, rec, first, last = a[1], a[2], int(a[3]), int(a[4])
    A = render(a[5], a[6], int(a[7]), inputs(rec), first, last)
    B = render(a[8], a[9], int(a[10]), inputs(opt('--rec-b', rec)), first, last)
    va, vb = first_visible(A), first_visible(B)
    print(tag, 'first visible A', A[va]['frame'] if va is not None else None, 'B', B[vb]['frame'] if vb is not None else None)
    for name, X, v in (('A', A, va), ('B', B, vb)):
        flash = [x['frame'] for x in X[:v] if x['nb']]
        print(f'  {name} non-black frames before it: {flash}')
    if va is None or vb is None:
        return
    n = min(len(A) - va, len(B) - vb)
    eq = [np.array_equal(A[va + k]['img'], B[vb + k]['img']) for k in range(n)]
    print(f'  frames equal from the first visible on: {sum(eq)} of {n}; first unequal k: {eq.index(False) if False in eq else None}')
    print('  VRAM equal at first visible', np.array_equal(A[va]['vram'], B[vb]['vram']),
          'VCE equal', np.array_equal(A[va]['vce'], B[vb]['vce']))
    if not np.array_equal(A[va]['vram'], B[vb]['vram']):
        d = np.nonzero(A[va]['vram'] != B[vb]['vram'])[0]
        print('   VRAM words differing', len(d), 'first', [hex(x) for x in d[:8]])
    png = opt('--png')
    if png:
        from PIL import Image
        Path(png).mkdir(parents=True, exist_ok=True)
        for name, X, v in (('before', A, va), ('after', B, vb)):
            for k in (0, 1, 2, 8, 30):
                if v + k < len(X):
                    Image.fromarray(X[v + k]['img']).save(Path(png) / f'{tag}-{name}-v{k}-f{X[v + k]["frame"]}.png')


if __name__ == '__main__':
    main()
