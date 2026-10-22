"""Side-by-side native | Enhanced pairs at evenly spaced camera positions for every area."""
import json
from pathlib import Path
from analyze import R
from core import png_decode, png_encode
OUT = R / 'report' / 'pairs'; OUT.mkdir(parents=True, exist_ok=True)
index = {}
for d in sorted((R / 'orig').iterdir()):
    if not (d / 'run.json').exists(): continue
    run = json.loads((d / 'run.json').read_text())
    samples = run['samples']
    chosen = []
    for a in run['areas']:
        sub = a['subarea']
        entry = [s for s in samples if s['subarea'] == sub and s['kind'] == 'entry']
        fwd = [s for s in samples if s['subarea'] == sub and s['kind'] in ('fwd', 'static')]
        n = 8 if len(fwd) > 40 else 5 if len(fwd) > 12 else len(fwd)
        pick = [fwd[round(i * (len(fwd) - 1) / max(n - 1, 1))] for i in range(n)] if fwd else []
        seen = set()
        for s in entry + pick:
            if s['name'] in seen: continue
            seen.add(s['name']); chosen.append(s)
    out = []
    for s in chosen:
        _, _, a = png_decode((R / 'orig' / d.name / 'samples' / f"{s['name']}.png").read_bytes())
        _, _, b = png_decode((R / 'enh' / d.name / 'samples' / f"{s['name']}.png").read_bytes())
        rows = [ra + [(24, 24, 24)] * 4 + rb for ra, rb in zip(a, b)]
        name = f"{d.name}-{s['name']}.png"
        (OUT / name).write_bytes(png_encode(rows))
        out.append({'file': f'pairs/{name}', 'name': s['name'], 'area': s['subarea'], 'camera': s['camera'], 'kind': s['kind']})
    index[d.name] = out
    print(d.name, len(out))
(R / 'report' / 'pairs.json').write_text(json.dumps(index, indent=1))
