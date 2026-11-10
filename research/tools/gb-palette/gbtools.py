"""Shared helpers for the GB palette probes (research reference, not a
maintained tool). Sessions follow docs/pc-engine/EMULATOR.md: one seed state
of the original, one fresh session per replay."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import comparison_video as cv  # noqa: E402

EMU = os.environ.get('NG_EMULATOR', '/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx')
WORK = Path(os.environ.get('GB_WORK', '/workspace/build/gb-palette'))
SEED = WORK / 'seed.state'
ORIGINAL = WORK / 'original.pce'
RUNS = ROOT / 'research/comparison-runs'
RUN_NAMES = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']


def seed():
    if not SEED.exists():
        cv.make_seed(EMU, ORIGINAL, SEED)
    return SEED


class Session:
    """A fresh emulator session in a temporary directory, deleted on exit."""

    def __init__(self, rom, flags=None):
        self.rom, self.flags = rom, flags

    def __enter__(self):
        self.dir = Path(tempfile.mkdtemp(prefix='s-', dir=WORK))
        self.game = cv.Game(EMU, self.dir).__enter__()
        cv.start_point(self.game, self.rom, seed(), self.flags is not None)
        if self.flags is not None:
            self.game.write(0x100, bytes([self.flags, self.flags]))
        return self.game

    def __exit__(self, *exc):
        try:
            self.game.__exit__(*exc)
        finally:
            shutil.rmtree(self.dir, ignore_errors=True)


def h(data):
    return hashlib.sha1(data).hexdigest()[:16]


def ram_palette(ram):
    """The 512 RAM palette words ($2286) from a System RAM dump (offset 0 = $2000)."""
    return [ram[0x286 + 2 * i] | ram[0x287 + 2 * i] << 8 for i in range(512)]


def vce_words(vce):
    return [vce[2 * i] | vce[2 * i + 1] << 8 for i in range(512)]


def queue(ram):
    n = ram[0x260]
    return n, [(ram[0x271 + k] | ram[0x279 + k] << 8, (ram[0x261 + k] | ram[0x269 + k] << 8) // 2)
               for k in range(min(n, 8))]


def load_run(name):
    return json.loads((RUNS / f'{name}.json').read_text())
