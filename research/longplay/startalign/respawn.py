"""start-pos: 2-2 re-entries other than the recording's own (emulator only).

    respawn.py ROM MODE OUTDIR SCENARIO...      MODE: original (build) | unmod-en
    SCENARIO = F:KIND[:HOLD]   F = frame of full-load.json to branch from (state after frame F)
      KIND  death     stage timer set to 001 (units first, $2EDB-$2EDD) -> timer death, respawn
            over      lives $2EAF = 0, then as death -> game over; Run at branch frames 420-421 (CONTINUE)
            select    build only: Select at branch frames 0-1 (menu), Run at 40-41 (Level Select restart)
      HOLD  buttons held from the first gameplay update after the respawn (default none)

Per scenario: N frames (env N, default 700) after F, each frame's picture (packed RGB, uint32) and
meta (frame, camera, $2E4B-$2E4E, $2E63, stage, area, counter, lives, $2240) to OUTDIR/<F>-<KIND>.npz.
Branch inputs are the same on both ROMs; the recording before F is replayed as is.
"""
import os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
import lx                                                              # noqa: E402
from pe import W, inputs, BITS                                          # noqa: E402

REC = str(Path(__file__).resolve().parents[1] / 'full-load.json')


def pack(a):
    return (a[:, :, 0].astype(np.uint32) << 16) | (a[:, :, 1].astype(np.uint32) << 8) | a[:, :, 2]


def main():
    rom, mode, out = sys.argv[1:4]
    scen = [s.split(':') for s in sys.argv[4:]]
    n = int(os.environ.get('N', '700'))
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    inp = inputs(REC)
    t = W(rom, None if mode == 'unmod-en' else mode)
    lx.boot(t, mode)
    f = 0
    for sc in sorted(scen, key=lambda s: int(s[0])):
        F, kind = int(sc[0]), sc[1]
        hold = sum(BITS[b] for b in sc[2].split('+')) if len(sc) > 2 and sc[2] else 0
        while f < F:
            t.press(inp[f]); t.lib.gx_run(1, 0); f += 1
        st = t.save()
        if kind in ('death', 'over'):
            t.ram[0xEDB], t.ram[0xEDC], t.ram[0xEDD] = 1, 0, 0
        if kind == 'over':
            t.ram[0xEAF] = 0
        imgs, meta, upd = [], [], False
        for i in range(n):
            r = bytes(t.ram)
            b = 0
            if kind == 'over' and i in (420, 421):      # the GAME OVER screen: Run on CONTINUE
                b = BITS['run']
            if kind == 'select' and i in (0, 1):        # build only: open the menu (STAGE shows this stage)
                b = BITS['select']
            if kind == 'select' and i in (40, 41):      # Run: restart the shown stage
                b = BITS['run']
            if hold and upd:
                b |= hold
            t.press(b); t.lib.gx_run(1, 1)
            r = bytes(t.ram)
            imgs.append(pack(lx.frame_rgb(t)))
            meta.append([F + 1 + i, r[0x20F] | r[0x210] << 8, r[0xE4B], r[0xE4C], r[0xE4D], r[0xE4E], r[0xE63],
                         r[0xE5F], r[0xE60], r[0], r[0xEAF], r[0x240]])
            # held buttons start once the respawned round's entry countdown has ended
            if i > 60 and r[0xE63] == 0 and r[0x240] == 0 and meta[-2][6] != 0:
                upd = True
        np.savez_compressed(out / f'{F}-{kind}{("-" + sc[2]) if len(sc) > 2 else ""}.npz', meta=np.array(meta, np.int32), imgs=np.array(imgs))
        print(F, kind, 'at F: cam', meta[0][1], 'stage', meta[0][7], 'area', meta[0][8], flush=True)
        t.load(st)
    print('done')


if __name__ == '__main__':
    main()
