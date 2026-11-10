"""Open the in-game menu (Select) at frame AT of a stored run with $2100 =
FLAGS, take a screenshot after 40 frames, check the VCE against the RAM
palette (GB table values in GB DMG mode), press Run (accept) and report
$2100 afterwards (the draft must keep bits 3-4).
usage: menu_shot.py ROM RUN AT FLAGS OUT.png"""
import json
import sys
from pathlib import Path

from gbtools import Session, cv, load_run, ram_palette, vce_words
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table  # noqa: E402

GB = gb_dmg_table()

rom, run_name, at, flags, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4], 0), Path(sys.argv[5])
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)]
with Session(rom, flags) as g:
    cv.start_stage(g, run['stage'])
    for f in range(at):
        g.press(inputs[f])
        g.checked_step(1)
    g.press({'select'})
    g.checked_step(2)
    g.press(set())
    g.checked_step(40)
    rows = g.read(28 * 64, 128, area=4)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(g.screenshot())
    ram = g.read(0, 0x2000)
    f = (lambda c: GB[c & 0x1ff]) if flags & 0x18 == 0x10 else (lambda c: c)
    vce, pal = vce_words(g.read(0, 1024, area=8)), ram_palette(ram)
    border = f(ram[0x281] | ram[0x282] << 8)
    bad = [i for i in range(512) if vce[i] != f(pal[i]) and not (i == 256 and vce[i] == border)]
    g.press({'run'})
    g.checked_step(2)
    g.press(set())
    g.checked_step(10)
    print(json.dumps({'run': run_name, 'at': at, 'flags': flags, 'menu_text_row28': rows[:16].hex(),
                      'vce_mismatches': len(bad), 'options_after_accept': g.read(0x100, 1)[0]}))
