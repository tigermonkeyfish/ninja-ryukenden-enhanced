#!/usr/bin/env python3
"""Per-area background composition report (native vs Enhanced).

For every area with background-changed cells, rows are stitched from the forward
sweep. Each Enhanced texture column is mapped to the native column it
reproduces (8-pixel window match). Reported per row: speed, repeat period,
composition segments, unmatched ("new") columns with their edited pixel counts,
native columns never shown, and cross-row shear (adjacent rows reproducing
different native columns at the same position).
"""
import json
import sys
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import stitch  # noqa: E402
from analyze import R, ROWS  # noqa: E402
from core import png_encode  # noqa: E402
from mapping import segments  # noqa: E402

OUT = R / 'report'


def edited_pixels(pe, pn, segs):
    """For 'new' spans, pixels differing from the native column implied by a neighbour."""
    total = 0
    detail = []
    for i, (a, b, d) in enumerate(segs):
        if d != 'new':
            continue
        cands = [s[2] for s in (segs[i - 1] if i else None, segs[i + 1] if i + 1 < len(segs) else None)
                 if s and isinstance(s[2], int)]
        best = None
        for delta in cands:
            diff = 0
            for u in range(a, b):
                v = (u + delta)
                if 0 <= v < len(pn) and pn[v] is not None and pe[u] is not None:
                    diff += sum(1 for y in range(8) if pe[u][y] != pn[v][y])
                else:
                    diff += 8
            if best is None or diff < best[0]:
                best = (diff, delta)
        px = best[0] if best else 8 * (b - a)
        total += px
        detail.append({'span': [a, b], 'pixels_differing': px,
                       'reference_delta': best[1] if best else None})
    return total, detail


def delta_map(segs, n):
    m = [None] * n
    for a, b, d in segs:
        if isinstance(d, int):
            for u in range(a, b):
                m[u] = d
    return m


