"""NES-A / NES-B animated colours (research reference, not a maintained
tool): for Level Select entries, FRAMES frames in the mode (fresh session
from the shared start state, health refilled), the colours each animated RAM
palette entry takes ($2286; the entries of the stage's animation set,
nes_palette.original_animations). Each must come from the mode's own list
for that entry (NES-A: animations.json; NES-B: relit), and the other
variant's list is reported for contrast.
The stage's set is the one whose every entry holds only its list's colours
and changes at least once (or, where this variant's lists are each one
colour, as NES-B's 3-1 lists, holds it).
usage: animcheck.py ROM FLAGS FRAMES stage,stage,..."""
import os
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from gbtools import ORIGINAL, Session, cv, ram_palette  # noqa: E402
import nes_palette as NP  # noqa: E402

rom, flags, frames = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3])
stages = [int(x) for x in sys.argv[4].split(',')]
orig = ORIGINAL.read_bytes()
orig = orig[512:] if len(orig) % 8192 == 512 else orig
data = NP.load()
mine = NP.layout(NP.relit(data) if flags & 0x20 else data)['animations']
other = NP.layout(data if flags & 0x20 else NP.relit(data))['animations']
sprite = {(s, e): f != 0 for s, recs in enumerate(NP.original_animations(orig)) for _, f, e, _, _ in recs}
SETTLE = 60                  # frames after the first update left out (the stage's fade-in)
ok = True
for stage in stages:
    with Session(rom, flags) as g:
        cv.start_stage(g, stage)
        seen = {}
        for n in range(SETTLE + frames):
            g.write(0xead, bytes([16]))
            g.checked_step(1)
            if n < SETTLE:
                continue
            pal = ram_palette(g.read(0, 0x2000))
            for s, lists in mine.items():
                for e, cols in lists:
                    seen.setdefault((s, e), set()).add(pal[256 + e if sprite[(s, e)] else e])
    # Which set is this stage's: the one whose entries all hold list colours.
    match = [s for s, lists in mine.items() if all(seen[(s, e)] <= set(cols) for e, cols in lists)
             and (any(len(seen[(s, e)]) > 1 for e, _ in lists) or all(len(set(c)) == 1 for _, c in lists))
             and any(seen[(s, e)] != {0} for e, _ in lists)]
    for s in match:
        lists = dict(mine[s])
        olists = dict(other[s])
        differs = sum(1 for e in lists if set(lists[e]) != set(olists[e]))
        print(cv.STAGE_NAMES[stage], 'flags', hex(flags), 'animation set', s, 'entries', sorted(lists),
              'every value from this mode\'s lists; lists differing from the other variant', differs, 'of', len(lists),
              'values seen', {e: sorted(f'{c:03X}' for c in seen[(s, e)]) for e in lists}, flush=True)
    if not match:
        ok = False
        print(cv.STAGE_NAMES[stage], 'flags', hex(flags), 'NO animation set matched', flush=True)
print('animcheck', 'passed' if ok else 'FAILED')
