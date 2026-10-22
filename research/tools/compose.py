#!/usr/bin/env python3
"""Model-based background composition: native backdrop vs Enhanced texture.

Motion models were verified first (model.py): every Enhanced background row is
a fixed texture at offset floor(camera/8) (or stationary, for the 6-1 sky),
and the native backdrop is screen-locked apart from an 8-pixel jitter. Using
those models, each ROM's backdrop is reassembled from all forward and reverse
samples (background-changed cells only, decoded from VRAM, so sprites never
contaminate it). Every Enhanced texture column is then traced to the native
column it reproduces (8-pixel window match); unmatched columns are counted as
edited pixels against the neighbouring source alignment.
"""
import json
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import stitch  # noqa: E402
from analyze import R, ROWS  # noqa: E402
from core import png_encode  # noqa: E402
from mapping import segments  # noqa: E402
from report import edited_pixels, ranges  # noqa: E402

OUT = R / 'report'
HOLE = None


def agreement(data, which, row, offs):
    cols = defaultdict(Counter)
    for k, d in enumerate(data):
        f, c = d['flags'][row], d[which][row]
        for x in range(256):
            if f[x]:
                cols[x + offs[k]][c[x]] += 1
    tot = sum(sum(v.values()) for v in cols.values())
    agree = sum(v.most_common(1)[0][1] for v in cols.values())
    return (agree / tot if tot else None), cols


def native_offsets(data, rows, search=16):
    """Per-sample jitter of the screen-locked native backdrop (joint over rows)."""
    ref = max(range(len(data)), key=lambda k: sum(sum(data[k]['flags'][r]) for r in rows))
    refcols = {r: defaultdict(Counter) for r in rows}
    for r in rows:
        for x in range(256):
            if data[ref]['flags'][r][x]:
                refcols[r][x][data[ref]['orig'][r][x]] += 1
    offs = [None] * len(data)
    offs[ref] = 0
    order = sorted(range(len(data)), key=lambda k: -sum(sum(data[k]['flags'][r]) for r in rows))
    for k in order:
        if k == ref:
            continue
        best = None
        for s in range(-search, search + 1):
            a = t = 0
            for r in rows:
                rc = refcols[r]
                f, c = data[k]['flags'][r], data[k]['orig'][r]
                for x in range(256):
                    if f[x]:
                        cell = rc.get(x + s)
                        if cell:
                            t += 1
                            a += cell.most_common(1)[0][0] == c[x]
            if t >= 24:
                score = (a / t, -abs(s))
                if best is None or score > best[0]:
                    best = (score, s)
        if best and best[0][0] >= 0.9:
            s = best[1]
            offs[k] = s
            for r in rows:
                f, c = data[k]['flags'][r], data[k]['orig'][r]
                for x in range(256):
                    if f[x]:
                        refcols[r][x + s][c[x]] += 1
    return offs


def pano_from(cols):
    if not cols:
        return [], 0
    lo, hi = min(cols), max(cols)
    return [cols[u].most_common(1)[0][0] if u in cols else HOLE for u in range(lo, hi + 1)], lo


