"""Read fades.py traces of two builds (tags old-<mode>, new-<mode>) and
report the fade steps side by side (research reference, not a maintained
tool; needs Pillow for the sheets).

A fade step is a gameplay frame ($2240 = 0) within 40 frames of a black
picture whose picture got lighter or darker than the frame before it in
more than MIN % of the playfield. For each case and mode the
steps are listed with, per build: mean L* of the playfield, the share that
is not black, the share that got lighter and darker (by more than 1 L*) and
how many frames the picture then holds. A step against the fade's direction
(pixels getting lighter in a fade-out, darker in a fade-in) is marked '<<'.
With SHEETS, a strip per case and mode of the steps' pictures, the old build
above the new one.
usage: fadereport.py FADES [SHEETS] [--min PERCENT] [--case NAME] [--mode MODE]"""
import json
import sys
from pathlib import Path

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opt = {sys.argv[i][2:]: sys.argv[i + 1] for i in range(1, len(sys.argv) - 1) if sys.argv[i].startswith('--')}
for v in opt.values():
    args.remove(v)
fades = Path(args[0])
sheets = Path(args[1]) if len(args) > 1 else None
MIN = float(opt.get('min', 0.5))
CASES = [c for c in ('load-8-60', 'run-4-1-2400-2547', 'load-17-60', 'warp-17-4-240') if opt.get('case', c) == c]
TITLE = {'load-8-60': '4-1 stage start (Level Select entry, frames from the hook)',
         'run-4-1-2400-2547': '4-1 end of stage (stored run)',
         'load-17-60': '6-2 stage start (Level Select entry, frames from the hook)',
         'warp-17-4-240': '6-2 end of stage (area 4 exit to 6-3; frames from the exit)'}


def load(tag, mode, case):
    p = fades / f'{tag}-{mode}-{case}.json'
    return {r['f']: r for r in json.loads(p.read_text())} if p.exists() else None


def steps(trace):
    return [f for f, r in trace.items() if r.get('lighter', 0) > MIN or r.get('darker', 0) > MIN]


def hold(trace, f):
    n = 1
    while f + n in trace and trace[f + n].get('lighter', 0) <= MIN and trace[f + n].get('darker', 0) <= MIN:
        n += 1
    return n


def direction(trace, f):
    """-1 in a fade-out (the picture is black within 40 frames), +1 in a
    fade-in (it was black within the last 40 frames), else 0."""
    after = [trace[g]['nonblack'] for g in range(f, f + 41) if g in trace]
    before = [trace[g]['nonblack'] for g in range(f - 40, f) if g in trace]
    if after and min(after) < 0.05 and trace[f]['nonblack'] >= 0.05:
        return -1
    if after and min(after) < 0.05:
        return -1 if trace[f]['darker'] >= trace[f]['lighter'] else 1
    if before and min(before) < 0.05:
        return 1
    return 0


for mode in ('sms', 'hell'):
    if opt.get('mode', mode) != mode:
        continue
    for case in CASES:
        old, new = load('old', mode, case), load('new', mode, case)
        if not old or not new:
            print(f'\n== {mode} {case}: missing trace')
            continue
        frames = [f for f in sorted(set(steps(old)) | set(steps(new)))
                  if new[f]['master'] == 0 and (direction(new, f) or direction(old, f))]
        print(f'\n== {mode.upper()} {TITLE[case]}: {len(new)} frames; steps (old | new): mean L*, % not black, '
              f'% lighter (by L*), % darker, frames held')
        against = {'old': [], 'new': []}
        for f in frames:
            cells = []
            for tag, t in (('old', old), ('new', new)):
                r = t[f]
                d = direction(t, f)
                wrong = (d < 0 and r.get('lighter', 0) > MIN) or (d > 0 and r.get('darker', 0) > MIN)
                if wrong:
                    share = r['lighter'] if d < 0 else r['darker']
                    against[tag].append((f, share, r.get('lighter_by' if d < 0 else 'darker_by', 0), hold(t, f)))
                cells.append(f"L {r['meanL']:5.1f} nb {r['nonblack']:5.1f} +{r.get('lighter', 0):5.1f} "
                             f"({r.get('lighter_by', 0):4.1f}) -{r.get('darker', 0):5.1f} hold {hold(t, f):3d}"
                             f"{' <<' if wrong else '   '}")
            print(f'  f{f:5d} {"out" if direction(new, f) < 0 else "in " if direction(new, f) > 0 else "   "} '
                  + ' | '.join(cells))
        for tag in ('old', 'new'):
            print(f'  {tag}: steps against the fade: ' +
                  (', '.join(f'f{f} {s:.1f}% of the playfield by {by:.0f} L* for {h} frames' for f, s, by, h in against[tag])
                   or 'none'))
        if sheets:
            from PIL import Image, ImageDraw
            sheets.mkdir(parents=True, exist_ok=True)
            # The steps near black (a Level Select load: from its fade-out's
            # last steps on; before that the seed's 1-1 scene is torn down).
            black = min([f for f, r in new.items() if r['nonblack'] < 0.05] or [0])
            keep = [f for f in frames if min(new[f]['meanL'], old[f]['meanL']) < 12 and
                    (not case.startswith('load') or f >= black - 3)][:14]
            if not keep:
                continue
            first = keep[0] - 1 if keep[0] - 1 in new else keep[0]
            cols = [first] + keep if first != keep[0] else keep
            W, H = 256, 224
            im = Image.new('RGB', (len(cols) * (W + 2), 2 * (H + 12)), (40, 40, 40))
            d = ImageDraw.Draw(im)
            for row, tag in enumerate(('old', 'new')):
                for k, f in enumerate(cols):
                    g = f
                    while g >= min(new) and not (fades / f'{tag}-{mode}-{case}-f{g:05d}.png').exists():
                        g -= 1
                    p = fades / f'{tag}-{mode}-{case}-f{g:05d}.png'
                    if p.exists():
                        im.paste(Image.open(p).convert('RGB').crop((0, 18, 256, 242)), (k * (W + 2), row * (H + 12) + 12))
                    d.text((k * (W + 2) + 2, row * (H + 12)), f'{"hell-1-1" if tag == "old" else "dark lift"} f{f}',
                           fill=(255, 255, 0))
            im.save(sheets / f'fade-{mode}-{case}.png')
