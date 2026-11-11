"""How much later may the reset initialization end before the boot moves by
a frame? The reset code runs about 5.8 frames with interrupts off, so the
first vblank interrupt is taken as soon as it enables them ($E060), wherever
the raster is; from the second on the main loop (bank 0 $E061: jsr $FD67,
the vblank wait) is tied to the raster. The loader's cost must stay below
the time the main loop spends waiting before the second interrupt.
Prints the master clocks of the first arrivals at $E061 and the first
vblank interrupts ($FCD7), and that wait.
usage: bootslack.py ROM [BRAM-IMAGE]"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from check_bram import clock, continue_to  # noqa: E402
from comparison_video import Game  # noqa: E402

image = Path(sys.argv[2]).read_bytes() if len(sys.argv) > 2 else None
with tempfile.TemporaryDirectory() as folder, Game(os.environ['NG_EMULATOR'], folder) as game:
    work = Path(folder)
    game.power_on(sys.argv[1], image)
    for offset in ('0061', '1cd7'):
        game.call('set_breakpoint', {'address': offset, 'memory_area': 'rom', 'execute': True})
    times = {'E061': [], 'FCD7': []}
    while len(times['FCD7']) < 4:
        pc = continue_to(game)
        times[pc].append(clock(game, work))
    waits = [t for t in times['E061'] if t < times['FCD7'][1]]
    slack = times['FCD7'][1] - waits[-1]
    print(Path(sys.argv[1]).name, 'vblank waits', times['E061'][:4], 'vblank interrupts', times['FCD7'],
          f'\n  the main loop waits {slack} clocks = {slack / 1365:.1f} lines for the second interrupt')
