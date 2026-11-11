"""Fade frames in one palette mode, frame by frame (research reference, not
a maintained tool). The mapped modes recolour each fade step's dimmed
colour through their table, so a table that lifts dark colours can show a
step that is lighter than the step before it just before black. This probe
records every frame of a fade: the picture's lightness (CIE L* per pixel of
the playfield, screenshot rows 50-241), its colours, and against the frame
before it the share of playfield pixels that got lighter or darker by more
than 1 L*; it keeps every picture that differs from the frame before it,
with the palette state behind it.
usage: fades.py ROM OUT TAG FLAGS CASE...
CASE: load:STAGE:AFTER     the Level Select entry of STAGE stepped frame by
                           frame from the main-loop hook through the load
                           to AFTER frames after its first update
      run:NAME:FROM:TO     a stored run; frames FROM..TO
      warp:STAGE:AREA:N    as cap.py's warp to area AREA (60 idle frames and
                           120 holding right per area), then the area exit
                           moved onto Ryu and N frames recorded
Writes OUT/TAG-<case>.json and OUT/TAG-<case>-fNNNNN.png.
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
import nes_palette as NP  # noqa: E402

_L = {}


def lightness(rgb):
    """L* per pixel of an (h, w, 3) uint8 array."""
    flat = rgb.reshape(-1, 3)
    u, inv = np.unique(flat, axis=0, return_inverse=True)
    lu = np.array([_L.setdefault(tuple(int(v) for v in p), NP.lab(tuple(int(v) for v in p))[0]) for p in u])
    return lu[inv.reshape(-1)].reshape(rgb.shape[:2])


def words(rgb):
    q = np.round(rgb.astype(int) * 7 / 255).astype(int)
    return (q[..., 1] << 6) | (q[..., 0] << 3) | q[..., 2]


class Recorder:
    def __init__(self, out, tag, case):
        self.base = out / f'{tag}-{case.replace(":", "-")}'
        self.rows, self.prev_l, self.prev_vce, self.prev_png, self.kept = [], None, None, None, 0

    def frame(self, g, n, note=''):
        png = g.screenshot()
        rgb = np.array(Image.open(io.BytesIO(png)).convert('RGB'))[50:242]
        light = lightness(rgb)
        vce = g.read(0, 1024, 8)
        ram = g.read(0, 0x1000)
        w, counts = np.unique(words(rgb), return_counts=True)
        top = sorted(zip(counts.tolist(), w.tolist()), reverse=True)[:12]
        row = {'f': n, 'note': note, 'master': ram[0x240], 'stage': ram[0xe5f], 'area': ram[0xe60],
               'queue': ram[0x260], 'lock': ram[0x283],
               'meanL': round(float(light.mean()), 2), 'maxL': round(float(light.max()), 1),
               'nonblack': round(float((light > 0).mean()) * 100, 2), 'colours': int(len(w)),
               'top': [[f'{c:03X}', round(k * 100 / light.size, 1)] for k, c in top],
               'vce': hashlib.sha1(vce).hexdigest()[:12], 'new_state': vce != self.prev_vce}
        changed = self.prev_png is None or png != self.prev_png
        if self.prev_l is not None:
            d = light - self.prev_l
            row['lighter'] = round(float((d > 1).mean()) * 100, 2)
            row['darker'] = round(float((d < -1).mean()) * 100, 2)
            row['lighter_by'] = round(float(d[d > 1].mean()), 1) if (d > 1).any() else 0
            row['darker_by'] = round(float(-d[d < -1].mean()), 1) if (d < -1).any() else 0
        row['picture_changed'] = changed
        if changed and self.kept < 260:
            # A new picture: keep it and the palette state behind it (VCE,
            # RAM palette $2286 and the fade's backup $2686, 512 words each).
            Path(f'{self.base}-f{n:05d}.png').write_bytes(png)
            self.kept += 1
            row['vce_words'] = vce.hex()
            row['ram_palette'] = ram[0x286:0x686].hex()
            row['backup'] = ram[0x686:0xa86].hex()
        self.prev_png = png
        self.prev_l, self.prev_vce = light, vce
        self.rows.append(row)

    def close(self):
        Path(str(self.base) + '.json').write_text(json.dumps(self.rows))
        pictures = [r for r in self.rows if r['picture_changed']]
        print(self.base.name, len(self.rows), 'frames,', len(pictures), 'distinct consecutive pictures', flush=True)


def load_case(g, rec, stage, after):
    cpu = g.call('get_huc6280_status')
    assert cpu['PC'] == '83F3', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    g.write(0x241, bytes([stage]))
    g.write(0x247, bytes([cv.NEXT_SEQUENCE[stage], 0]))
    g.write(0xe65, bytes(22))
    g.write(0xead, bytes([16]))
    sp = saved['S']
    g.write(0x100 + sp - 1, bytes([0xf2, 0x83]))
    g.reg('S', sp - 2)
    g.reg('A', stage)
    g.reg('PC', 0x8244)
    for a in ('23f3', '2457'):
        g.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
    n = 0
    rec.frame(g, n, 'hook')
    while True:
        if g.step(1) is not None:
            n += 1
            rec.frame(g, n, 'load')
            continue
        pc = g.call('get_huc6280_status')['PC']
        if pc == '83F3':
            for k in ('X', 'Y', 'P'):
                g.reg(k, saved[k])
            g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
            continue
        if pc == '8457':
            g.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
            break
        raise RuntimeError(f'unexpected stop {pc}')
    for _ in range(after):
        g.step(1)
        n += 1
        rec.frame(g, n, 'play')


def run_case(g, rec, name, first, last):
    run = load_run(name)
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
    cv.start_stage(g, run['stage'])
    for f in range(min(last + 1, len(inputs))):
        g.press(set(inputs[f]))
        g.checked_step(1)
        if f >= first:
            rec.frame(g, f)


def warp_case(g, rec, stage, target, count):
    cv.start_stage(g, stage)
    area = 0

    def idle(n, buttons):
        g.press(buttons)
        for _ in range(n):
            g.write(0xead, bytes([16]))
            g.checked_step(1)

    def exit_onto_ryu():
        r = g.read(0xe9f, 1)[0]
        box = g.read(0xeb5, 6)
        g.write(0xe87, bytes([r]))
        g.write(0xe81, bytes([(box[0] + box[3]) // 2, (box[2] + box[5]) // 2]))

    while True:
        idle(60, set())
        idle(120, {'right'})
        exit_onto_ryu()
        if area == target:
            break
        for _ in range(240):
            g.write(0xead, bytes([16]))
            g.checked_step(1)
            ram = g.read(0x240, 1) + g.read(0xe5f, 2)
            if ram[1] != stage or ram[0] or ram[2] != area:
                break
        if ram[1] != stage or ram[0] or ram[2] == area:
            raise RuntimeError(f'area {target} of stage {stage} not reached (area {area})')
        area = ram[2]
    g.press(set())
    for n in range(count):
        g.write(0xead, bytes([16]))
        g.checked_step(1)
        rec.frame(g, n)


def main():
    rom, out, tag, flags = sys.argv[1], Path(sys.argv[2]), sys.argv[3], int(sys.argv[4], 0)
    out.mkdir(parents=True, exist_ok=True)
    for case in sys.argv[5:]:
        kind, *a = case.split(':')
        rec = Recorder(out, tag, case)
        with Session(rom, flags) as g:
            g.write(0x1227, b'\x01')
            if kind == 'load':
                load_case(g, rec, int(a[0]), int(a[1]))
            elif kind == 'run':
                run_case(g, rec, a[0], int(a[1]), int(a[2]))
            else:
                warp_case(g, rec, int(a[0]), int(a[1]), int(a[2]))
        rec.close()


if __name__ == '__main__':
    main()
