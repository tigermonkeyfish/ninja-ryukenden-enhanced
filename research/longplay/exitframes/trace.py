"""exit-frames: instruction trace of one frame with VDC position, from a probe.py state.

    trace.py ROM MODE STATE FIRST TARGET [REC] [--from-line 55] [--to-line 75]

Loads STATE (saved by probe.py --states before frame FIRST), replays FIRST..TARGET-1 with the
recording's inputs, traces frame TARGET and prints the instructions executed while the VDC was on
scanlines [from, to] (vpos), with P's I flag, plus the IRQ1 entry and the BYR write.
"""
import argparse, ctypes, os, sys
from pathlib import Path
import numpy as np
os.environ.setdefault('GXT_LIB', '/workspace/build/exit-frames/lib/libgxe.so')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'drift'))
import lx                                                              # noqa: E402,F401
from pe import W, inputs                                                # noqa: E402
TR = np.dtype([('clk', '<u8'), ('pc', '<u2'), ('bank', 'u1'), ('p', 'u1'), ('vpos', '<i2'), ('hpos', '<i2'),
               ('op', 'u1'), ('pad', 'u1'), ('cyc', '<u4')], align=True)


def trace(t, cap=400000, render=0):
    L = t.lib
    L.gx_trace_vdc.restype = ctypes.c_long
    L.gx_trace_vdc.argtypes = [ctypes.c_void_p, ctypes.c_long, ctypes.c_int]
    rec = np.zeros(cap, dtype=TR)
    n = L.gx_trace_vdc(rec.ctypes.data, cap, render)
    assert n <= cap
    return rec[:n].copy()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rom'); ap.add_argument('mode'); ap.add_argument('state'); ap.add_argument('first', type=int)
    ap.add_argument('target', type=int)
    ap.add_argument('rec', nargs='?', default=str(Path(__file__).resolve().parents[1] / 'full-load.json'))
    ap.add_argument('--from-line', type=int, default=55); ap.add_argument('--to-line', type=int, default=75)
    ap.add_argument('--save', help='write the whole trace (npy)')
    a = ap.parse_args()
    inp = inputs(a.rec)
    t = W(a.rom, None if a.mode == 'unmod-en' else a.mode)
    t.load(Path(a.state).read_bytes())
    for f in range(a.first, a.target):
        t.press(inp[f - 1]); t.lib.gx_run(1, 0)
    t.press(inp[a.target - 1])
    r = trace(t)
    if a.save:
        np.save(a.save, r)
    sel = r[(r['vpos'] >= a.from_line) & (r['vpos'] <= a.to_line)]
    prev = None
    for x in sel:
        key = (x['bank'], x['pc'])
        print('%d v=%3d h=%3d %02X:%04X op=%02X I=%d cyc=%d' % (x['clk'], x['vpos'], x['hpos'], x['bank'], x['pc'],
                                                              x['op'], (x['p'] >> 2) & 1, x['cyc']))


if __name__ == '__main__':
    main()
