"""Catalogue every contact-damage event in the stored runs on a ROM (no wheel)."""
import json
import subprocess
import sys
from fw import *

rom = sys.argv[1]
names = sys.argv[2:] or [p.stem for p in sorted(RUNS.glob('*.json'))]
here = Path(__file__).parent
result = {}
for name in names:
    run = json.loads((RUNS / f'{name}.json').read_text())
    out = OUT / f'cat-{name}.json'
    p = subprocess.run([sys.executable, str(here / 'survey.py'), 'trace', rom, name, '0', '-1',
                        str(run['frames']), str(out)], capture_output=True, text=True)
    evs = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
    if p.returncode:
        print(name, 'FAILED', p.stderr[-500:], flush=True)
        continue
    for e in evs:
        if e['health'][1] < e['health'][0] and e['health'][1] > 0 or e['health'][0] - e['health'][1] < 16:
            q = subprocess.run([sys.executable, str(here / 'survey.py'), 'ident', rom, name, '0', '-1', str(e['f'])],
                               capture_output=True, text=True)
            try:
                e['hit'] = json.loads(q.stdout.strip().splitlines()[-1])
            except Exception:
                e['hit'] = q.stderr[-300:]
        print(name, json.dumps(e), flush=True)
    result[name] = evs
(OUT / 'catalog.json').write_text(json.dumps(result, indent=1))
