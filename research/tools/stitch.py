#!/usr/bin/env python3
"""Per-row background speed, repeat period and stitched panoramas.

For one stage area and sweep pass, consecutive samples are aligned row by row
using background-changed pixels only (sprites never appear: layers are decoded
from VRAM). Offsets accumulate into texture coordinates; each texture column is
the majority over every sample that showed it.
"""
import json
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze import K, R, ROWS, load, runs, sample_rows  # noqa: E402
from core import png_encode  # noqa: E402

HOLE = None


def collect(stage, sub, kind):
    orun = json.loads((R / 'orig' / stage / 'run.json').read_text())
    erun = json.loads((R / 'enh' / stage / 'run.json').read_text())
    pairs = [(a, b) for a, b in zip(orun['samples'], erun['samples'])
             if a['subarea'] == sub and a['kind'] in kind]
    data = []
    for ro, re in pairs:
        rc = ro['render_camera']
        so = sample_rows(load('orig', stage, ro), rc)
        se = sample_rows(load('enh', stage, re), rc)
        flags = []
        for cy in range(ROWS):
            co, cells, wo = so[cy]
            ce, _, we = se[cy]
            changed = {cells[x] for x in range(256) if wo[x] != we[x]}
            flags.append([cells[x] in changed for x in range(256)])
        data.append({'camera': ro['camera'], 'name': ro['name'],
                     'orig': [r[0] for r in so], 'enh': [r[0] for r in se], 'flags': flags})
    return data


def shift_between(prev_cols, prev_flags, cols, flags):
    """Shift s with cols[x] == prev_cols[x + s] (texture moved by s pixels)."""
    index = defaultdict(list)
    for a, b in runs(prev_flags):
        hs = [hash(c) for c in prev_cols[a:b]]
        for i in range(0, b - a - K + 1):
            index[hash(tuple(hs[i:i + K]))].append(a + i)
    votes = Counter()
    for a, b in runs(flags):
        hs = [hash(c) for c in cols[a:b]]
        for i in range(0, b - a - K + 1):
            for xp in index.get(hash(tuple(hs[i:i + K])), ()):
                votes[xp - (a + i)] += 1
    return votes


KS = 8   # stitching window width


def _windows(cols, flags):
    out = []
    for a, b in runs(flags):
        hs = [hash(c) for c in cols[a:b]]
        for i in range(0, b - a - KS + 1):
            out.append((a + i, hash(tuple(hs[i:i + KS]))))
    return out


def stitch_group(data, which, rows, max_shift=24):
    """Jointly align a group of rows (one layer) against the panorama so far.

    Returns (offsets, {row: columns dict u -> Counter}, steps). steps[k] for
    k >= 1 is (offset or None, votes). Unresolved samples contribute nothing.
    """
    index = {r: defaultdict(set) for r in rows}
    columns = {r: defaultdict(Counter) for r in rows}
    offsets, steps, history = [], [], []
    anchored = False
    for k, smp in enumerate(data):
        cam = smp['camera']
        wins = {r: _windows(smp[which][r], smp['flags'][r]) for r in rows}
        visible = any(any(smp['flags'][r]) for r in rows)
        if len(history) >= 2:
            recent = history[-10:]
            slopes = sorted((b[1] - a[1]) / (b[0] - a[0]) for a, b in zip(recent, recent[1:])
                            if b[0] != a[0])
            slope = slopes[len(slopes) // 2] if slopes else 0.0
            slope = max(-1.0, min(1.0, slope))
            c1, o1 = history[-1]
            pred = o1 + slope * (cam - c1)
        elif history:
            pred = history[-1][1]
        else:
            pred = 0
        votes = Counter()
        for r in rows:
            idx = index[r]
            for x, h in wins[r]:
                for u in idx.get(h, ()):
                    o = u - x
                    if abs(o - pred) <= max_shift:
                        votes[o] += 1
        resolved = None
        if not anchored:
            if visible:
                resolved = 0
                anchored = True
        elif votes:
            top = max(votes.values())
            best = min((o for o, v in votes.items() if v == top), key=lambda o: abs(o - pred))
            if top >= 2 or abs(best - pred) <= 1:
                resolved = best
        if k:
            steps.append((resolved, votes[resolved] if resolved is not None else 0))
        o = resolved if resolved is not None else int(round(pred))
        offsets.append(o)
        if resolved is not None:
            history.append((cam, o))
            for r in rows:
                cols, flags = smp[which][r], smp['flags'][r]
                for x in range(256):
                    if flags[x]:
                        columns[r][x + o][cols[x]] += 1
                for x, h in wins[r]:
                    index[r][h].add(x + o)
    return offsets, columns, steps


def to_pano(cols, lo=None, hi=None):
    if not cols:
        return [], 0
    lo = min(cols) if lo is None else lo
    hi = max(cols) if hi is None else hi
    return [cols[u].most_common(1)[0][0] if u in cols else HOLE for u in range(lo, hi + 1)], lo


def stitch(data, which, row, max_shift=24):
    """Single-row wrapper: (offsets, panorama, steps, lo)."""
    offsets, columns, steps = stitch_group(data, which, [row], max_shift)
    pano, lo = to_pano(columns[row])
    return offsets, pano, steps, lo


def period(pano, min_p=16):
    """Smallest P where known columns repeat after P pixels (>=98% agreement)."""
    n = len(pano)
    best = None
    for p in range(min_p, n // 2 + 1):
        agree = total = 0
        for u in range(n - p):
            a, b = pano[u], pano[u + p]
            if a is HOLE or b is HOLE:
                continue
            total += 1
            agree += a == b
        if total > p and agree / total >= 0.98:
            best = (p, agree / total, total)
            break
    return best


def to_image(rows_pixels, width):
    """rows_pixels: list of panoramas (one per BAT row) -> RGB rows (8 lines each)."""
    out = []
    for pano in rows_pixels:
        for y in range(8):
            line = []
            for u in range(width):
                c = pano[u] if u < len(pano) else HOLE
                line.append(c[y] if c is not HOLE else ((u // 4 + y // 2) % 2 and (90, 90, 90) or (60, 60, 60)))
            out.append(line)
    return out


if __name__ == '__main__':
    stage, sub = sys.argv[1], int(sys.argv[2])
    kinds = tuple(sys.argv[3].split(',')) if len(sys.argv) > 3 else ('fwd',)
    data = collect(stage, sub, kinds)
    report = {}
    for row in range(ROWS):
        if not any(any(s['flags'][row]) for s in data):
            continue
        res = {}
        for which in ('orig', 'enh'):
            offs, pano, steps, lo = stitch(data, which, row)
            cams = [d['camera'] for d in data]
            dc = cams[-1] - cams[0]
            res[which] = {'offset_total': offs[-1], 'camera_total': dc,
                          'ratio': offs[-1] / dc if dc else None,
                          'pano_len': len(pano), 'holes': sum(1 for c in pano if c is HOLE),
                          'period': period(pano) if pano else None,
                          'unresolved_steps': sum(1 for s, v in steps if s is None)}
        report[row] = res
        print(row, json.dumps(res))
