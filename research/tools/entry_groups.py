"""Round-start shift per row group (sky rows 0-13, horizon rows 14-22)."""
import json, sys
import stitch
from analyze import R, ROWS
GROUPS = {'sky': range(0, 14), 'horizon': range(14, 23)}
stages = sys.argv[1:]
for d in sorted((R / 'orig').iterdir()):
    if not (d / 'run.json').exists() or (stages and d.name not in stages): continue
    run = json.loads((d / 'run.json').read_text())
    for a in run['areas']:
        data = stitch.collect(d.name, a['subarea'], ('entry',))
        if not data: continue
        smp = data[0]
        out = []
        for g, rows in GROUPS.items():
            rows = [r for r in rows if any(smp['flags'][r])]
            if not rows: out.append(f'{g}: none'); continue
            same = sum(smp['enh'][r][x] == smp['orig'][r][x] for r in rows for x in range(256) if smp['flags'][r][x])
            tot = sum(1 for r in rows for x in range(256) if smp['flags'][r][x])
            best = None
            for s in range(-360, 361):
                ag = t = 0
                for r in rows:
                    e, o, f = smp['enh'][r], smp['orig'][r], smp['flags'][r]
                    for x in range(256):
                        if f[x] and 0 <= x + s < 256 and f[x + s]:
                            t += 1; ag += e[x] == o[x + s]
                if t >= 64 and (best is None or (ag / t, -abs(s)) > (best[1], -abs(best[0]))):
                    best = (s, ag / t)
            out.append(f'{g}: in-place {same}/{tot} ({same / tot:.0%}) best shift {best[0] if best else None} ({best[1]:.3f})' if best else f'{g}: in-place {same}/{tot}')
        print(d.name, a['subarea'], f"cam {a.get('entry_camera', '?')}", ' | '.join(out))
