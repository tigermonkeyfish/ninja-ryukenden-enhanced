"""Trace the area-change draw (init_background jsr $fe46, $FF63..$FF66) at the
first forced area change of a stage; cycles by bank:page and top PCs.
usage: areadraw.py ROM LABEL STAGE"""
import sys, re, json
from collections import Counter
from pathlib import Path
import core
import local
rom, label, stage = Path(sys.argv[1]).resolve(), sys.argv[2], int(sys.argv[3])
SP = local.WORK / f'areadraw-{label}'; SP.mkdir(exist_ok=True)
LINE = re.compile(r'@\d+ \+(\d+)\s+([0-9A-F]{2}):([0-9A-F]{4})')
def run_to(s):
    s.call('debug_continue')
    for _ in range(80000):
        st = s.status()
        if st['paused']: return st['pc']
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    run_to(s); s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    s.step(30)
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    run_to(s); s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    s.reg('PC', 0x8490)
    s.call('set_breakpoint', {'address': '1f63', 'memory_area': 'rom', 'execute': True})
    print('stop', run_to(s))
    s.call('remove_breakpoint', {'address': '1f63', 'memory_area': 'rom'})
    s.call('set_breakpoint', {'address': '1f66', 'memory_area': 'rom', 'execute': True})
    s.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M', 'filters': ['cpu.instructions']})
    seq0 = s.call('get_trace_log', {'count': 1})['total_logged']
    print('stop', run_to(s))
    seq1 = s.call('get_trace_log', {'count': 1})['total_logged']
    c = Counter(); pcs = Counter(); start = seq0
    while start < seq1:
        tr = s.call('get_trace_log', {'start': start, 'count': min(1000, seq1 - start)})
        for line in tr['lines']:
            m = LINE.match(line)
            if m:
                cyc = int(m.group(1))
                c[f'{m.group(2)}:{m.group(3)[0]}xxx'] += cyc
                pcs[f'{m.group(2)}:{m.group(3)}'] += cyc
        start += len(tr['lines'])
        if not tr['lines']: break
    tot = sum(c.values())
    print(label, 'area draw', tot, 'trace units', f'({tot / 358995:.3f} frames if units are master clocks)')
    for k, v in c.most_common(12): print(' ', k, v, f'{v / tot:.1%}')
    (SP / 'pcs.json').write_text(json.dumps(pcs))
