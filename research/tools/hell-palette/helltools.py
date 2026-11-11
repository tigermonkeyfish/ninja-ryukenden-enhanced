"""Shared helpers for the HELL palette probes (research reference, not a
maintained tool). They reuse the GB palette probes' session helpers
(research/tools/gb-palette/gbtools.py: one seed state of the original, one
fresh session per replay); set GB_WORK to the work folder (default
/workspace/build/hell-palette), which must hold original.pce."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/hell-palette')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))

import gbtools  # noqa: E402
from gbtools import RUN_NAMES, Session, cv, h, load_run, queue, ram_palette, vce_words  # noqa: E402,F401
from palette_tables import gb_dmg_table, hell_table, load_hell  # noqa: E402

GB = gb_dmg_table()
HELL = hell_table()
HELL_MAPPED = load_hell()['mapped_entries']


def hell_entry(i, colour):
    """What VCE entry i shows in HELL gameplay for RAM colour `colour`."""
    colour &= 0x1ff
    return HELL[colour] if i < HELL_MAPPED else colour


def expected(mode, pal, border):
    """The 512 VCE words due in gameplay for a RAM palette and border colour:
    mode 0 original, 0x10 GB DMG, 0x18 HELL (entry $100 is the border)."""
    words = list(pal)
    words[256] = border
    if mode == 0x10:
        return [GB[c & 0x1ff] for c in words]
    if mode == 0x18:
        return [hell_entry(i, c) for i, c in enumerate(words)]
    return [c & 0x1ff for c in words]


def mismatches(vce, pal, border, mode):
    want = expected(mode, pal, border)
    return [i for i in range(512) if vce[i] != want[i]]
