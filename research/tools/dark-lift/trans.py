"""Stage and area transitions in one palette mode, frame by frame (research
reference, not a maintained tool). A mapped mode (GB DMG, HELL, SMS) shows a
black screen only when the VCE holds its black; this probe records, for
every frame of a chain of transitions, what the playfield shows and how the
VCE stands against the colours due, so that frames in which the Original
mode's screen is black and a mapped mode's is not can be found
(transreport.py).
usage: trans.py ROM OUT TAG FLAGS CASE...
CASE: walk:STAGE        Level Select entry of STAGE; in each area 60 idle
                        frames and 120 holding right (health refilled), then
                        the area exit is moved onto Ryu; ends TAIL frames
                        after the stage changes or a cinema begins
                        ($2240 != 0), or when an exit does nothing in 240
                        frames
      run:NAME          a stored run, every frame (and its 60-frame tail)
      die:STAGE         Level Select entry, 60 idle frames, then Ryu's
                        health is written to 0 once; 420 frames
Per frame (OUT/TAG-<case>.json): master state, stage, area, lock, queue
count, the fade's bytes $2A8A-$2A8E, the module's state $2104, the share of
the playfield (screenshot rows 50-241) that is not the mode's black, its
colours (the 6 commonest, as PC Engine words), the VCE entries that differ
from the colour due (count, how many of those are not black in the VCE, the
first few), and a hash of the gameplay fields.
(GB_WORK: seed.state, original.pce)"""
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from gbtools import Session, cv, load_run  # noqa: E402
import palette_tables as PT  # noqa: E402

TAIL = 200


def tables(flags):
    """(table for a stage number, entries mapped) of the mode in $2100."""
    family = flags & 0x98
    if family == 0x10:
        t = PT.gb_dmg_table()
        return (lambda stage: t), 512
    if family == 0x98:
        t = PT.sms_table()
        return (lambda stage: t), 512
    if family == 0x18:
        cache = {}
        return (lambda stage: cache.setdefault(stage, PT.hell_stage_table(stage))), PT.load_hell()['mapped_entries']
    ident = list(range(512))
    return (lambda stage: ident), 0


def words(rgb):
    q = np.round(rgb.astype(int) * 7 / 255).astype(int)
    return (q[..., 1] << 6) | (q[..., 0] << 3) | q[..., 2]


class Recorder:
    def __init__(self, out, tag, case, flags):
        self.path = out / f'{tag}-{case.replace(":", "-")}.json'
        self.table, self.mapped = tables(flags)
        self.rows = []
        self.keep = None

    def frame(self, g, n, note=''):
        png = g.screenshot()
        rgb = np.array(Image.open(io.BytesIO(png)).convert('RGB'))[50:242]
        ram = g.read(0, 0x1000)
        vce = g.read(0, 1024, 8)
        stage = ram[0xe5f]
        t = self.table(stage)
        v = [(vce[2 * i] | vce[2 * i + 1] << 8) & 0x1ff for i in range(512)]
        r = [(ram[0x286 + 2 * i] | ram[0x287 + 2 * i] << 8) & 0x1ff for i in range(512)]
        border = (ram[0x281] | ram[0x282] << 8) & 0x1ff
        gameplay = ram[0x240] == 0
        due = [(t[c] if gameplay and i < self.mapped else c) for i, c in enumerate(r)]
        due[256] = t[border] if gameplay and self.mapped == 512 else border
        black = t[0] if gameplay and self.mapped else 0
        late = [i for i in range(512) if v[i] != due[i]]
        lit = [i for i in late if v[i] != black]
        w, counts = np.unique(words(rgb), return_counts=True)
        top = sorted(zip(counts.tolist(), w.tolist()), reverse=True)
        size = rgb.shape[0] * rgb.shape[1]
        notblack = sum(k for k, c in top if c != black)
        row = {'f': n, 'note': note, 'master': ram[0x240], 'stage': stage, 'area': ram[0xe60],
               'lock': ram[0x283], 'queue': ram[0x260], 'fade': ram[0xa8a:0xa8f].hex(), 'state': ram[0x104],
               'timer': ram[0xe63], 'notblack': round(notblack * 100 / size, 3),
               'top': [[f'{c:03X}', round(k * 100 / size, 2)] for k, c in top[:6]],
               'late': len(late), 'lit': len(lit), 'lit_first': lit[:24],
               'lit_colours': sorted({f'{v[i]:03X}' for i in lit})[:12],
               'ramblack': sum(1 for c in r if c == 0),
               'play': hashlib.sha1(ram[0xe9e:0xeb8] + ram[0xeda:0xede] + ram[0x20f:0x211] + bytes(
                   [ram[0xe5f], ram[0xe60], ram[0xeaf], ram[0xead], ram[0x240]])).hexdigest()[:10],
               'png': hashlib.sha1(png).hexdigest()[:10]}
        self.rows.append(row)
        if self.keep is not None and n in self.keep:
            self.path.with_name(f'{self.path.stem}-f{n:05d}.png').write_bytes(png)
        return ram

    def close(self):
        self.path.write_text(json.dumps(self.rows))
        print(self.path.name, len(self.rows), 'frames', flush=True)


