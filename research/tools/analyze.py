#!/usr/bin/env python3
"""Shift-tolerant background fidelity analysis of matched original/Enhanced sweeps.

For each matched sample (same stage, area, camera), the visible playfield cells
(BAT rows 0-23, screen x 0-255) are decoded from VRAM for both ROMs (background
layer only, sprites excluded). A cell is "background-changed" when its BAT word
or decoded pixels differ between the two ROMs at the same camera; the foreground
and untouched rows are identical by construction and are checked separately.

Enhanced fidelity: every 16-pixel-wide, 8-pixel-tall window of Enhanced pixels
inside background-changed runs must occur somewhere in the native background of
the same tile row (collected over all native samples of the stage). Windows that
never occur in the native art are flagged and grouped into regions. Coverage is
the reverse: native windows never shown by Enhanced.

Screenshot checks: outside background-changed cells, Enhanced and native
screenshots must be pixel-identical (foreground, HUD and sprites untouched).
"""
import json
import sys
import zlib
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core import png_decode, png_encode  # noqa: E402
from vdc import Background  # noqa: E402

import os
import local
R = Path(os.environ.get('BGROOT', str(local.CAPTURES)))
ROWS = 24          # visible playfield BAT rows
SCREEN_Y0 = 50     # screen line of BAT row 0
K = 16             # window width in pixels


def load(which, stage, rec):
    d = R / which / stage / 'samples'
    n = rec['name']
    bg = Background(zlib.decompress((d / f'{n}.vram.z').read_bytes()),
                    (d / f'{n}.pal').read_bytes(), rec['mwr'])
    return bg


