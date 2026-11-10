"""Record every stored run (rec2.py: traces + screenshot hashes, no images)
on the given labelled ROMs and compare pairs.
regress2.py WORK label=ROM:FLAGS ... -- pairA,pairB ..."""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import comparison_video as cvm  # noqa: E402

here = Path(__file__).parent
WT = Path(__file__).resolve().parents[3]
work = Path(sys.argv[1])
work.mkdir(parents=True, exist_ok=True)
args = sys.argv[2:]
sep = args.index('--')
builds = dict(a.split('=', 1) for a in args[:sep])
pairs = [p.split(',') for p in args[sep + 1:]]
names = [p.stem for p in sorted((WT / 'research/comparison-runs').glob('*.json'))]


def rec(job):
    name, label = job
    rom, flags = builds[label].rsplit(':', 1)
    out = work / f'{name}-{label}.json'
    if out.exists():
        return name, label, 0, 'cached'
    p = subprocess.run([sys.executable, str(here / 'rec2.py'), rom, str(WT / f'research/comparison-runs/{name}.json'),
                        str(out), flags], capture_output=True, text=True)
    return name, label, p.returncode, (p.stdout + p.stderr).strip()[-200:]


with ThreadPoolExecutor(4) as pool:
    for r in pool.map(rec, [(n, l) for n in names for l in builds]):
        print(*r, flush=True)
summary = {}
for name in names:
    t = {l: json.loads((work / f'{name}-{l}.json').read_text()) for l in builds}
    row = {'frames': len(next(iter(t.values())))}
    for a, b in pairs:
        same, diff = cvm.compare(t[a], t[b])
        row[f'{a}~{b}'] = {'identical_gameplay': same, 'ram_frames_differ': len(diff['ram']),
                           'png_frames_differ': sum(1 for x, y in zip(t[a], t[b]) if x['png'] != y['png']),
                           'whole_trace_equal': t[a] == t[b]}
    summary[name] = row
    print(name, json.dumps(row), flush=True)
(work / 'summary.json').write_text(json.dumps(summary, indent=1))
