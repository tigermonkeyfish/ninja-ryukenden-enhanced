"""start-align: picture + scroll registers around every stage load / area change (emulator only).

    capture.py ROM MODE OUTDIR [REC]       MODE: original (build, backup-RAM palette) | unmod-en

Runs the whole recording once (in-process Geargrafx, libgxl.so of research/longplay/load) and renders
frames EV-4 .. EV+110 for each of the 47 events (EV = the frame of load-exact's survey).
Writes OUTDIR/ev-<frame>.npz: frames, img<frame> (HxWx3), meta (frame, cam, bxr, byr?, $2E4B-4E, $2E63, stage, area, cnt).
"""
import sys, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402

EVENTS = [1, 2846, 10151, 11343, 12421, 12546, 13256, 14030, 14671, 16547, 27793, 31416, 34867, 53302, 55309,
          55429, 57134, 60369, 60708, 61795, 63544, 64436, 70025, 73278, 74531, 75459, 76157, 77219, 77972,
          78669, 79287, 80296, 80630, 80887, 82897, 86521, 88458, 90754, 91716, 91820, 92931, 93822, 94460,
          94579, 96625, 102317, 106481, 111242]
PRE, POST = 4, 110


def main():
    rom, mode, out = sys.argv[1:4]
    rec = sys.argv[4] if len(sys.argv) > 4 else '/workspace/.claude/worktrees/start-align/research/longplay/full-load.json'
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    inp = inputs(rec)
    t = W(rom, None if mode == 'unmod-en' else mode)
    bf, st = lx.boot(t, mode)
    print('boot frames', bf, 'language', t.r(0x3227)[0], flush=True)
    import os
    only = [int(x) for x in os.environ.get('ONLY', '').split()] or EVENTS
    wins = {e: (e - PRE, e + POST) for e in only}
    last = max(w[1] for w in wins.values())
    data = {e: {} for e in only}
    meta = {e: [] for e in only}
    t0 = time.time()
    for f in range(1, last + 1):
        act = [e for e, (a, b) in wins.items() if a <= f <= b]
        t.press(inp[f - 1])
        t.lib.gx_run(1, 1 if act else 0)
        if act:
            img = lx.frame_rgb(t)
            r = bytes(t.ram)
            m = [f, r[0x20F] | r[0x210] << 8, r[0xE4B], r[0xE4C], r[0xE4D], r[0xE4E], r[0xE63], r[0xE5F], r[0xE60], r[0]]
            for e in act:
                data[e][f] = img
                meta[e].append(m)
        for e in [e for e, (a, b) in wins.items() if b == f]:
            np.savez_compressed(out / f'ev-{e}.npz', meta=np.array(meta[e], np.int32),
                                **{f'img{k}': v for k, v in data[e].items()})
            del data[e]
        if f % 20000 == 0:
            print(f, round(time.time() - t0), flush=True)
    print('done', round(time.time() - t0), 's')


if __name__ == "__main__":
    main()
