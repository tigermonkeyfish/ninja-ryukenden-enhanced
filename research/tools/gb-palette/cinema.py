"""Cinemas keep the original colours in GB DMG mode (scope check).

Replays RUN with $2100 = FLAGS, then completes the following stages through
the native completion path (as comparison_video.cinema_after does) until
the next cinema has played and gameplay resumes. Every frame: in gameplay
($2240 = 0) the VCE is compared with the GB table value of the RAM palette,
in a cinema ($2240 = 1) with the RAM palette itself. Reports mismatching
frames per state and how long the first gameplay frames after the cinema
take to map; saves one cinema screenshot.
usage: cinema.py ROM RUN FLAGS [SHOT.png]"""
import json
import sys
from pathlib import Path

from gbtools import Session, cv, load_run, ram_palette, vce_words
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table  # noqa: E402

GB = gb_dmg_table()


def mismatches(g, mapped):
    ram = g.read(0, 0x2000)
    f = (lambda c: GB[c & 0x1ff]) if mapped else (lambda c: c)
    vce, pal = vce_words(g.read(0, 1024, area=8)), ram_palette(ram)
    border = f(ram[0x281] | ram[0x282] << 8)
    return ram[0x240], sum(1 for i in range(512) if vce[i] != f(pal[i]) and not (i == 256 and vce[i] == border))


def main():
    rom, run_name, flags = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
    shot = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    run = load_run(run_name)
    stats = {'gameplay_frames': 0, 'gameplay_bad': [], 'cinema_frames': 0, 'cinema_bad': [],
             'after_cinema': []}
    with Session(rom, flags) as g:
        g.write(0x1227, b'\x01')
        cv.start_stage(g, run['stage'])
        for count, buttons in run['segments']:
            g.press(set(buttons))
            g.checked_step(count)
        g.press(set())
        # The run's own stage end may start the cinema a few frames later.
        for _ in range(120):
            if g.read(0x240, 1)[0] != 0:
                break
            g.checked_step(1)
        seen_cinema, n = False, 0
        for _ in range(40000):
            kind = g.read(0x240, 1)[0]
            if kind == 0 and seen_cinema:
                for k in range(30):
                    g.checked_step(1)
                    stats['after_cinema'].append(mismatches(g, flags & 0x18 == 0x10)[1])
                break
            if kind == 0:
                g.step(120)
                g.call('debug_run_to_cursor', {'address': '8457'})
                for _ in range(20000):
                    status = g.call('debug_get_status')
                    if status.get('paused'):
                        break
                g.reg('PC', 0x8478)
                for _ in range(1200):
                    g.step(1)
                    m, bad = mismatches(g, flags & 0x18 == 0x10)
                    if m == 0:
                        stats['gameplay_frames'] += 1
                        if bad:
                            stats['gameplay_bad'].append((n, bad))
                    n += 1
                    if m != 0:
                        break
                continue
            seen_cinema = True
            g.checked_step(1)
            n += 1
            m, bad = mismatches(g, False)
            stats['cinema_frames'] += 1
            if bad:
                stats['cinema_bad'].append((n, m, bad))
            if shot and stats['cinema_frames'] == 400:
                shot.parent.mkdir(parents=True, exist_ok=True)
                shot.write_bytes(g.screenshot())
    stats['gameplay_bad'] = stats['gameplay_bad'][:20]
    stats['cinema_bad_count'] = len(stats['cinema_bad'])
    stats['cinema_bad'] = stats['cinema_bad'][:20]
    print(json.dumps({'run': run_name, 'flags': flags, **stats}), flush=True)


if __name__ == '__main__':
    main()
