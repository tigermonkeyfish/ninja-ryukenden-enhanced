"""HELL screenshots on one ROM (research reference, not a maintained tool):
a stored run replayed to a frame ('run:NAME:FRAME[:menu]') or a Level Select
entry held right for FRAME frames ('ls:INDEX:FRAME[:menu]'), in a fresh
session per shot, language English, $2100 = FLAGS; saves OUT/TAG-<spec>.png
and with ':menu' the popup opened there (checking that the PALETTE row
reads HELL and $2100 is unchanged).
usage: shots11.py ROM OUT TAG FLAGS SPEC...   (GB_WORK: seed.state, original.pce)"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from gbtools import Session, cv, load_run  # noqa: E402
import check_menu as CM  # noqa: E402

NAMES = {0x00: 'ORIGINAL', 0x18: 'HELL'}


def tap(g, button, after=4):
    g.press({button})
    g.checked_step(2)
    g.press(set())
    g.checked_step(after)


def main():
    rom, out, tag, flags = sys.argv[1], Path(sys.argv[2]), sys.argv[3], int(sys.argv[4], 0)
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for spec in sys.argv[5:]:
        kind, which, frame, *extra = spec.split(':')
        frame = int(frame)
        with Session(rom, flags) as g:
            g.write(0x1227, b'\x01')
            if kind == 'run':
                run = load_run(which)
                inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
                cv.start_stage(g, run['stage'])
            else:
                inputs = [['right']] * frame
                cv.start_stage(g, int(which))
            for f in range(frame):
                g.press(set(inputs[f]))
                g.checked_step(1)
            g.press(set())
            g.checked_step(1)
            name = spec.replace(':menu', '').replace(':', '-')
            (out / f'{tag}-{name}.png').write_bytes(g.screenshot())
            ram = g.read(0, 0x2000)
            line = f'{spec} stage {ram[0xe5f]} area {ram[0xe60]} master {ram[0x240]}'
            if 'menu' in extra:
                tap(g, 'select', 12)
                ram = g.read(0, 0x2000)
                shown = CM.field_text(g, CM.box_column(ram), 4).strip()
                good = shown == NAMES.get(flags, '?') and ram[0x100] == flags
                ok = ok and good
                (out / f'{tag}-{name}-popup.png').write_bytes(g.screenshot())
                line += f'; popup PALETTE row reads {shown!r}, $2100 {ram[0x100]:#04x} {"ok" if good else "MISMATCH"}'
            print(line, flush=True)
    print('shots', 'passed' if ok else 'FAILED')


if __name__ == '__main__':
    main()
