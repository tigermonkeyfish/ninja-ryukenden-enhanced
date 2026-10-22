"""Opening composition: horizontal shift between Enhanced and native backdrops at each area entry."""
import json
from collections import Counter
import stitch
from analyze import R, ROWS
out = {}
for d in sorted((R/'orig').iterdir()):
    if not (d/'run.json').exists() or not (R/'enh'/d.name/'run.json').exists(): continue
    run = json.loads((d/'run.json').read_text())
    for a in run['areas']:
        data = stitch.collect(d.name, a['subarea'], ('entry',))
        if not data: continue
        smp = data[0]
        rows = [r for r in range(ROWS) if any(smp['flags'][r])]
        if not rows:
            print(d.name, a['subarea'], 'entry: no changed cells (identical)'); continue
        best = None
        for s in range(-128, 129):
            ag = t = 0
            for r in rows:
                e, o, f = smp['enh'][r], smp['orig'][r], smp['flags'][r]
                for x in range(256):
                    if f[x] and 0 <= x + s < 256 and f[x + s]:
                        t += 1; ag += e[x] == o[x + s]
            if t >= 64 and (best is None or (ag / t, -abs(s)) > (best[1], -abs(best[0]))):
                best = (s, ag / t, t)
        same = sum(1 for r in rows for x in range(256) if smp['flags'][r][x] and smp['enh'][r][x] == smp['orig'][r][x])
        tot = sum(1 for r in rows for x in range(256) if smp['flags'][r][x])
        print(f"{d.name} a{a['subarea']} entry cam {smp['camera']}: identical-in-place {same}/{tot} cols ({100*same/max(tot,1):.0f}%), best shift {best[0] if best else None} (agreement {best[1]:.3f})" if best else f"{d.name} a{a['subarea']} entry: {same}/{tot} same, no shift fit")
