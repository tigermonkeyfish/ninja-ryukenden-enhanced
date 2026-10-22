"""Per sample: shift s such that Enhanced background pixels equal native pixels at x+s (changed cells only)."""
import sys
import stitch
stage, sub = sys.argv[1], int(sys.argv[2]); rows = [int(r) for r in sys.argv[3].split(',')]
kinds = tuple(sys.argv[4].split(',')) if len(sys.argv) > 4 else ('fwd',)
rng = int(sys.argv[5]) if len(sys.argv) > 5 else 40
data = stitch.collect(stage, sub, kinds)
out = []
for d in data:
    best = None
    for s in range(-rng, rng + 1):
        agree = tot = 0
        for r in rows:
            e, o, f = d['enh'][r], d['orig'][r], d['flags'][r]
            for x in range(256):
                if f[x] and 0 <= x + s < 256 and f[x + s]:
                    tot += 1; agree += e[x] == o[x + s]
        if tot >= 32 and (best is None or agree / tot > best[1] + 1e-9):
            best = (s, round(agree / tot, 3), tot)
    out.append((d['camera'], best))
for cam, b in out: print(cam, b)
