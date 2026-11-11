"""(f) Screenshots: replay stored runs to given frames in HELL and in Original
(fresh sessions from the shared start state, language English) and save
both pictures; with ':menu' also open the popup there in HELL; with
':preview' open it in Original, go to PALETTE, press Left (ORIGINAL wraps to
HELL) and save the live preview 30 frames later.
usage: shots.py ROM OUT run:frame[:menu][:preview] ..."""
import sys
from pathlib import Path

from helltools import Session, load_run


def tap(g, button, after=4):
    g.press({button})
    g.checked_step(2)
    g.press(set())
    g.checked_step(after)


def replay(g, run, frame):
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
    for f in range(frame):
        g.press(set(inputs[f]))
        g.checked_step(1)
    g.press(set())


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    from helltools import cv
    for spec in sys.argv[3:]:
        name, frame, *extra = spec.split(':')
        run, frame = load_run(name), int(frame)
        for flags, tag in ((0x18, 'hell'), (0x00, 'original')):
            with Session(rom, flags) as g:
                g.write(0x1227, b'\x01')
                cv.start_stage(g, run['stage'])
                replay(g, run, frame)
                g.checked_step(1)
                (out / f'{name}-f{frame}-{tag}.png').write_bytes(g.screenshot())
                if flags and 'menu' in extra:
                    tap(g, 'select', 12)
                    (out / f'{name}-f{frame}-hell-popup.png').write_bytes(g.screenshot())
                if not flags and 'preview' in extra:
                    tap(g, 'select', 12)
                    for _ in range(4):
                        tap(g, 'down')
                    tap(g, 'left', 30)
                    (out / f'{name}-f{frame}-preview-hell.png').write_bytes(g.screenshot())
                    print('options during the preview', hex(g.read(0x100, 1)[0]), flush=True)
        print('shot', spec, flush=True)


if __name__ == '__main__':
    main()
