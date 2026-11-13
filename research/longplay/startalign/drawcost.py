"""start-pos: cost of the 2-2 area-change draw frame (emulator only, tracer core).

    drawcost.py ROM MODE FRAME...       MODE: original, sms, ... | unmod-en

Replays full-load.json; traces each FRAME: lines after the frame start (master clocks / 1365) at
which the main loop enters its vblank wait (WAITR $37C0, or the native $FD67 in the unmodified ROM)
for the last time, the cycles spent in palette_now ($FEBE .. its return), and the instruction cycles
executed outside the wait loop.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402

rom, mode, frames = sys.argv[1], sys.argv[2], sorted(int(x) for x in sys.argv[3:])
inp = inputs(str(Path(__file__).resolve().parents[1] / 'full-load.json'))
t = W(rom, None if mode == 'unmod-en' else mode)
lx.boot(t, mode)
f = 1
for F in frames:
    while f < F:
        t.press(inp[f - 1]); t.lib.gx_run(1, 0); f += 1
    t.press(inp[f - 1])
    c0 = t.clock()
    tr = t.trace_frame(); f += 1
    pcs = tr['pc'].astype(int)
    wait = [i for i in range(len(tr)) if pcs[i] in (0x37C0, 0xFD67)]
    busy = sum(int(x['cyc']) for x, p in zip(tr, pcs) if not (0x37C0 <= p <= 0x37DD or 0xFD67 <= p <= 0xFD6F))
    pn = [i for i in range(len(tr)) if pcs[i] == 0xFEBE]
    pn_cyc = 0
    for i in pn:      # to the matching return: the next instruction back at the caller's page after an rts
        j = i
        depth = 0
        while j < len(tr):
            op = None
            j += 1
            if pcs[j - 1] == 0xFEC0 + 0 and False:
                break
            if tr[j - 1]['bank'] == 0x56 and pcs[j - 1] >= 0x4000:
                break
        pn_cyc += sum(int(x['cyc']) for x in tr[i:j - 1])
    last_wait = round((int(tr[wait[-1]]['clk']) - c0) / 1365, 2) if wait else None
    print(F, mode, 'last wait entry at line', last_wait, 'busy cycles', busy, 'palette_now calls', len(pn),
          'their cycles', pn_cyc, flush=True)