def walk_case(g, rec, stage):
    cv.start_stage(g, stage)
    n, area = 0, 0

    def frames(count, buttons):
        nonlocal n
        g.press(buttons)
        ram = None
        for _ in range(count):
            g.write(0xead, bytes([16]))
            g.checked_step(1)
            ram = rec.frame(g, n)
            n += 1
            if ram[0x240] or ram[0xe5f] != stage:
                return ram
        return ram

    while True:
        ram = frames(60, set())
        if not (ram[0x240] or ram[0xe5f] != stage):
            ram = frames(120, {'right'})
        if ram[0x240] or ram[0xe5f] != stage:
            break
        g.press(set())
        r = g.read(0xe9f, 1)[0]
        box = g.read(0xeb5, 6)
        g.write(0xe87, bytes([r]))
        g.write(0xe81, bytes([(box[0] + box[3]) // 2, (box[2] + box[5]) // 2]))
        moved = False
        for _ in range(240):
            g.write(0xead, bytes([16]))
            g.checked_step(1)
            ram = rec.frame(g, n, 'exit')
            n += 1
            if ram[0x240] or ram[0xe5f] != stage or ram[0xe60] != area:
                moved = True
                break
        if not moved:
            print('walk', stage, 'area', area, 'exit did nothing', flush=True)
            return
        if ram[0x240] or ram[0xe5f] != stage:
            break
        area = ram[0xe60]
        if area > 12:
            break
    for _ in range(TAIL):
        g.write(0xead, bytes([16]))
        g.checked_step(1)
        rec.frame(g, n, 'tail')
        n += 1


def run_case(g, rec, name):
    run = load_run(name)
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
    cv.start_stage(g, run['stage'])
    for f, buttons in enumerate(inputs):
        g.press(set(buttons))
        g.checked_step(1)
        rec.frame(g, f)


def die_case(g, rec, stage):
    cv.start_stage(g, stage)
    for n in range(480):
        if n == 60:
            g.write(0xead, bytes([0]))
        g.checked_step(1)
        rec.frame(g, n, 'dead' if n >= 60 else '')


def main():
    rom, out, tag, flags = sys.argv[1], Path(sys.argv[2]), sys.argv[3], int(sys.argv[4], 0)
    out.mkdir(parents=True, exist_ok=True)
    for case in sys.argv[5:]:
        case, _, keep = case.partition('@')
        kind, *a = case.split(':')
        rec = Recorder(out, tag, case, flags)
        if keep:                       # CASE@f1,f2,..: also keep those frames' pictures
            rec.keep = {int(x) for x in keep.split(',')}
        with Session(rom, flags) as g:
            g.write(0x1227, b'\x01')
            if kind == 'walk':
                walk_case(g, rec, int(a[0]))
            elif kind == 'run':
                run_case(g, rec, a[0])
            else:
                die_case(g, rec, int(a[0]))
        rec.close()


if __name__ == '__main__':
    main()
