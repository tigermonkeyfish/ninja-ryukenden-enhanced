"""Main-loop slack per frame around FRAME of a stored run: with the CPU
instruction trace on for COUNT frames, for each vblank report (in lines
after it) when the vblank handler returned (RTI at $FD60), when the main
loop next reached the vblank wait ($FD69) and the line of the next vblank;
slack = next vblank - wait reached (negative / missing = the update overran).
usage: slack.py ROM RUN FLAGS|orig FRAME COUNT"""
import re
import sys

from gbtools import Session, cv, load_run

LINE = 1365
rom, run_name = sys.argv[1], sys.argv[2]
flags = None if sys.argv[3] == 'orig' else int(sys.argv[3], 0)
at, count = int(sys.argv[4]), int(sys.argv[5])
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)] + [set()] * 60
EV = re.compile(r'@(\d+)\s')
with Session(rom, flags) as g:
    cv.start_stage(g, run['stage'])
    for f in range(at):
        g.press(inputs[f])
        g.checked_step(1)
    g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M',
                             'filters': ['cpu.instructions', 'vdc.irqs']})
    pos = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    for f in range(at, at + count):
        g.press(inputs[f])
        g.checked_step(1)
    end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    marks = []
    while pos < end:
        chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
        lines = chunk.get('entries') or chunk.get('lines') or []
        if not lines:
            break
        for ln in lines:
            t = ln if isinstance(ln, str) else ln.get('text', '')
            if 'VBLANK' in t:
                marks.append((int(EV.match(t).group(1)), 'vbl'))
            elif ':FD69 ' in t or ':FD60 ' in t:
                m = EV.match(t)
                if m:
                    marks.append((int(m.group(1)), 'wait' if ':FD69 ' in t else 'rti'))
        pos += len(lines)
vbls = [t for t, k in marks if k == 'vbl']
for i, v in enumerate(vbls[:-1]):
    nxt = vbls[i + 1]
    rti = next((t for t, k in marks if k == 'rti' and v < t < nxt), None)
    wait = next((t for t, k in marks if k == 'wait' and (rti or v) < t < nxt), None)
    print(f'frame {at + i}: handler returns {((rti - v) / LINE) if rti else -1:6.2f}  '
          f'wait reached {((wait - v) / LINE) if wait else float("nan"):7.2f}  '
          f'slack {((nxt - wait) / LINE) if wait else float("nan"):7.2f} lines')