def compose(job):
    stage, sub = job
    data = stitch.collect(stage, sub, ('fwd', 'rev', 'entry', 'static'))
    rows = [r for r in range(ROWS) if any(any(d['flags'][r]) for d in data)]
    res = {'stage': stage, 'subarea': sub, 'samples': len(data), 'rows': {},
           'cameras': [min(d['camera'] for d in data), max(d['camera'] for d in data)]}
    if not rows:
        res['identical'] = True
        return res
    noffs = native_offsets(data, rows)
    res['native_jitter'] = dict(Counter(o for o in noffs if o is not None))
    res['native_unplaced'] = sum(1 for o in noffs if o is None)
    keep = [k for k, o in enumerate(noffs) if o is not None]
    nd = [data[k] for k in keep]
    no = [noffs[k] for k in keep]
    models = {'scroll_1_8': [d['camera'] // 8 for d in data], 'stationary': [0] * len(data)}
    images = {'orig': [], 'enh': []}
    for r in rows:
        na, ncols = agreement(nd, 'orig', r, no)
        choices = {m: agreement(data, 'enh', r, o) for m, o in models.items()}
        model = max(choices, key=lambda m: choices[m][0] or 0)
        ea, ecols = choices[model]
        pn, nlo = pano_from(ncols)
        pe, elo = pano_from(ecols)
        period = stitch.period(pe) if pe else None
        segs = segments(pe, pn) if pe and pn else []
        px, detail = edited_pixels(pe, pn, segs)
        used = set()
        for a, b, d in segs:
            if isinstance(d, int):
                used.update(range(a + d, b + d))
        known = {v for v, c in enumerate(pn) if c is not HOLE}
        never = sorted(known - used)
        res['rows'][r] = {
            'enhanced_model': model, 'enhanced_agreement': round(ea, 4) if ea else None,
            'native_agreement': round(na, 4) if na else None,
            'native_len': len(pn), 'native_holes': sum(1 for c in pn if c is HOLE),
            'enhanced_len': len(pe), 'enhanced_holes': sum(1 for c in pe if c is HOLE),
            'enhanced_period': period[0] if period else None,
            'segments': [[a, b, d] for a, b, d in segs],
            'new_columns': sum(b - a for a, b, d in segs if d == 'new'),
            'edited_pixels': px, 'edits': detail,
            'native_columns_known': len(known), 'native_columns_never_shown': len(never),
            'never_shown_ranges': ranges(never),
        }
        marks = set()
        for a, b, d in segs:
            if d == 'new':
                marks.update(range(a, b))
        images['orig'].append((pn, nlo, set()))
        images['enh'].append((pe, elo, marks))
    OUT.mkdir(parents=True, exist_ok=True)
    name = f'compose-{stage}-a{sub}.png'
    draw(images, OUT / name)
    res['image'] = name
    return res


def draw(images, path, scale=2):
    """Stack native rows, a separator, then Enhanced rows; rows keep their own origin."""
    def block(entries):
        lo = min((e[1] for e in entries if e[0]), default=0)
        width = max((e[1] - lo + len(e[0]) for e in entries if e[0]), default=1)
        out = []
        for pano, plo, marks in entries:
            for y in range(8):
                line = []
                for u in range(width):
                    i = u - (plo - lo)
                    c = pano[i] if 0 <= i < len(pano) else HOLE
                    if c is HOLE:
                        line.append((70, 70, 70) if (u // 4 + y // 4) % 2 else (40, 40, 40))
                    else:
                        p = c[y]
                        if i in marks and y in (0, 7):
                            p = (255, 0, 255)
                        line.append(p)
                out.append(line)
        return out
    a, b = block(images['orig']), block(images['enh'])
    W = max(len(a[0]), len(b[0]))
    pad = lambda rows: [r + [(30, 30, 30)] * (W - len(r)) for r in rows]
    img = pad(a) + [[(255, 255, 255)] * W] * 3 + pad(b)
    big = []
    for line in img:
        l2 = [p for p in line for _ in range(scale)]
        big.extend([l2] * scale)
    path.write_bytes(png_encode(big))


if __name__ == '__main__':
    jobs = []
    for d in sorted((R / 'orig').iterdir()):
        if not (d / 'run.json').exists() or (len(sys.argv) > 1 and d.name not in sys.argv[1:]):
            continue
        for a in json.loads((d / 'run.json').read_text())['areas']:
            jobs.append((d.name, a['subarea']))
    results = []
    with Pool(8) as pool:
        for res in pool.imap_unordered(compose, jobs):
            results.append(res)
            if res.get('identical'):
                print(res['stage'], res['subarea'], 'identical', flush=True)
                continue
            s = {r: (v['enhanced_model'][:6], v['enhanced_agreement'], v['native_agreement'],
                     v['enhanced_period'], v['new_columns'], v['edited_pixels'],
                     v['native_columns_never_shown']) for r, v in res['rows'].items()}
            print(res['stage'], res['subarea'], 'jitter', res['native_jitter'],
                  'unplaced', res['native_unplaced'], flush=True)
            for r, v in s.items():
                print('   ', r, v, flush=True)
    results.sort(key=lambda r: (r['stage'], r['subarea']))
    suffix = '' if len(sys.argv) == 1 else '-' + '_'.join(sys.argv[1:])
    (OUT / f'compose{suffix}.json').write_text(json.dumps(results, indent=1) + '\n')
