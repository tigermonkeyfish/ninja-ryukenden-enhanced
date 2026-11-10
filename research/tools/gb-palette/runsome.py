"""Like runall.py for a chosen list of runs.
usage: runsome.py RUNS(comma) PROBE ROM OUTDIR TAG FLAGS [JOBS] [extra args...]"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

names = sys.argv[1].split(',')
probe, rom, outdir, tag, flags = sys.argv[2:7]
jobs = int(sys.argv[7]) if len(sys.argv) > 7 else 3
extra = sys.argv[8:]
here = Path(__file__).resolve().parent
Path(outdir).mkdir(parents=True, exist_ok=True)


def one(name):
    out = Path(outdir) / f'{tag}-{name}.json'
    r = subprocess.run([sys.executable, str(here / probe), rom, name, str(out), flags, *extra],
                       capture_output=True, text=True)
    return (r.stdout.strip().splitlines() or [''])[-1] + (f' ERROR {r.stderr[-800:]}' if r.returncode else '')


with ThreadPoolExecutor(jobs) as pool:
    for line in pool.map(one, names):
        print(line, flush=True)
