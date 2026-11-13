"""Whole-recording replay in the in-process watch core (palette-exact; diagnostic, emulator only).

Power-on with MODE's settings in backup RAM ('none': no backup RAM, for the unmodified ROM and
1.10), the title left as the headless tools do (pe.W.boot), then the recording as one continuous
input list. Per frame: update counter, master flags, stage, area, boss health, CORE and WIDE
fingerprints (scripts/longplay_six.py's, WIDE also without RENT $3740-$37BF); clocks of the
main-loop update ($E06C), its wait call ($E061), the vblank handler's path ($FCEC) and its palette
upload call ($FD13 to $FD16); and every
write (--reads: and read) of the watched RAM range with the accessing PC and bank.

    python3 pe_run.py TAG ROM MODE RECORDING OUTDIR [--frames N] [--watch 0x1740 0x17C0]
"""
import argparse, sys, time, zlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from pe import W, inputs                                                       # noqa: E402
CORE = [(0x000, 0x001), (0x240, 0x242), (0x20f, 0x211), (0x237, 0x238), (0xe5f, 0xe61),
        (0xe9e, 0xeb8), (0xed0, 0xede), (0xf00, 0x1100)]
EXCLUDED = [(0x100, 0x200), (0x260, 0x284), (0x286, 0xa86), (0x1740, 0x17fe), (0x1c00, 0x2000)]
WIDE, _p = [], 0
for _a, _b in EXCLUDED:
    if _a > _p:
        WIDE.append((_p, _a))
    _p = _b
WIDE.append((_p, 0x2000))
KEYS = [(0, 0xE06C), (0, 0xE061), (0, 0xFCEC), (0, 0xFD13), (0, 0xFD16), (0xF8, 0x374F), (0xF8, 0x37AE),
        (0x46, 0x5000)]
# pal..pal_end: the vblank's palette path; rent_body: RENT's M form past its gate (MS/MN upload);
# rent_disp: RENT's M form to the dispatcher; entry: palette_entry (dispatcher or palette_now)
NAMES = ['upd', 'wait', 'vbl', 'pal', 'pal_end', 'rent_body', 'rent_disp', 'entry']


def fp(ram, ranges):
    c = 0
    for a, b in ranges:
        c = zlib.crc32(ram[a:b], c)
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('tag'); ap.add_argument('rom'); ap.add_argument('mode'); ap.add_argument('recording')
    ap.add_argument('out', type=Path)
    ap.add_argument('--frames', type=int)
    ap.add_argument('--watch', nargs=2, default=['0x1740', '0x17c0'])
    ap.add_argument('--reads', action='store_true', help='record reads too (not on a build that runs code there)')
    a = ap.parse_args()
    inp = inputs(a.recording)
    n = a.frames or len(inp)
    t = W(a.rom, None if a.mode == 'none' else a.mode)
    lo, hi = int(a.watch[0], 0), int(a.watch[1], 0)
    t.watch_range(lo, hi, not a.reads)
    keys = [(b << 16) | p for b, p in KEYS]
    acc0, h0 = t.run_w(0)   # nothing; keeps the API exercised
    t0 = time.time()
    boot_acc = []
    # the boot, with the watch on (frame numbers negative: -boot_frames .. -1)
    t.frame = 0
    t.lib.gx_watch_range(lo, hi, 0 if a.reads else 1)
    # W.boot steps with gx_run; repeat it here with run_w to watch it
    from pe import BITS
    previous, since, presses, pressed, title = None, 0, [200], False, False
    boot_frames = None
    for frame in range(1, 20000):
        held = BITS['run'] if any(p <= frame - 1 < p + 2 for p in presses) else 0
        acc, _ = t.run_w(1, np.array([held], np.uint8))
        if len(acc):
            acc['frame'] = 1000000 + frame
            boot_acc.append(acc)
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
            boot_frames = frame
            break
    t.press(0)
    if t.until(1, 0x8457) < 0:
        raise RuntimeError('first update not reached')
    st = t.save(); t.load(st)
    entered_clock = t.clock()
    (a.out).mkdir(parents=True, exist_ok=True)
    (a.out / f'{a.tag}.entered.state').write_bytes(st)
    arr = {k: np.zeros(n + 1, np.uint8) for k in ('cnt', 'mas', 'm2', 'stg', 'are', 'bos', 'gate', 'live')}
    core = np.zeros(n + 1, np.uint32); wide = np.zeros(n + 1, np.uint32); fend = np.zeros(n + 1, np.uint64)
    accs, hits = list(boot_acc), []
    ram = np.frombuffer(t.ram, dtype=np.uint8)
    t.frame = 1
    CH = 500
    for f0 in range(1, n + 1, CH):
        k = min(CH, n + 1 - f0)
        for f in range(f0, f0 + k):
            acc, h = t.run_w(1, inp[f - 1:f], keys)
            if len(acc): accs.append(acc)
            if len(h): hits.append(h)
            r = bytes(t.ram)
            arr['cnt'][f] = r[0]; arr['mas'][f] = r[0x240]; arr['m2'][f] = r[0x241]
            arr['stg'][f] = r[0xe5f]; arr['are'][f] = r[0xe60]; arr['bos'][f] = r[0x1035]
            arr['gate'][f] = r[0x174a]; arr['live'][f] = r[0x17e0]   # RENT+$0A (M form: $CE MS, $4E MN), LIVE
            core[f] = fp(r, CORE); wide[f] = fp(r, WIDE); fend[f] = t.clock()
        if f0 // CH % 40 == 0:
            print(a.tag, f0 + k - 1, round(time.time() - t0), flush=True)
    accs = np.concatenate(accs) if accs else np.zeros(0, dtype=t.run_w(0)[0].dtype)
    hits = np.concatenate(hits) if hits else np.zeros(0)
    np.savez_compressed(a.out / f'{a.tag}.npz', **arr, core=core, wide=wide, fend=fend, acc=accs, hits=hits,
                        names=np.array(NAMES), boot_frames=boot_frames, entered_clock=entered_clock,
                        watch=np.array([lo, hi]))
    print(a.tag, 'done', n, 'frames', round(time.time() - t0), 's; boot', boot_frames, 'watched writes', len(accs))


if __name__ == '__main__':
    main()
