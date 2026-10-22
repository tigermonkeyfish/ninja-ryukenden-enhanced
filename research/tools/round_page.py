"""Round-start page: original vs current build at every round's first frame."""
import json, re, sys
from pathlib import Path
from core import png_decode, png_encode
import local
REPORT = local.CAPTURES / 'report'
SRC = Path(sys.argv[1])          # capture set with orig/ and enh/
ROM_LABEL = sys.argv[2]
NAMES = {'00-1-1': '1-1', '03-2-2': '2-2', '05-3-1': '3-1', '06-3-2': '3-2', '08-4-1': '4-1', '09-4-2': '4-2',
         '13-5-2': '5-2', '14-5-3': '5-3', '15-5-4': '5-4', '16-6-1': '6-1', '18-6-3': '6-3'}
NOTES = {
    ('03-2-2', None): 'Aligned. The left 56px shows loop art where the original shows its non-repeating left edge (two native tiles are not recoverable from the frozen data).',
    ('13-5-2', 0): 'Same picture 8px left: exact alignment needs native columns 32-33, outside the 256px loop.',
    ('13-5-2', 2): 'Same picture 8px left (see 5-2a).',
    ('14-5-3', 6): 'Columns aligned; the differences are animated star tiles caught on different animation frames.',
    ('16-6-1', 0): 'Exact except one star in horizon row 14-15 that the stationary 6-1 sky design leaves out of the scrolling horizon.',
}
results = {}
for line in (SRC / 'round-starts.txt').read_text().splitlines():
    m = re.match(r'(\S+) a?(\d+) (?:entry cam (\d+): identical-in-place (\d+)/(\d+) cols \((\d+)%\), best shift (-?\d+)|entry: no changed cells)', line)
    if m:
        results[m.group(1), int(m.group(2))] = m.groups()
out = (REPORT / 'rounds'); out.mkdir(exist_ok=True)
sections = []
for (stage, area), g in sorted(results.items()):
    run = json.loads((SRC / 'orig' / stage / 'run.json').read_text())
    erun = json.loads((SRC / 'enh' / stage / 'run.json').read_text())
    o, e = [(o, e) for o, e in zip(run['samples'], erun['samples']) if o['subarea'] == area and o['kind'] == 'entry'][0]
    imgs = []
    for which, s in (('orig', o), ('enh', e)):
        d = png_decode((SRC / which / stage / 'samples' / f"{s['name']}.png").read_bytes())
        imgs.append(d if isinstance(d, list) else d[2])
    row = [a + [(255, 255, 255)] * 4 + b for a, b in zip(*imgs)]
    letter = 'abcdefg'[area]
    name = f'{stage}-{letter}.png'
    (out / name).write_bytes(png_encode(row))
    if g[2] is None:
        pill, cls = 'no backdrop visible at start (identical)', 'ok'
    else:
        pct, shift = int(g[5]), int(g[6])
        pill, cls = ('exact', 'ok') if pct == 100 or (pct >= 99 and shift == 0 and stage == '16-6-1') else (f'{pct}% in place, shift {shift}px', 'warn')
        if stage == '16-6-1' and pct >= 99: pill = '99.9% (one omitted star)'
    note = NOTES.get((stage, area), NOTES.get((stage, None), '')) if cls == 'warn' or stage == '16-6-1' else ''
    sections.append(f'<section><h3>{NAMES[stage]}{letter} <span class="pill {cls}">{pill}</span></h3>'
                    f'<p class="small">{note} Columns: Original | {ROM_LABEL}.</p><img class="px" src="rounds/{name}" alt="Round {NAMES[stage]}{letter}: original and Enhanced first frames"></section>')
head = (REPORT / 'round-starts.html').read_text().split('<main>')[0]
html = head + f'''<main>
<h1>Round start audit</h1><p class="small">Opening frame of every round (area) in the 11 modified stages: raw ROM vs {ROM_LABEL},
reached the same way (Level Select writes, then the game's own round transition). Score = background tile columns identical in place.
4-2, 5-3, 5-4 and 6-1 use bridge columns: the loop holds the untouched native picture, and the bridge appears only while scrolling.</p>
{''.join(sections)}
</main></body></html>'''
(REPORT / 'round-starts.html').write_text(html)
print(len(sections), 'rounds')
