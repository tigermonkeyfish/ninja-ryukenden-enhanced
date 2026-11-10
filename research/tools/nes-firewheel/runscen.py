"""Run scenarios on ROM(s): runscen.py NAMES... ; each on nes ROM with 4 and 0
and on 1.10 with 0, three at a time; compare off with 1.10."""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

here = Path(__file__).parent
B = Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve()
NES = sys.argv[1]
names = sys.argv[2:]
jobs = [(n, tag, rom, fl) for n in names for tag, rom, fl in (('on', NES, '4'), ('off', NES, '0'), ('v110', str(Path(os.environ['NFW_V110'])), '0'))]


def one(j):
    n, tag, rom, fl = j
    p = subprocess.run([sys.executable, str(here / 'scen.py'), rom, fl, str(B / 'sc' / f'{n}.json'),
                        str(B / 'sc' / f'{n}-{tag}.json')], capture_output=True, text=True)
    return n, tag, p.returncode, (p.stdout + p.stderr).strip()[-300:]


with ThreadPoolExecutor(3) as pool:
    for r in pool.map(one, jobs):
        print(*r, flush=True)
for n in names:
    a = json.loads((B / 'sc' / f'{n}-off.json').read_text())['log']
    b = json.loads((B / 'sc' / f'{n}-v110.json').read_text())['log']
    c = json.loads((B / 'sc' / f'{n}-on.json').read_text())['log']
    print(n, 'option off identical to 1.10:', a[:-1] == b[:-1], 'stack low on/off/1.10:', c[-1], a[-1], b[-1])
