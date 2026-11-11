"""(e) Defaults, menu never opened: replay each stored run on two ROMs from
the same seed and require identical frames: screenshot, all RAM, SAT and VCE
every frame, all VRAM every 30 frames and at the end.
usage: identity.py BASE_ROM CANDIDATE_ROM OUT [runs,comma]"""
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
EMU = os.environ['GEARGRAFX']

import hashlib, json, sys, tempfile
from pathlib import Path
from comparison_video import Game, start_point, start_stage
RUNS = ROOT / 'research/comparison-runs'
base, cand, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
names = sys.argv[4].split(',') if len(sys.argv) > 4 else sorted(p.stem for p in RUNS.glob('*.json'))
out.mkdir(parents=True, exist_ok=True)
seed = Path(os.environ['NINJA_SEED_STATE'])  # comparison_video.make_seed on the original


def trace(rom, run):
    inputs = [b for c, b in run['segments'] for _ in range(c)] + [[]] * 60
    hashes = []
    with Game(EMU, Path(tempfile.mkdtemp(dir=out))) as g:
        start_point(g, rom, seed, enhanced=True)
        start_stage(g, run['stage'])
        for f, buttons in enumerate(inputs):
            g.press(set(buttons))
            g.checked_step(1)
            h = hashlib.sha256()
            h.update(g.screenshot())
            h.update(g.read(0, 0x2000))
            h.update(g.read(0, 512, area=6))
            h.update(g.read(0, 1024, area=8))
            if f % 30 == 0 or f == len(inputs) - 1:
                h.update(g.read(0, 0x10000, area=4))
            hashes.append(h.hexdigest()[:16])
    return hashes


report = {}
for name in names:
    run = json.loads((RUNS / f'{name}.json').read_text())
    a, b = trace(base, run), trace(cand, run)
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    report[name] = {'frames': len(a), 'differing_frames': len(diff), 'first': diff[:5],
                    'trace_sha256': hashlib.sha256(''.join(b).encode()).hexdigest()}
    print(name, report[name], flush=True)
report['ok'] = all(r['differing_frames'] == 0 for r in report.values() if isinstance(r, dict))
(out / 'identity.json').write_text(json.dumps(report, indent=1))
print('identity', 'passed' if report['ok'] else 'FAILED')
