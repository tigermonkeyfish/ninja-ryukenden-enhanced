#!/usr/bin/env python3
"""Decode a stage's collision rectangles from the ROM and draw each area.

Emulator-free decoder (research tool). Found with a CPU trace of one game
frame in 2-1 (headless Geargrafx): bank 1 $9299 maps bank 7 at $6000 and calls
$6000, which tests Ryu's box against rectangles:
  bank 7 $62F2 + 2*stage  -> stage table (stage = $2E5F, Level Select index)
  stage table + 2*area    -> page table (area = $2E60)
  page table + 2*page     -> 5-byte records [type, x0, y0, x1, y1] until $FF
                             (x within the 256-px page = high byte of Ryu x)
Types seen: 00 floor/platform top, 01 girder/platform, 02 wall (Ryu clings),
03 solid block, 13 door: touching it changes area (the exits, and the doors
back). Coordinates are Ryu's: y is his feet, 192 the bottom of the playfield.
Reads the ROM given (default: the ROM under test); prints nothing of the ROM
except coordinates.
"""
import argparse
from pathlib import Path

ROM = Path('/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 2).pce')
NAMES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2', '4-3', '4-4', '5-1', '5-2', '5-3',
         '5-4', '6-1', '6-2', '6-3', '6-4A', '6-4B', '6-4C']
CHAR = {0x00: '=', 0x01: '-', 0x02: '|', 0x03: '#', 0x13: 'D'}


def load(rom=ROM):
    data = Path(rom).read_bytes()
    if len(data) % 8192 == 512:
        data = data[512:]
    return data[7 * 0x2000:8 * 0x2000]


def decode(b7, stage, pages_hint=None):
    b = lambda a: b7[a - 0x6000]
    w = lambda a: b(a) | b(a + 1) << 8
    st = w(0x62F2 + 2 * stage)
    first = w(st)
    na = (first - st) // 2 if st < first < st + 32 else 1
    areas = []
    for a in range(na):
        pt = w(st + 2 * a)
        np_ = (w(pt) - pt) // 2
        if not 0 < np_ <= 16:
            np_ = pages_hint or 1
        rects = []
        for pg in range(np_):
            r = w(pt + 2 * pg)
            while b(r) != 0xFF and len(rects) < 400:
                t, x0, y0, x1, y1 = (b(r + i) for i in range(5))
                rects.append((t, pg * 256 + x0, y0, pg * 256 + x1, y1))
                r += 5
        areas.append({'pages': np_, 'rects': rects})
    return areas


def draw(area, cell=8):
    W = area['pages'] * 256 // cell
    H = 200 // cell
    grid = [[' '] * W for _ in range(H)]
    order = sorted(area['rects'], key=lambda r: r[0] == 0x13)
    for t, x0, y0, x1, y1 in order:
        ch = CHAR.get(t, '?')
        for gy in range(y0 // cell, min(H, (y1 + cell - 1) // cell)):
            for gx in range(x0 // cell, min(W, (x1 + cell - 1) // cell)):
                if t in (0, 1) and gy != y0 // cell:
                    continue          # platforms: top edge only
                grid[gy][gx] = ch
    lines = []
    for gy in range(H):
        lines.append(f'{gy * cell:3d} ' + ''.join(grid[gy]))
    ruler = '    ' + ''.join(str((gx * cell // 256) % 10) if gx * cell % 256 == 0 else
                             ('.' if gx * cell % 64 == 0 else ' ') for gx in range(W))
    return '\n'.join([ruler] + lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=NAMES)
    ap.add_argument('--rom', default=ROM)
    ap.add_argument('--rects', action='store_true')
    ap.add_argument('--cell', type=int, default=8)
    a = ap.parse_args()
    for i, area in enumerate(decode(load(a.rom), NAMES.index(a.stage))):
        print(f'== {a.stage} area {i}: {area["pages"]} pages')
        doors = [r for r in area['rects'] if r[0] == 0x13]
        print('doors (type 13):', ' '.join(f'x{r[1]}-{r[3]} y{r[2]}-{r[4]}' for r in doors))
        if a.rects:
            print(' '.join(f'[{t:02x} x{x0}-{x1} y{y0}-{y1}]' for t, x0, y0, x1, y1 in area['rects']))
        print(draw(area, a.cell))


if __name__ == '__main__':
    main()