def mark_image(data_rows, out, scale=2):
    """data_rows: list of (pano, marks) per BAT row; marks = set of u to outline."""
    W = max(len(p) for p, _ in data_rows) if data_rows else 1
    img = []
    for pano, marks in data_rows:
        if pano == 'sep':
            img.extend([[(255, 255, 255)] * W] * 2)
            continue
        for y in range(8):
            line = []
            for u in range(W):
                c = pano[u] if u < len(pano) else None
                if c is None:
                    line.append((70, 70, 70) if (u // 4 + y // 4) % 2 else (40, 40, 40))
                else:
                    p = c[y]
                    if u in marks and y in (0, 7):
                        p = (255, 0, 255)
                    line.append(p)
            img.append(line)
    big = []
    for line in img:
        l2 = [p for p in line for _ in range(scale)]
        big.extend([l2] * scale)
    Path(out).write_bytes(png_encode(big))


def area_report(job):
    stage, sub = job
    data = stitch.collect(stage, sub, ('fwd',))
    if not data:
        return None
    rows = [r for r in range(ROWS) if any(any(s['flags'][r]) for s in data)]
    res = {'stage': stage, 'subarea': sub, 'samples': len(data),
           'camera_range': [data[0]['camera'], data[-1]['camera']], 'rows': {}}
    if not rows:
        res['identical'] = True
        return res
    cam_total = data[-1]['camera'] - data[0]['camera']
    native_imgs, enh_imgs = [], []
    dmaps = {}
    for r in rows:
        on = stitch.stitch(data, 'orig', r)
        oe = stitch.stitch(data, 'enh', r)
        pn, pe = on[1], oe[1]
        segs = segments(pe, pn) if pe and pn else []
        new_cols = sum(b - a for a, b, d in segs if d == 'new')
        px, detail = edited_pixels(pe, pn, segs)
        used = set()
        for a, b, d in segs:
            if isinstance(d, int):
                used.update(range(a + d, b + d))
        known_native = {v for v, c in enumerate(pn) if c is not None}
        never = sorted(known_native - used)
        dmaps[r] = delta_map(segs, len(pe))
        period = stitch.period(pe) if pe else None
        res['rows'][r] = {
            'native': {'shift_total': on[0][-1], 'speed': on[0][-1] / cam_total if cam_total else None,
                       'len': len(pn), 'unresolved_steps': sum(1 for s, v in on[2] if s is None)},
            'enhanced': {'shift_total': oe[0][-1], 'speed': oe[0][-1] / cam_total if cam_total else None,
                         'len': len(pe), 'period': period[0] if period else None,
                         'unresolved_steps': sum(1 for s, v in oe[2] if s is None)},
            'segments': [[a, b, d] for a, b, d in segs],
            'new_columns': new_cols, 'edited_pixels': px, 'edits': detail,
            'native_columns_known': len(known_native), 'native_columns_never_shown': len(never),
            'never_shown_ranges': ranges(never),
        }
        native_imgs.append((pn, set()))
        marks = set()
        for a, b, d in segs:
            if d == 'new':
                marks.update(range(a, b))
        enh_imgs.append((pe, marks))
    # Shear between adjacent changed rows that move at the same Enhanced speed.
    shear = []
    for r1, r2 in zip(rows, rows[1:]):
        if r2 != r1 + 1:
            continue
        s1 = res['rows'][r1]['enhanced']['shift_total']
        s2 = res['rows'][r2]['enhanced']['shift_total']
        if abs(s1 - s2) > 8:
            shear.append({'rows': [r1, r2], 'note': 'different speeds', 'shift_totals': [s1, s2]})
            continue
        m1, m2 = dmaps[r1], dmaps[r2]
        spans, cur = [], None
        for u in range(min(len(m1), len(m2))):
            bad = (m1[u] is not None and m2[u] is not None and m1[u] != m2[u]
                   and (m1[u] - m2[u]) % (res['rows'][r1]['enhanced']['period'] or 10**6) != 0)
            if bad and cur is None:
                cur = [u, u + 1, m1[u] - m2[u]]
            elif bad:
                cur[1] = u + 1
            elif cur:
                spans.append(cur)
                cur = None
        if cur:
            spans.append(cur)
        if spans:
            shear.append({'rows': [r1, r2], 'spans': spans})
    res['shear'] = shear
    OUT.mkdir(parents=True, exist_ok=True)
    mark_image(native_imgs + [('sep', None)] + enh_imgs,
               OUT / f'pano-{stage}-a{sub}.png')
    res['image'] = f'pano-{stage}-a{sub}.png'
    res['rows_list'] = rows
    return res


def ranges(vals):
    out, start, prev = [], None, None
    for v in vals:
        if start is None:
            start = prev = v
        elif v == prev + 1:
            prev = v
        else:
            out.append([start, prev + 1])
            start = prev = v
    if start is not None:
        out.append([start, prev + 1])
    return out


if __name__ == '__main__':
    jobs = []
    for d in sorted((R / 'orig').iterdir()):
        if not (d / 'run.json').exists() or (len(sys.argv) > 1 and d.name not in sys.argv[1:]):
            continue
        run = json.loads((d / 'run.json').read_text())
        for a in run['areas']:
            jobs.append((d.name, a['subarea']))
    results = []
    with Pool(8) as pool:
        for res in pool.imap_unordered(area_report, jobs):
            if res is None:
                continue
            results.append(res)
            summ = {r: (v['enhanced']['period'], v['new_columns'], v['edited_pixels'],
                        v['native_columns_never_shown']) for r, v in res['rows'].items()}
            print(res['stage'], res['subarea'], 'identical' if res.get('identical') else summ,
                  'shear' if res.get('shear') else '', flush=True)
    results.sort(key=lambda r: (r['stage'], r['subarea']))
    OUT.mkdir(parents=True, exist_ok=True)
    name = 'composition.json' if len(sys.argv) == 1 else f'composition-{"_".join(sys.argv[1:])}.json'
    (OUT / name).write_text(json.dumps(results, indent=1) + '\n')
