#!/usr/bin/env python3
"""Choose a backdrop loop made only of original columns (development tool).

The loop keeps native columns 0..K in order (what round starts show), then
appends bridge columns and wraps to column 0. Its cost is the number of
16x8-pixel windows (one per pixel offset, per tile row) that never occur in
the same row of the original picture (columns 0-33), the same test as the
emulator review. Windows are compared by colour, so palettes do not matter.
The search is exact over the window cost (a shortest path over the last two
columns) and breaks ties by loop length.

  python3 scripts/native_seams.py --rom ORIGINAL.pce [--max-length 64] [profile ...]
"""
import argparse
import heapq
from pathlib import Path

import native_gfx as N


def colour_rows(backdrop, word):
    pal, px = backdrop.cell(word)
    return tuple(tuple(backdrop.colour(pal, v) for v in line) for line in px)


class Windows:
    def __init__(self, backdrop, rows):
        self.backdrop, self.rows = backdrop, rows
        self.cells = [[colour_rows(backdrop, backdrop.rows[r][c]) for c in range(34)] for r in rows]
        self.native = []
        for i, r in enumerate(rows):
            strip = [sum((cell[y] for cell in self.cells[i]), ()) for y in range(8)]
            self.native.append({tuple(line[x:x + 16] for line in strip) for x in range(len(strip[0]) - 15)})
        self.memo = {}

    def starting_in(self, p, a, b):
        """Windows that start in cell p (followed by a, b) and are not native."""
        key = (p, a, b)
        if key not in self.memo:
            bad = 0
            for i in range(len(self.rows)):
                cp, ca, cb = self.cells[i][p], self.cells[i][a], self.cells[i][b]
                strip = [cp[y] + ca[y] + cb[y] for y in range(8)]
                for q in range(8):
                    if tuple(line[q:q + 16] for line in strip) not in self.native[i]:
                        bad += 1
            self.memo[key] = bad
        return self.memo[key]

    def cost(self, sequence):
        n = len(sequence)
        return sum(self.starting_in(sequence[i], sequence[(i + 1) % n], sequence[(i + 2) % n]) for i in range(n))


def search(windows, keep, max_length=64, max_pairs=None):
    """Best loop: list(range(keep + 1)) + bridge, then wrap to 0."""
    prefix = list(range(keep + 1))
    base = sum(windows.starting_in(prefix[i], prefix[i + 1], prefix[i + 2]) for i in range(len(prefix) - 2))
    best = None
    heap = [(base, 0, (keep - 1, keep), ())]
    seen = {}
    while heap:
        cost, length, (p, a), bridge = heapq.heappop(heap)
        if best is not None and cost >= best[0]:
            break
        if seen.get((p, a, length), 1 << 30) <= cost:
            continue
        seen[p, a, length] = cost
        # close: ... p, a, 0, 1
        total = cost + windows.starting_in(p, a, 0) + windows.starting_in(a, 0, 1)
        sequence = prefix + list(bridge)
        if best is None or (total, len(sequence)) < (best[0], len(best[1])):
            if max_pairs is None or max_pairs(sequence):
                best = (total, sequence)
        if len(prefix) + length + 1 > max_length:
            continue
        for b in range(1, 34):
            heapq.heappush(heap, (cost + windows.starting_in(p, a, b), length + 1, (a, b), bridge + (b,)))
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rom', type=Path, required=True)
    ap.add_argument('--max-length', type=int, default=64)
    ap.add_argument('profiles', type=int, nargs='*', default=list(range(9)))
    args = ap.parse_args()
    data = args.rom.read_bytes()
    rom = data[512:] if len(data) % 0x2000 == 512 else data
    for profile in args.profiles:
        backdrop = N.Backdrop(rom, profile)
        keep = N.ROUND_START_COLUMNS[profile]
        rows = list(range(N.CASTLE_SKY_ROWS, backdrop.height)) if profile == 7 else list(range(backdrop.height))
        windows = Windows(backdrop, rows)
        current = windows.cost(N.LOOPS[profile])
        cost, sequence = search(windows, keep, args.max_length)
        print(f'{backdrop.name}: keep 0-{keep}; current loop {len(N.LOOPS[profile])} cols, {current} '
              f'non-native windows; best {len(sequence)} cols, {cost}: bridge {sequence[keep + 1:]}', flush=True)


if __name__ == '__main__':
    main()
