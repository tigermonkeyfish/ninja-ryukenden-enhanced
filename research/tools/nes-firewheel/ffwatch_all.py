import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

here = Path(__file__).parent
rom, lo, hi = sys.argv[1:4]
names = ['boot'] + [p.stem for p in sorted((Path(__file__).resolve().parents[3] / 'research/comparison-runs').glob('*.json'))]


def one(n):
    p = subprocess.run([sys.executable, str(here / 'ffwatch.py'), rom, n, lo, hi], capture_output=True, text=True)
    return (p.stdout.strip().splitlines() or [p.stderr[-300:]])[-1]


with ThreadPoolExecutor(3) as pool:
    for line in pool.map(one, names):
        print(line, flush=True)
