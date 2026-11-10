"""Print the hardware-event trace (CPU/VDC IRQs, VCE writes) of a few frames
after stage entry. usage: traceprobe.py ROM FLAGS STAGE FRAMES [SKIP]"""
import sys
from gbtools import Session, cv

rom, flags, stage, frames = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3]), int(sys.argv[4])
skip = int(sys.argv[5]) if len(sys.argv) > 5 else 0
with Session(rom, flags) as g:
    cv.start_stage(g, stage)
    if skip:
        g.checked_step(skip)
    g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                             'filters': ['cpu.irqs', 'vdc.irqs', 'vce.registers']})
    start = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    g.checked_step(frames)
    end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    pos = start
    while pos < end:
        chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
        lines = chunk.get('entries') or chunk.get('lines') or []
        if not lines:
            print(list(chunk.keys()))
            break
        for ln in lines:
            print(ln if isinstance(ln, str) else ln.get('text', ln))
        pos += len(lines)
