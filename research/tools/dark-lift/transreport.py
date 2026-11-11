"""Read trans.py traces and report, per transition, the frames in which the
Original mode's playfield is black and a mapped mode's is not (research
reference, not a maintained tool).

A transition is a span of gameplay frames ($2240 = 0) in which the Original
recording's playfield (screenshot rows 50-241) is entirely black. For the
same frames of a mapped mode's recording (same case, same frame numbers:
the probes' interventions and the gameplay are identical) the report gives:
  tail   frames from the span's start until the mode's playfield is first
         its black (the fade-out's last steps arriving late)
  flash  frames after that in which the playfield is not black again while
         the Original's still is, with the largest share of the playfield
         and the colours shown
  lit    VCE entries that are not the mode's black at the first frame of
         the span with the palette lock ($2283) set, and their colours: the
         fade-out left unfinished when a load begins
  play   'differs' if the gameplay hash differs from the Original's in any
         frame of the case
usage: transreport.py TRANS TAG[,TAG2] [--modes gb-dmg,hell,sms] [--all] [--json OUT]
TAG: the recordings TRANS/TAG-<mode>-<case>.json; with TAG2 its columns
follow TAG's for the same spans. Without --all only transitions with a
flash or lit entries (in any listed tag and mode) are listed; the totals
count all."""
import json
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = {}
for i, a in enumerate(sys.argv):
    if a.startswith('--'):
        nxt = sys.argv[i + 1] if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--') else ''
        opt[a[2:]] = nxt
        if nxt:
            args.remove(nxt)
trans, tags = Path(args[0]), args[1].split(',')
MODES = opt.get('modes', 'gb-dmg,hell,sms').split(',')
STAGES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2', '4-3',
          '4-4', '5-1', '5-2', '5-3', '5-4', '6-1', '6-2', '6-3', '6-4A', '6-4B', '6-4C']


def load(tag, mode, case):
    p = trans / f'{tag}-{mode}-{case}.json'
    return json.loads(p.read_text()) if p.exists() else None


def spans(orig):
    """[first, last] frame of each run of black gameplay frames."""
    out, start = [], None
    for r in orig:
        black = r['master'] == 0 and r['notblack'] == 0
        if black and start is None:
            start = r['f']
        if not black and start is not None:
            out.append((start, r['f'] - 1))
            start = None
    if start is not None:
        out.append((start, orig[-1]['f']))
    return out


def measure(rows, a, b):
    seg = [r for r in rows if a <= r['f'] <= b]
    tail = 0
    while tail < len(seg) and seg[tail]['notblack'] > 0:
        tail += 1
    flash = [r for r in seg[tail:] if r['notblack'] > 0]
    locked = next((r for r in seg if r['lock']), None)
    colours = {}
    for r in flash:
        for c, share in r['top']:
            colours[c] = max(colours.get(c, 0), share)
    return {'tail': tail, 'flash': len(flash),
            'flash_frames': [flash[0]['f'], flash[-1]['f']] if flash else None,
            'flash_share': max((r['notblack'] for r in flash), default=0),
            'flash_colours': sorted(colours, key=lambda c: -colours[c])[:4],
            'lit': locked['lit'] if locked else None,
            'lit_colours': locked['lit_colours'] if locked else [],
            'lit_first': locked['lit_first'][:12] if locked else []}


def name(case, orig, a):
    row = next(r for r in orig if r['f'] == a)
    before = next((r for r in reversed(orig) if r['f'] < a and r['notblack'] > 0), row)
    after = next((r for r in orig if r['f'] > a and r['notblack'] > 0), row)
    def place(r):
        return f"{STAGES[r['stage']] if r['stage'] < len(STAGES) else r['stage']}/{r['area']}"
    return f'{place(before)} > {place(after)}'


cases = sorted({p.name[len(tags[0]) + len('-original-'):-5] for p in trans.glob(f'{tags[0]}-original-*.json')},
               key=lambda c: (c.split('-')[0], [int(x) if x.isdigit() else x for x in c.split('-')[1:]]))
report, totals = [], {(t, m): {'spans': 0, 'flash': 0, 'flash_frames': 0, 'lit': 0, 'tail': 0, 'play': 0}
                      for t in tags for m in MODES}
for case in cases:
    orig = load(tags[0], 'original', case)
    sp = spans(orig)
    oplay = {r['f']: r['play'] for r in orig}
    for a, b in sp:
        entry = {'case': case, 'span': [a, b], 'what': name(case, orig, a), 'modes': {}}
        for tag in tags:
            for mode in MODES:
                rows = load(tag, mode, case)
                if rows is None:
                    continue
                m = measure(rows, a, b)
                entry['modes'][f'{tag}:{mode}'] = m
                t = totals[(tag, mode)]
                t['spans'] += 1
                t['flash'] += 1 if m['flash'] else 0
                t['flash_frames'] += m['flash']
                t['lit'] += 1 if m['lit'] else 0
                t['tail'] = max(t['tail'], m['tail'])
        report.append(entry)
    for tag in tags:
        for mode in MODES:
            rows = load(tag, mode, case)
            if rows is None:
                continue
            bad = [r['f'] for r in rows if oplay.get(r['f']) != r['play']]
            if len(rows) != len(orig) or bad:
                totals[(tag, mode)]['play'] += 1
                print(f'PLAY {tag} {mode} {case}: {len(rows)} frames against {len(orig)}; gameplay differs in '
                      f'{len(bad)} frames, first {bad[:5]}')

for e in report:
    shown = '--all' in sys.argv or any(m['flash'] or m['lit'] for m in e['modes'].values())
    if not shown:
        continue
    print(f"{e['case']:10s} frames {e['span'][0]}-{e['span'][1]} ({e['span'][1] - e['span'][0] + 1}) {e['what']}")
    for key, m in e['modes'].items():
        flash = (f"flash {m['flash']} frames {m['flash_frames'][0]}-{m['flash_frames'][1]}, up to {m['flash_share']:.2f}% "
                 f"{'/'.join(m['flash_colours'])}") if m['flash'] else 'no flash'
        lit = (f"lit at lock {m['lit']} ({'/'.join(m['lit_colours'][:5])}; entries {m['lit_first'][:8]})"
               if m['lit'] else ('lit at lock 0' if m['lit'] == 0 else 'no lock'))
        print(f"    {key:14s} tail {m['tail']:3d}  {flash}; {lit}")
print()
for (tag, mode), t in totals.items():
    print(f"TOTAL {tag:5s} {mode:7s}: {t['spans']} black spans; with a flash {t['flash']} ({t['flash_frames']} frames); "
          f"with entries lit at the lock {t['lit']}; longest tail {t['tail']}; cases with gameplay differing {t['play']}")
if opt.get('json'):
    Path(opt['json']).write_text(json.dumps({'report': report,
                                             'totals': {f'{t}:{m}': v for (t, m), v in totals.items()}}))
