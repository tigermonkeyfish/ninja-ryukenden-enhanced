"""Shared helpers for the SMS palette probes (research reference, not a
maintained tool). They reuse the GB palette probes' session helpers
(research/tools/gb-palette/gbtools.py: one seed state of the original, one
fresh session per replay) and the HELL probes' layout; set GB_WORK to the
work folder (default /workspace/build/sms-palette), which must hold
original.pce.

Palette modes since the SMS build: $2100 bits 3-5 ($00 Original, $08 NES-A,
$28 NES-B, $10 GB DMG, $18 HELL, $38 SMS; $20 uploads as Original, $30 as
GB DMG) and bit 7 set exactly with SMS (so SMS is $B8 in $2100); the
palette module's state is $2104 bits 5-7 (before: $2100 bits 5-7).
mode_due(flags) gives the mapping a $2100 value's gameplay is due for, as
the upload dispatches: $2100 & $98 compared with $10."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/sms-palette')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))

import gbtools  # noqa: E402
from gbtools import RUN_NAMES, Session, cv, h, load_run, queue, ram_palette, vce_words  # noqa: E402,F401
from palette_tables import gb_dmg_table, hell_table, load_hell, sms_colours, sms_table  # noqa: E402

GB = gb_dmg_table()
HELL = hell_table()
HELL_MAPPED = load_hell()['mapped_entries']
SMS = sms_table()
SMS64 = sms_colours()
SMS_FLAGS = 0xb8            # $2100 for SMS: mode $38 and bit 7


def mode_due(flags):
    """0 (raw), 0x10 (GB DMG), 0x18 (HELL) or 0x38 (SMS) for $2100 = flags in
    gameplay, as the upload's dispatch decides: m = flags & $98; below $10
    raw, $10 GB DMG, above it HELL if m - $10 < $80, else SMS."""
    m = flags & 0x98
    if m < 0x10:
        return 0
    if m == 0x10:
        return 0x10
    return 0x38 if (m - 0x10) & 0x80 else 0x18


def hell_entry(i, colour):
    """What VCE entry i shows in HELL gameplay for RAM colour `colour`."""
    colour &= 0x1ff
    return HELL[colour] if i < HELL_MAPPED else colour


def expected(mode, pal, border):
    """The 512 VCE words due in gameplay for a RAM palette and border colour:
    mode 0 original, 0x10 GB DMG, 0x18 HELL, 0x38 SMS (entry $100 is the
    border)."""
    words = list(pal)
    words[256] = border
    if mode == 0x10:
        return [GB[c & 0x1ff] for c in words]
    if mode == 0x18:
        return [hell_entry(i, c) for i, c in enumerate(words)]
    if mode == 0x38:
        return [SMS[c & 0x1ff] for c in words]
    return [c & 0x1ff for c in words]


def mismatches(vce, pal, border, mode):
    want = expected(mode, pal, border)
    return [i for i in range(512) if vce[i] != want[i]]
