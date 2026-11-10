"""Cold boot ROM; log ($2240,$2241) changes and palette-queue activity per
frame (read after each frame step, i.e. at the start of vblank before the
IRQ flushes the queue). With 'mash', press Run 2 frames in every 20.
usage: bootstates.py ROM FRAMES [mash]"""
import sys
import tempfile
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from comparison_video import Game  # noqa: E402

EMU = '/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx'
WORK = Path('/workspace/build/gb-palette')
rom, frames = sys.argv[1], int(sys.argv[2])
mash = len(sys.argv) > 3
work = Path(tempfile.mkdtemp(prefix='boot-', dir=WORK))
try:
    with Game(EMU, work) as g:
        g.call('load_media', {'file_path': str(Path(rom).resolve())})
        g.call('debug_pause')
        prev = None
        for f in range(frames):
            if mash:
                g.press({'run'} if f % 20 < 2 else set())
            g.step(1)
            ram = g.read(0x200, 0x100)
            m = (ram[0x40], ram[0x41])
            q = ram[0x60]
            if m != prev or q:
                ents = [(ram[0x71 + k] | ram[0x79 + k] << 8, (ram[0x61 + k] | ram[0x69 + k] << 8) // 2)
                        for k in range(min(q, 8))]
                stage = g.read(0xe5f, 2)
                print(f, 'master', m, 'q', ents, 'lock', ram[0x83], 'stage', stage.hex(), flush=True)
                prev = m
finally:
    shutil.rmtree(work, ignore_errors=True)
