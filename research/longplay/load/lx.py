"""load-exact probes on libgxw.so (research/longplay/drift, Makefile target watch).
Diagnostic, emulator evidence only.

    run(tag, rom, mode, recording, out, frames=None, states=())
        power on (mode's settings in backup RAM; mode 'none' = no backup RAM, 'unmod-en' = no
        backup RAM and the native title language switch to English), leave the title as
        longplay_lib does, stop at 1-1's first update, then replay the recording as one input
        list; records per frame counter / master / stage / area and hits of KEYS, saves states
        at the frames in `states` (before that frame's step).
"""
import ctypes, os, sys, time
from pathlib import Path
import numpy as np
os.environ.setdefault('GXT_LIB', '/workspace/build/load-exact/lib/libgxl.so')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'drift'))
from pe import W, inputs, BITS                                          # noqa: E402
KEYS = [(0, 0xE06C), (0, 0xE061), (0, 0xFCEC), (1, 0x82CD), (1, 0x85B4), (1, 0x80AB), (1, 0x82D0)]
NAMES = ['upd', 'wait', 'vbl', 'load', 'area', 'init', 'load_ret']


def vram(t):
    L = t.lib
    L.gx_vram.restype = ctypes.POINTER(ctypes.c_uint16)
    return np.ctypeslib.as_array(L.gx_vram(), shape=(0x8000,)).copy()


def vce(t):
    L = t.lib
    L.gx_vce.restype = ctypes.POINTER(ctypes.c_uint16)
    return np.ctypeslib.as_array(L.gx_vce(), shape=(512,)).copy()


def frame_rgb(t):
    """The last rendered frame (after t.lib.gx_run(1, 1)) as an HxWx3 uint8 array."""
    L = t.lib
    w, h = ctypes.c_int(0), ctypes.c_int(0)
    L.gx_fb_size(ctypes.byref(w), ctypes.byref(h))
    L.gx_fb.restype = ctypes.POINTER(ctypes.c_uint8)
    a = np.ctypeslib.as_array(L.gx_fb(), shape=(512 * 2048 * 4,))
    return a[:w.value * h.value * 4].reshape(h.value, w.value, 4)[:, :, :3].copy()


def boot(t, mode):
    """pe.W.boot's title handling; 'unmod-en' adds the native language switch (hold I + II,
    tap Select at the title, as longplay_six --shortcut)."""
    previous, since, presses, pressed, title = None, 0, [200], False, False
    for frame in range(1, 20000):
        held = BITS['run'] if any(p <= frame - 1 < p + 2 for p in presses) else 0
        if mode == 'unmod-en' and title and master == b'\x01\x01':
            # longplay_six applies the buttons after the step that made `since` 10, 12, 14, 16
            sc = {10: 3, 11: 3, 12: 7, 13: 7, 14: 3, 15: 3}.get(since, 0)
            held |= sc
        t.press(held)
        t.step(1)
        since += 1
        master = t.r(0x2240, 2)
        if master != previous:
            previous, since = master, 0
        if master == b'\x01\x01':
            title = True
        if master == b'\x01\x01' and since == 180 and not pressed:
            presses.append(frame); pressed = True
        if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150 and not title:
            presses.append(frame)
        if title and master[0] == 0 and frame > presses[-1] + 2:
            t.press(0)
            if t.until(1, 0x8457) < 0:
                raise RuntimeError('first update not reached')
            st = t.save(); t.load(st)
            return frame, st
    raise RuntimeError('gameplay not reached')


def power(rom, mode):
    t = W(rom, None if mode in ('none', 'unmod-en') else mode)
    master = None  # noqa
    return t


def run(tag, rom, mode, recording, out, frames=None, states=(), start=None, first=1):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    inp = inputs(recording) if isinstance(recording, str) else recording
    n = frames or len(inp)
    t = W(rom, None if mode in ('none', 'unmod-en') else mode)
    if start is None:
        bf, st = boot(t, mode)
        lang = t.r(0x3227)[0]
    else:
        t.load(Path(start).read_bytes()); bf, lang = None, t.r(0x3227)[0]
    keys = [(b << 16) | p for b, p in KEYS]
    arr = {k: np.zeros(n + 1, np.uint8) for k in ('cnt', 'mas', 'm2', 'stg', 'are')}
    hits = []
    t.frame = first
    states = set(states)
    sdir = Path('/workspace/build/load-exact/states') / tag
    t0 = time.time()
    for f in range(first, n + 1):
        if f in states:
            sdir.mkdir(parents=True, exist_ok=True)
            (sdir / f'{f}.state').write_bytes(t.save())
        _, h = t.run_w(1, inp[f - 1:f], keys)
        if len(h):
            hits.append(h)
        r = bytes(t.ram)
        arr['cnt'][f] = r[0]; arr['mas'][f] = r[0x240]; arr['m2'][f] = r[0x241]
        arr['stg'][f] = r[0xe5f]; arr['are'][f] = r[0xe60]
        if f % 20000 == 0:
            print(tag, f, round(time.time() - t0), flush=True)
    hits = np.concatenate(hits)
    np.savez_compressed(out / f'{tag}.npz', **arr, hits=hits, names=np.array(NAMES), boot_frames=bf or 0,
                        language=lang)
    print(tag, 'done', n, round(time.time() - t0), 's; language', lang, flush=True)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('tag'); ap.add_argument('rom'); ap.add_argument('mode'); ap.add_argument('recording')
    ap.add_argument('--out', default='/workspace/build/load-exact/runs')
    ap.add_argument('--frames', type=int)
    ap.add_argument('--states', type=int, nargs='*', default=[])
    a = ap.parse_args()
    run(a.tag, a.rom, a.mode, a.recording, a.out, a.frames, a.states)
