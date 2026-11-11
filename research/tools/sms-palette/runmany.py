"""Run one probe over several runs, at most JOBS sessions at once (research
reference, not a maintained tool). Each command is the probe followed by its
arguments with {run} replaced by the run name; its last output line (and any
error) is printed, and the whole output saved to OUTDIR/<tag>-<run>.out.
usage: runmany.py OUTDIR TAG JOBS RUNS(comma|all) PROBE ARG... ({run} in the args)"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_NAMES = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']

outdir, tag, jobs, runs, probe, *args = sys.argv[1:]
runs = RUN_NAMES if runs == 'all' else runs.split(',')
Path(outdir).mkdir(parents=True, exist_ok=True)
script = next(p for p in (HERE / probe, HERE.parent / 'hell-palette' / probe, HERE.parent / 'gb-palette' / probe)
              if p.exists())


def one(name):
    r = subprocess.run([sys.executable, str(script), *[a.replace('{run}', name) for a in args]],
                       capture_output=True, text=True)
    (Path(outdir) / f'{tag}-{name}.out').write_text(r.stdout + r.stderr)
    last = (r.stdout.strip().splitlines() or [''])[-1]
    return f'{name}: {last}' + (f' ERROR rc={r.returncode} {r.stderr[-600:]}' if r.returncode else '')


with ThreadPoolExecutor(int(jobs)) as pool:
    for line in pool.map(one, runs):
        print(line, flush=True)
