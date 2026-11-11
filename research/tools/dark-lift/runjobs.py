"""Run the command lines of a file, at most JOBS at once (research
reference, not a maintained tool): one emulator session per line, so JOBS
is the number of sessions. Each line is `NAME: python arguments...`; its
output goes to LOGDIR/NAME.out and its last line (and any error) is printed.
usage: runjobs.py FILE JOBS LOGDIR   (from the repository root, in the
emulator environment of run-check.sh; GB_WORK / NES_WORK as the probes need)"""
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

jobs_file, jobs, logdir = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
logdir.mkdir(parents=True, exist_ok=True)
lines = [l.strip() for l in Path(jobs_file).read_text().splitlines() if l.strip() and not l.startswith('#')]


def one(line):
    name, command = line.split(':', 1)
    r = subprocess.run([sys.executable, *shlex.split(command)], capture_output=True, text=True)
    (logdir / f'{name}.out').write_text(r.stdout + r.stderr)
    last = (r.stdout.strip().splitlines() or [''])[-1]
    return f'{name}: {last}' + (f' ERROR rc={r.returncode} {r.stderr[-800:]}' if r.returncode else '')


with ThreadPoolExecutor(jobs) as pool:
    for result in pool.map(one, lines):
        print(result, flush=True)
print('finished')
