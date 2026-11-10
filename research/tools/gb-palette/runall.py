"""Run a probe over all 11 stored runs, at most JOBS sessions at once.
usage: runall.py PROBE ROM OUTDIR TAG FLAGS [JOBS] [extra args...]
writes OUTDIR/TAG-<run>.json via `PROBE ROM RUN OUT FLAGS extra...`."""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gbtools import RUN_NAMES

probe, rom, outdir, tag, flags = sys.argv[1:6]
jobs = int(sys.argv[6]) if len(sys.argv) > 6 else 3
extra = sys.argv[7:]
Path(outdir).mkdir(parents=True, exist_ok=True)
here = Path(__file__).resolve().parent


def one(name):
    out = Path(outdir) / f'{tag}-{name}.json'
    if out.exists():
        return f'{name}: exists'
    r = subprocess.run([sys.executable, str(here / probe), rom, name, str(out), flags, *extra],
                       capture_output=True, text=True)
    return (r.stdout.strip().splitlines() or [''])[-1] + (f' ERROR {r.stderr[-800:]}' if r.returncode else '')


with ThreadPoolExecutor(jobs) as pool:
    for line in pool.map(one, RUN_NAMES):
        print(line, flush=True)
