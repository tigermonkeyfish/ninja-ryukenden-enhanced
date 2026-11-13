"""start-pos: the playfield split's BYR write per frame around an event (emulator only, tracer core).

    splittrace.py ROM MODE FIRST LAST       MODE: original (build) | unmod-en

Replays full-load.json to FIRST-1, then traces frames FIRST..LAST: per frame the lines after vblank
(master clocks from the frame's start / 1365) of the IRQ1 entry ($FCD7) and the BYR write ($FD3B),
the instruction that was running when the IRQ was taken, and the line spans of Enhanced banks
($40-$7F) and of palette_now ($FEBE) calls.
"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402

rom, mode, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
inp = inputs(str(Path(__file__).resolve().parents[1] / 'full-load.json'))
t = W(rom, None if mode == 'unmod-en' else mode)
lx.boot(t, mode)
for f in range(1, first):
    t.press(inp[f - 1]); t.lib.gx_run(1, 0)
for f in range(first, last + 1):
    t.press(inp[f - 1])
    c0 = t.clock()
    tr = t.trace_frame()
    L = lambda c: round((int(c) - c0) / 1365, 2)
    irq = [i for i in range(len(tr)) if tr[i]['pc'] == 0xFCD7]
    byr = [i for i in range(len(tr)) if tr[i]['pc'] == 0xFD3B]
    out = []
    for i in irq:
        p = tr[i - 1]
        out.append(f"IRQ1 at line {L(tr[i]['clk'])} (after pc ${int(p['pc']):04X} bank ${int(p['bank']):02X}, {int(p['cyc'])} cyc)")
    for i in byr:
        out.append(f"BYR write at line {L(tr[i]['clk'])}")
    enh = [i for i in range(len(tr)) if tr[i]['bank'] >= 0x40 and tr[i]['pc'] >= 0x4000 and tr[i]['pc'] < 0xA000]
    if enh:
        out.append(f"Enhanced banks lines {L(tr[enh[0]]['clk'])}-{L(tr[enh[-1]]['clk'])} ({len(enh)} instr)")
    pn = [i for i in range(len(tr)) if tr[i]['pc'] == 0xFEBE]
    for i in pn:
        out.append(f"palette_now at line {L(tr[i]['clk'])}")
    long_ = sorted(((int(x['cyc']), int(x['pc']), int(x['bank']), L(x['clk'])) for x in tr), reverse=True)[:3]
    out.append('longest instr (cyc, pc, bank, line): ' + ', '.join(f'({a}, ${b:04X}, ${c:02X}, {d})' for a, b, c, d in long_))
    r = bytes(t.ram)
    print(f, 'cam', r[0x20F] | r[0x210] << 8, 'e63', r[0xE63], 'area', r[0xE60], '|', '; '.join(out), flush=True)