def sample_rows(bg, rcam):
    """Per visible row: list of 256 column tuples, plus per-x cell id and word."""
    out = []
    for cy in range(ROWS):
        cols, cells, wordl = [], [], []
        for x in range(256):
            bx = (rcam + x) % 512
            word = bg.cell_word(bx // 8, cy)
            px = bg.cell_pixels(word)
            cols.append(tuple(px[y][bx % 8] for y in range(8)))
            cells.append(bx // 8)
            wordl.append(word)
        out.append((cols, cells, wordl))
    return out


def runs(flags):
    res, start = [], None
    for x, f in enumerate(flags + [False]):
        if f and start is None:
            start = x
        elif not f and start is not None:
            res.append((start, x))
            start = None
    return res


def windows(cols, run):
    a, b = run
    hs = [hash(c) for c in cols[a:b]]
    return [(a + i, hash(tuple(hs[i:i + K]))) for i in range(0, b - a - K + 1)]


def analyze_stage(stage):
    orun = json.loads((R / 'orig' / stage / 'run.json').read_text())
    erun = json.loads((R / 'enh' / stage / 'run.json').read_text())
    pairs = list(zip(orun['samples'], erun['samples']))
    native = defaultdict(set)            # row -> window hashes (native art)
    enh_windows = []                     # (sample index, row, x, hash)
    enh_set = defaultdict(set)
    per_sample = []
    word_stats = Counter()
    for si, (ro, re) in enumerate(pairs):
        assert ro['name'] == re['name'] and ro['camera'] == re['camera'], (ro, re)
        assert ro['render_camera'] == re['render_camera']
        bo, be = load('orig', stage, ro), load('enh', stage, re)
        rc = ro['render_camera']
        so, se = sample_rows(bo, rc), sample_rows(be, rc)
        changed_cells = set()
        same_word_diff_px = set()
        for cy in range(ROWS):
            co, cello, wo = so[cy]
            ce, _, we = se[cy]
            cellflag = {}
            for x in range(256):
                c = cello[x]
                f = cellflag.get(c, False)
                if wo[x] != we[x] or co[x] != ce[x]:
                    f = True
                    if wo[x] == we[x]:
                        same_word_diff_px.add((c, cy))
                cellflag[c] = f
            flags = [cellflag[cello[x]] for x in range(256)]
            for c, f in cellflag.items():
                if f:
                    changed_cells.add((c, cy))
            for run in runs(flags):
                for x, h in windows(co, run):
                    native[cy].add(h)
                for x, h in windows(ce, run):
                    enh_windows.append((si, cy, x, h))
                    enh_set[cy].add(h)
            # word-level summary for changed cells
        for (c, cy) in changed_cells:
            word_stats['changed_cells'] += 1
        word_stats['same_word_diff_px'] += len(same_word_diff_px)
        per_sample.append({'name': ro['name'], 'camera': ro['camera'], 'render_camera': rc,
                           'subarea': ro['subarea'], 'changed_cells': sorted(changed_cells),
                           'same_word_diff_px': sorted(same_word_diff_px),
                           'pal_diff': [i for i in range(256)
                                        if bo.pal[i] != be.pal[i]],
                           'png_same': ro['png_sha256'] == re['png_sha256']})
    # Evaluate Enhanced windows against native art.
    fails = defaultdict(list)            # sample -> [(row, x)]
    total = Counter()
    for si, cy, x, h in enh_windows:
        total['windows'] += 1
        if h not in native[cy]:
            total['unmatched'] += 1
            fails[si].append((cy, x))
    coverage = {cy: (len(native[cy]), len(native[cy] - enh_set[cy])) for cy in native}
    # Screenshot integrity outside changed cells.
    shot_issues = []
    for si, (ro, re) in enumerate(pairs):
        ps = per_sample[si]
        if ps['png_same']:
            ps['shot_fg_diff'] = 0
            continue
        _, _, imo = png_decode((R / 'orig' / stage / 'samples' / f"{ro['name']}.png").read_bytes())
        _, _, ime = png_decode((R / 'enh' / stage / 'samples' / f"{re['name']}.png").read_bytes())
        changed = set(map(tuple, ps['changed_cells']))
        rc = ps['render_camera']
        bad = 0
        bad_px = []
        for sy in range(len(imo)):
            for x in range(256):
                if imo[sy][x] == ime[sy][x]:
                    continue
                cy = (sy - SCREEN_Y0) // 8
                if 0 <= cy < ROWS and sy >= SCREEN_Y0 and ((((rc + x) % 512) // 8, cy) in changed):
                    continue
                bad += 1
                if len(bad_px) < 50:
                    bad_px.append((x, sy))
        ps['shot_fg_diff'] = bad
        if bad:
            shot_issues.append({'name': ro['name'], 'pixels': bad, 'examples': bad_px})
    result = {
        'stage': stage, 'samples': len(pairs), 'K': K,
        'windows': total['windows'], 'unmatched': total['unmatched'],
        'match_rate': 1 - total['unmatched'] / total['windows'] if total['windows'] else None,
        'changed_cells_total': word_stats['changed_cells'],
        'same_word_diff_px_cells': word_stats['same_word_diff_px'],
        'coverage_by_row': {str(k): {'native_windows': v[0], 'never_shown': v[1]}
                            for k, v in sorted(coverage.items())},
        'rows_changed': sorted({cy for ps in per_sample for (_, cy) in ps['changed_cells']}),
        'fails': {pairs[si][0]['name']: v for si, v in fails.items()},
        'pal_diff_entries': sorted({i for ps in per_sample for i in ps['pal_diff']}),
        'shot_issues': shot_issues,
        'per_sample': [{k: v for k, v in ps.items() if k not in ('changed_cells',)}
                       | {'n_changed': len(ps['changed_cells'])} for ps in per_sample],
    }
    out = R / 'analysis'
    out.mkdir(exist_ok=True)
    (out / f'{stage}.json').write_text(json.dumps(result) + '\n')
    return {k: result[k] for k in ('stage', 'samples', 'windows', 'unmatched', 'match_rate',
                                   'same_word_diff_px_cells', 'rows_changed', 'pal_diff_entries')} | {
        'shot_issue_samples': len(shot_issues),
        'fail_samples': len(fails),
        'never_shown': sum(v[1] for v in coverage.values()),
        'native_windows': sum(v[0] for v in coverage.values())}


if __name__ == '__main__':
    stages = sys.argv[1:] or sorted(p.name for p in (R / 'orig').iterdir() if (p / 'run.json').exists())
    with Pool(min(len(stages), 8)) as pool:
        for res in pool.imap_unordered(analyze_stage, stages):
            print(json.dumps(res), flush=True)
