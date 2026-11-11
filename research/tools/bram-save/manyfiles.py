"""Where does a long directory start to delay the boot, and by how much?
(evidence for docs/validation/bram-save.md, "Many files")

For each N: a formatted backup RAM holding N other games' files of SIZE
bytes each (18 by default; 16 is the smallest an entry can be), and

- the reset loader's master clocks ($FFE6 to the native init $FCBE);
- an idle boot (no input) of IDLE frames, picture by picture, against the
  same ROM's boot without backup RAM: identical, or the same pictures K
  frames later (the shift is printed; "differs" if neither);
- the frame of the first 1-1 update when Run is mashed from power-on as
  check_boot.py does it (2 frames in every 20). A boot that runs one frame
  behind meets those presses in another phase, so this number can move by
  a whole press period; the idle shift is the real delay.

usage: manyfiles.py ROM N [N ...] [--size SIZE] [--ours] [--idle IDLE]
       (--ours: our entry last; IDLE default 700)
"""
import hashlib
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import bram_image as bi  # noqa: E402
from check_bram import boot, loader_clocks  # noqa: E402
from comparison_video import Game  # noqa: E402

args = sys.argv[1:]


def option(name, default):
    if name in args:
        at = args.index(name)
        value = int(args[at + 1])
        del args[at:at + 2]
        return value
    return default


size = option('--size', 18)
IDLE = option('--idle', 700)
ours = '--ours' in args
if ours:
    args.remove('--ours')
rom, counts = args[0], [int(a) for a in args[1:]]
EMU = os.environ['NG_EMULATOR']


def idle(image):
    with tempfile.TemporaryDirectory() as folder, Game(EMU, folder) as game:
        game.power_on(rom, image)
        hashes = []
        for _ in range(IDLE):
            game.step(1)
            hashes.append(hashlib.sha256(game.screenshot()).hexdigest())
        assert game.backup_ram() == image
        return hashes


plain = idle(None)
for n in counts:
    entries = [bi.other(k, size) for k in range(n)] + ([bi.settings_entry(0x00, 1)] if ours else [])
    image = bi.image(entries)
    with tempfile.TemporaryDirectory() as folder:
        clocks = loader_clocks(EMU, rom, image, Path(folder))
        with Game(EMU, folder) as game:
            started = boot(game, rom, image, Path(folder))
    here = idle(image)
    # Frame 0's picture differs between sessions of one ROM (check_boot.py).
    shift = next((k for k in range(4) if here[k + 1:] == plain[1:IDLE - k]), None)
    print(f'{n} files of {size} bytes{" and ours" if ours else ""}: loader {clocks} clocks = {clocks / 1365:.1f} lines; '
          f'idle boot, {IDLE} frames: ' + ('differs' if shift is None else 'identical' if shift == 0 else
                                           f'the same pictures {shift} frame(s) later')
          + f"; mashing Run: first update at frame {started['first_update_frame']}, "
          f"status {bi.STATUS[started['status']]}", flush=True)
