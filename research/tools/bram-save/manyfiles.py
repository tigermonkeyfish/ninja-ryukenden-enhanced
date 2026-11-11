"""Where does a long directory start to delay the boot? (evidence for
docs/validation/bram-save.md, "Many files")

For each N: a formatted backup RAM holding N other games' files of SIZE
bytes each (18 by default; 16 is the smallest an entry can be), a cold boot
of ROM with Run mashed; prints the reset loader's master clocks ($FFE6 to
the native init $FCBE) and the frame of the first 1-1 update. The frame is
the original's (163) while the loader ends before the boot's second vblank
interrupt (bootslack.py) and one later from then on.

usage: manyfiles.py ROM N [N ...] [--size SIZE] [--ours]   (--ours: our entry last)
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import bram_image as bi  # noqa: E402
from check_bram import boot, loader_clocks  # noqa: E402
from comparison_video import Game  # noqa: E402

args = sys.argv[1:]
ours = '--ours' in args
size = int(args[args.index('--size') + 1]) if '--size' in args else 18
rom = args[0]
counts = [int(a) for a in args[1:] if a.isdigit() and (args[args.index(a) - 1] != '--size')]
EMU = os.environ['NG_EMULATOR']
for n in counts:
    entries = [bi.other(k, size) for k in range(n)] + ([bi.settings_entry(0x00, 1)] if ours else [])
    image = bi.image(entries)
    with tempfile.TemporaryDirectory() as folder:
        clocks = loader_clocks(EMU, rom, image, Path(folder))
        with Game(EMU, folder) as game:
            started = boot(game, rom, image, Path(folder))
    print(f'{n} files of {size} bytes{" and ours" if ours else ""}: loader {clocks} clocks = {clocks / 1365:.1f} lines, '
          f"first update at frame {started['first_update_frame']}, status {bi.STATUS[started['status']]}", flush=True)
