"""Run sweep.py for every run of the catalogue log, three at a time."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

B = Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve()
here = Path(__file__).parent
cat = {}
for line in (B / 'catalog.log').read_text().splitlines():
    name, rest = line.split(' ', 1)
    if rest.startswith('{'):
        cat.setdefault(name, []).append(json.loads(rest))
(B / 'catalog.json').write_text(json.dumps(cat, indent=1))


def one(name):
    out = B / f'sweep-{name}.json'
    p = subprocess.run([sys.executable, str(here / 'sweep.py'), str(Path(os.environ['NFW_V110'])), os.environ['NFW_DEV'],
                        str(B / 'catalog.json'), str(out)], env=dict(os.environ, ONLY=name),
                       capture_output=True, text=True)
    (B / f'sweep-{name}.log').write_text(p.stdout + p.stderr)
    return name, p.returncode


with ThreadPoolExecutor(int(sys.argv[1]) if len(sys.argv) > 1 else 3) as pool:
    for name, rc in pool.map(one, list(cat)):
        print(name, 'rc', rc, flush=True)
