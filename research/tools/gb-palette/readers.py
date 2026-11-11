"""Who reads a RAM range during frames FROM..TO of a stored run (read
watchpoint; the replay is not frame-exact after the first stop, which is
fine for finding readers). usage: readers.py ROM RUN FLAGS FROM TO LO HI"""
import collections
import sys

from gbtools import Session, cv, load_run

rom, run_name, flags, a, b, lo, hi = sys.argv[1:8]
a, b = int(a), int(b)
run = load_run(run_name)
inputs = [set(x) for c, x in run['segments'] for _ in range(c)] + [set()] * 60
pcs = collections.Counter()
with Session(rom, int(flags, 0)) as g:
    cv.start_stage(g, run['stage'])
    for f in range(a):
        g.press(inputs[f])
        g.checked_step(1)
    g.call('set_breakpoint_range', {'start_address': lo, 'end_address': hi, 'read': True})
    f = a
    stops = 0
    while f < b and stops < 3000:
        g.press(inputs[f])
        r = g.step(1)
        if r is None:
            st = g.call('get_huc6280_status')
            bank = st['MPR'][int(st['PC'], 16) >> 13]['value']
            pcs[f'{bank}:{st["PC"]}'] += 1
            stops += 1
            continue
        f += 1
for k, v in pcs.most_common(30):
    print(k, v)
