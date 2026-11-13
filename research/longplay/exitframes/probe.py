"""exit-frames: VDC scroll writes, per-line scroll, pictures and RAM writes around area changes.
Diagnostic, emulator evidence only (in-process Geargrafx 78fc3d7, libgxe.so from this folder's Makefile).

    probe.py ROM MODE OUTDIR [REC] [--pre 40] [--post 6] [--events 14030 ...] [--area] [--states]
    MODE: original (build, options 0) | parallax-off (build, options bit 0) | unmod-en (unmodified ROM)

One fresh power-on, one pass over the recording (as startalign/capture.py: lx.boot, then one input per
frame). For each event EV, frames EV-pre .. EV+post run through gx_run_vdc with rendering and write
OUTDIR/ev-<EV>.npz: img<frame>, meta (frame, cam, $2E4B-4E, $2E63, stage, area, counter, $2258),
vw (VDC BXR/BYR writes: frame, pc, bank, reg, val, old, vpos, hpos, raster, op, kind, clk),
lr (per line: frame, vpos, latched BXR, BG Y offset, raster), hits (KEYS), ram (writes to $2E4B-$2E4E).
--states also saves the core state before frame EV-pre (OUTDIR/ev-<EV>.state).
"""
import argparse, ctypes, os, sys, time
from pathlib import Path
import numpy as np
os.environ.setdefault('GXT_LIB', '/workspace/build/exit-frames/lib/libgxe.so')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
import lx                                                              # noqa: E402
import pe                                                               # noqa: E402
from pe import W, inputs, WREC                                          # noqa: E402
pe.MODE_BITS.setdefault('parallax-off', 0x01)   # options bit 0: smooth parallax OFF (the native backdrop)
from tracer import HIT                                                  # noqa: E402

AREA = [11343, 12421, 12546, 14030, 14671, 55309, 55429, 60708, 61795, 63544, 74531, 75459, 76157, 77972, 78669,
        79287, 80296, 80630, 80887, 90754, 91716, 91820, 92931, 94460, 94579, 96625]   # the 26 surveyed area changes
EVENTS = [14030, 14671, 55309, 75459, 77972, 78669, 79287, 80296, 80630, 80887, 94460, 96625]
KEYS = [(0, 0xFCD7), (0, 0xFD26), (0, 0xFD3B), (0, 0xFD13), (1, 0x83F3), (1, 0x8457), (1, 0x85B4), (1, 0x80AB),
        (0, 0xFF42), (0, 0xFF2C), (0, 0xFCEC), (0, 0xE06C), (0, 0xE061)]
KNAMES = ['irq1', 'split', 'byr', 'vblpal', 'mainhook', 'gameloop', 'area', 'init80ab', 'ff42', 'ff2c', 'vbl',
          'upd', 'wait']
VW = np.dtype([('frame', '<u4'), ('pc', '<u2'), ('bank', 'u1'), ('reg', 'u1'), ('val', '<u2'), ('old', '<u2'),
               ('vpos', '<i2'), ('hpos', '<i2'), ('raster', '<i2'), ('op', 'u1'), ('kind', 'u1'), ('clk', '<u8')],
              align=True)
LR = np.dtype([('frame', '<u4'), ('vpos', '<i2'), ('bxr', '<u2'), ('by', '<i4'), ('raster', '<i4')], align=True)


def setup(t):
    L = t.lib
    L.gx_run_vdc.restype = ctypes.c_long
    L.gx_run_vdc.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long, ctypes.c_uint32,
                             ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long,
                             ctypes.c_void_p, ctypes.c_int]


def run_vdc(t, frame, button, keys, render=1):
    """One frame; returns (ram writes, hits, vdc writes, lines)."""
    rec = np.zeros(1 << 14, dtype=WREC); h = np.zeros(1 << 12, dtype=HIT)
    vw = np.zeros(1 << 14, dtype=VW); lr = np.zeros(1024, dtype=LR)
    nh, nv, nl = ctypes.c_long(0), ctypes.c_long(0), ctypes.c_long(0)
    b = np.array([button], dtype=np.uint8)
    k = np.array(keys, dtype=np.uint32)
    n = t.lib.gx_run_vdc(1, b.ctypes.data, rec.ctypes.data, len(rec), frame, k.ctypes.data, len(k), h.ctypes.data,
                         len(h), ctypes.byref(nh), vw.ctypes.data, len(vw), ctypes.byref(nv), lr.ctypes.data,
                         len(lr), ctypes.byref(nl), render)
    assert n <= len(rec) and nh.value <= len(h) and nv.value <= len(vw) and nl.value <= len(lr)
    return rec[:n].copy(), h[:nh.value].copy(), vw[:nv.value].copy(), lr[:nl.value].copy()


def meta(t, f):
    r = bytes(t.ram)
    return [f, r[0x20F] | r[0x210] << 8, r[0xE4B], r[0xE4C], r[0xE4D], r[0xE4E], r[0xE63], r[0xE5F], r[0xE60], r[0],
            r[0x258]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rom'); ap.add_argument('mode'); ap.add_argument('out')
    ap.add_argument('rec', nargs='?', default=str(Path(__file__).resolve().parents[1] / 'full-load.json'))
    ap.add_argument('--pre', type=int, default=40); ap.add_argument('--post', type=int, default=6)
    ap.add_argument('--events', type=int, nargs='*', default=EVENTS)
    ap.add_argument('--area', action='store_true', help='all 26 area changes instead of the 12 exit-frame events')
    ap.add_argument('--states', action='store_true')
    a = ap.parse_args()
    if a.area:
        a.events = AREA
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    inp = inputs(a.rec)
    t = W(a.rom, None if a.mode == 'unmod-en' else a.mode)
    setup(t)
    t.watch_range(0xE4B, 0xE4F)
    bf, st = lx.boot(t, a.mode)
    print('boot frames', bf, 'language', t.r(0x3227)[0], flush=True)
    keys = [(b << 16) | p for b, p in KEYS]
    wins = {e: (e - a.pre, e + a.post) for e in a.events}
    last = max(w[1] for w in wins.values())
    acc = {e: dict(img={}, meta=[], vw=[], lr=[], hits=[], ram=[]) for e in a.events}
    t0 = time.time()
    for f in range(1, last + 1):
        act = [e for e, (lo, hi) in wins.items() if lo <= f <= hi]
        if a.states:
            for e in [e for e, (lo, hi) in wins.items() if lo == f]:
                (out / f'ev-{e}.state').write_bytes(t.save())
        if act:
            ram, h, vw, lr = run_vdc(t, f, inp[f - 1], keys)
            img = lx.frame_rgb(t); m = meta(t, f)
            for e in act:
                d = acc[e]; d['img'][f] = img; d['meta'].append(m)
                d['vw'].append(vw); d['lr'].append(lr); d['hits'].append(h); d['ram'].append(ram)
        else:
            t.press(inp[f - 1]); t.lib.gx_run(1, 0)
        for e in [e for e, (lo, hi) in wins.items() if hi == f]:
            d = acc.pop(e)
            np.savez_compressed(out / f'ev-{e}.npz', meta=np.array(d['meta'], np.int32), vw=np.concatenate(d['vw']),
                                lr=np.concatenate(d['lr']), hits=np.concatenate(d['hits']),
                                ram=np.concatenate(d['ram']), knames=np.array(KNAMES),
                                **{f'img{k}': v for k, v in d['img'].items()})
        if f % 20000 == 0:
            print(f, round(time.time() - t0), flush=True)
    print('done', round(time.time() - t0), 's')


if __name__ == '__main__':
    main()
