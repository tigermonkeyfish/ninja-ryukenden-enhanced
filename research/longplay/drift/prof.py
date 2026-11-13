"""Instruction-level profile of frames in the tracer core.
trace(tag_rom, state_path, start_frame, first, last): replay from the state (saved after
start_frame) with the recording's input to frame `first`-1, then trace frames first..last.
Returns a structured array of every instruction with frame numbers."""
import numpy as np
from tracer import T, inputs, REC
import os
INP = inputs(os.environ.get("REC")) if os.environ.get("REC") else inputs()


def trace(rom, state, start_frame, first, last, t=None):
    t = t or T(rom)
    t.load(state)
    f = start_frame
    while f < first - 1:
        t.press(INP[f]); t.step(1); f += 1
    out = []
    for fr in range(first, last + 1):
        t.press(INP[fr - 1])
        r = t.trace_frame()
        rr = np.zeros(len(r), dtype=REC.descr + [('frame', '<u4')])
        for n in REC.names:
            rr[n] = r[n]
        rr['frame'] = fr
        out.append(rr)
    end = t.clock()
    return np.concatenate(out), end, t


def costs(tr, end):
    clk = tr['clk'].astype(np.int64)
    return np.diff(np.append(clk, end))


def irq_mask(tr):
    """True for instructions executed inside an interrupt handler (IRQ1 $FCD7, timer $FCD3)."""
    pc = tr['pc']; bank = tr['bank']
    m = np.zeros(len(tr), bool)
    depth = 0
    ent = np.nonzero((bank == 0) & ((pc == 0xFCD7) | (pc == 0xFCD3)))[0]
    rti = np.nonzero((bank == 0) & ((pc == 0xFD60) | (pc == 0xFCD6)))[0]
    if len(rti) and (not len(ent) or rti[0] < ent[0]):
        depth = 1   # the trace starts inside a handler
    for i in range(len(tr)):
        p = pc[i]
        if bank[i] == 0 and p in (0xFCD7, 0xFCD3):
            depth += 1
        m[i] = depth > 0
        if bank[i] == 0 and p in (0xFD60, 0xFCD6) and depth > 0:
            depth -= 1
    return m
