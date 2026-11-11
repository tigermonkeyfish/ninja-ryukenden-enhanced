"""Diagnosis for identity.py: replay one stored run on two ROMs (same
flags) and, for frames FIRST..LAST, print which parts differ: the picture
(pixel count), the VCE entries, the SAT, VRAM, and the RAM addresses (dead
stack below S excluded, S itself printed).
usage: framediff.py BASE_ROM CANDIDATE_ROM FLAGS RUN FIRST LAST [SHOTS_DIR]"""
import sys

from pathlib import Path

from ntools import Session, cv, load_run


def capture(rom, run, flags, first, last):
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
    out = {}
    with Session(rom, flags) as g:
        cv.start_stage(g, run['stage'])
        for f, buttons in enumerate(inputs[:last + 1]):
            g.press(set(buttons))
            g.checked_step(1)
            if f >= first:
                s = int(g.call('get_huc6280_status')['S'], 16)
                ram = bytearray(g.read(0, 0x2000))
                ram[0x100:0x100 + s + 1] = bytes(s + 1)
                out[f] = {'png': g.screenshot(), 'ram': bytes(ram), 's': s, 'sat': g.read(0, 512, area=6),
                          'vce': g.read(0, 1024, area=8), 'vram': g.read(0, 0x10000, area=4)}
    return out


def main():
    base, cand, flags, name, first, last = sys.argv[1], sys.argv[2], int(sys.argv[3], 0), sys.argv[4], \
        int(sys.argv[5]), int(sys.argv[6])
    run = load_run(name)
    a = capture(base, run, flags, first, last)
    b = capture(cand, run, flags, first, last)
    for f in sorted(a):
        x, y = a[f], b[f]
        parts = []
        if x['png'] != y['png']:
            import io
            from PIL import Image
            pa = list(Image.open(io.BytesIO(x['png'])).convert('RGB').getdata())
            pb = list(Image.open(io.BytesIO(y['png'])).convert('RGB').getdata())
            px = [i for i in range(len(pa)) if pa[i] != pb[i]]
            rows = sorted({i // 256 for i in px})
            if len(sys.argv) > 7:           # SHOTS_DIR: keep both pictures
                d = Path(sys.argv[7])
                d.mkdir(parents=True, exist_ok=True)
                (d / f'{name}-{f}-base.png').write_bytes(x['png'])
                (d / f'{name}-{f}-candidate.png').write_bytes(y['png'])
            parts.append(f'picture: {len(px)} pixels on screenshot rows {rows[:6]}')
        if x['s'] != y['s']:
            parts.append(f'S {x["s"]:02x}/{y["s"]:02x}')
        ram = [i for i in range(0x2000) if x['ram'][i] != y['ram'][i]]
        if ram:
            parts.append('RAM ' + ' '.join(f'{0x2000 + i:04X}:{x["ram"][i]:02x}/{y["ram"][i]:02x}' for i in ram[:16]))
        vce = [i // 2 for i in range(0, 1024, 2) if x['vce'][i:i + 2] != y['vce'][i:i + 2]]
        if vce:
            parts.append(f'VCE {len(vce)} entries {vce[:8]}')
        if x['sat'] != y['sat']:
            parts.append('SAT')
        vram = [i // 2 for i in range(0, 0x10000, 2) if x['vram'][i:i + 2] != y['vram'][i:i + 2]]
        if vram:
            parts.append(f'VRAM {len(vram)} words from ${vram[0]:04X}')
        print(f, '; '.join(parts) or 'same', flush=True)


if __name__ == '__main__':
    main()
