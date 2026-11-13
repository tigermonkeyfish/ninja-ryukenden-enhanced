"""Instruction trace of one stage load (load-exact; diagnostic, emulator only).

    ltrace.py ROM STATE STATE_FRAME RECORDING FIRST LAST

Replays from STATE (saved before STATE_FRAME's step) to FIRST, traces FIRST..LAST and splits the
load update (the one that reaches bank 1 $82CD) into: native work before $82CD, the call at
$82CD (native $80AB, or the patch's $FF35 = native $80AB + Enhanced draw), the rest to the wait;
clocks by bank inside the call, interrupt clocks excluded and listed apart, and the vblanks.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'drift'))
from tracer import REC                                                  # noqa: E402
from prof import irq_mask, costs                                        # noqa: E402


def trace(rom, state, sf, rec, first, last):
    t = W(rom, None)
    t.load(Path(state).read_bytes())
    inp = inputs(rec)
    f = sf
    while f < first:
        t.press(inp[f - 1]); t.step(1); f += 1
    out = []
    for fr in range(first, last + 1):
        t.press(inp[fr - 1])
        r = t.trace_frame()
        rr = np.zeros(len(r), dtype=REC.descr + [('frame', '<u4')])
        for n in REC.names:
            rr[n] = r[n]
        rr['frame'] = fr
        out.append(rr)
    return np.concatenate(out), t.clock(), t


def split(A, end):
    c = costs(A, end)
    irq = irq_mask(A)
    pc, bank = A['pc'], A['bank']
    i_call = np.nonzero((bank == 1) & (pc == 0x82CD))[0][0]
    i_ret = np.nonzero((bank == 1) & (pc == 0x82D0))[0][0]
    starts = np.nonzero((bank == 0) & (pc == 0xE06C))[0]
    i_upd = starts[starts < i_call][-1]
    waits = np.nonzero((bank == 0) & (pc == 0xE061))[0]
    i_wait = waits[waits > i_ret][0]
    vbl = np.nonzero((bank == 0) & (pc == 0xFCEC))[0]
    v_in = vbl[(vbl > i_upd) & (vbl < i_wait)]
    v_next = vbl[vbl > i_wait][0]
    clk = A['clk'].astype(np.int64)
    res = dict(pre=int(c[i_upd:i_call][~irq[i_upd:i_call]].sum()), call=int(c[i_call:i_ret][~irq[i_call:i_ret]].sum()),
               post=int(c[i_ret:i_wait][~irq[i_ret:i_wait]].sum()), irq=int(c[i_upd:i_wait][irq[i_upd:i_wait]].sum()),
               total=int(clk[i_wait] - clk[i_upd]), vblanks=len(v_in), left=int(clk[v_next] - clk[i_wait]),
               upd_frame=int(A['frame'][i_upd]))
    m = np.zeros(len(A), bool); m[i_call:i_ret] = True; m &= ~irq
    key = np.where(bank >= 0x40, bank.astype(int) * 256, bank.astype(int) * 256 + (pc >> 8))
    ks, inv = np.unique(key[m], return_inverse=True)
    sums = np.bincount(inv, weights=c[m])
    res['by_bank'] = {(f'bank {k >> 8:02X}' if k >> 8 >= 0x40 else f'{k >> 8:02X}:{k & 255:02X}xx'): int(v)
                      for k, v in zip(ks, sums)}
    # the native init inside the call: from $80AB to its return
    i80 = np.nonzero((bank == 1) & (pc == 0x80AB))[0]
    i80 = i80[(i80 >= i_call) & (i80 < i_ret)]
    return res, (i_upd, i_call, i_ret, i_wait), c, irq


if __name__ == '__main__':
    rom, state, sf, rec, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
    A, end, t = trace(rom, state, sf, rec, first, last)
    res, idx, c, irq = split(A, end)
    bb = res.pop('by_bank')
    print(res)
    for k, v in sorted(bb.items(), key=lambda kv: -kv[1]):
        if v > 2000:
            print(f'  {k:12s} {v:9d}')
