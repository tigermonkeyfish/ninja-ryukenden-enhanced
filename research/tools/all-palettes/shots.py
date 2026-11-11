"""Screenshots in every palette mode (research reference, not a maintained
tool): replay stored runs to given frames (fresh session per mode from the
shared start state, language English, $2100 = the mode) and save the
picture; with ':menu' also open the popup there and save it, after checking
that the PALETTE row reads the mode's name (check_menu.field_text).
Modes: original $00, nes-a $08, nes-b $28, gb-dmg $10, hell $18, sms $B8.
usage: shots.py ROM OUT run:frame[:menu] ..."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from gbtools import Session, cv, load_run  # noqa: E402
import check_menu as CM  # noqa: E402

MODES = [('original', 0x00, 'ORIGINAL'), ('nes-a', 0x08, 'NES-A'), ('nes-b', 0x28, 'NES-B'),
         ('gb-dmg', 0x10, 'GB DMG'), ('hell', 0x18, 'HELL'), ('sms', 0xb8, 'SMS')]


def tap(g, button, after=4):
    g.press({button})
    g.checked_step(2)
    g.press(set())
    g.checked_step(after)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for spec in sys.argv[3:]:
        name, frame, *extra = spec.split(':')
        run, frame = load_run(name), int(frame)
        inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
        for tag, flags, text in MODES:
            with Session(rom, flags) as g:
                g.write(0x1227, b'\x01')
                cv.start_stage(g, run['stage'])
                for f in range(frame):
                    g.press(set(inputs[f]))
                    g.checked_step(1)
                g.press(set())
                g.checked_step(1)
                (out / f'{name}-f{frame}-{tag}.png').write_bytes(g.screenshot())
                if 'menu' in extra:
                    tap(g, 'select', 12)
                    ram = g.read(0, 0x2000)
                    shown = CM.field_text(g, CM.box_column(ram), 4).strip()
                    good = shown == text and ram[0x100] == flags
                    ok = ok and good
                    (out / f'{name}-f{frame}-{tag}-popup.png').write_bytes(g.screenshot())
                    print(spec, tag, 'PALETTE row reads', repr(shown), '$2100', hex(ram[0x100]),
                          'ok' if good else 'MISMATCH', flush=True)
        print('shot', spec, flush=True)
    print('shots', 'passed' if ok else 'FAILED')


if __name__ == '__main__':
    main()
