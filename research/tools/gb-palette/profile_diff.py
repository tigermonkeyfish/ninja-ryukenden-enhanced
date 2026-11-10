"""Clocks per code page (bank:PC>>8) over COUNT frames from FRAME of a
stored run, from the CPU instruction trace (each entry's delta charged to
its own instruction's page). Prints the top pages; with two flag sets,
prints both and the pages whose totals differ.
usage: profile_diff.py ROM RUN FRAME COUNT FLAGS_A FLAGS_B"""
import re
import sys
from collections import Counter

from gbtools import Session, cv, load_run

rom, run_name, at, count = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60
LINE = re.compile(r'@(\d+)\s+(?:\+(\d+)\s+)?([0-9A-F]{2}):([0-9A-F]{4})')


def profile(flags):
    pages = Counter()
    with Session(rom, None if flags == 'orig' else int(flags, 0)) as g:
        cv.start_stage(g, run['stage'])
        for f in range(at):
            g.press(inputs[f])
            g.checked_step(1)
        g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M',
                                 'filters': ['cpu.instructions']})
        pos = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
        for f in range(at, at + count):
            g.press(inputs[f])
            g.checked_step(1)
        end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
        prev = None
        while pos < end:
            chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
            lines = chunk.get('entries') or chunk.get('lines') or []
            if not lines:
                break
            for ln in lines:
                m = LINE.match(ln if isinstance(ln, str) else ln.get('text', ''))
                if not m:
                    continue
                if prev is not None and m.group(2):
                    pages[prev] += int(m.group(2))
                prev = f'{m.group(3)}:{m.group(4)[:2]}'
            pos += len(lines)
    return pages


a, b = profile(sys.argv[5]), profile(sys.argv[6])
print('total', sum(a.values()), sum(b.values()))
for k in sorted(set(a) | set(b), key=lambda k: -abs(a[k] - b[k]))[:20]:
    print(k, a[k], b[k], b[k] - a[k])
