"""Trace the Enhanced first draw during a stage load (init_draw jsr $fe46 at
$FF5C .. $FF5F) and attribute cycles by bank and 4K page.
usage: inittrace.py ROM LABEL STAGE"""
import sys, re, struct
from collections import Counter
from pathlib import Path
import core
import local
rom, label, stage = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
SP = local.WORK / f'inittrace-{label}'
SP.mkdir(exist_ok=True)
LINE = re.compile(r'@\d+ \+(\d+)\s+([0-9A-F]{2}):([0-9A-F]{4})')
def wait(s):
    for _ in range(80000):
        if s.status()['paused']: return s.cpu()['physical_PC'][-4:].upper()
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    cpu = s.cpu(); sp = int(cpu['S'], 16)
    s.write(0x241, bytes([stage])); s.write(0x247, bytes([core.NEXT_SEQUENCE[stage], 0])); s.write(0xe65, bytes(22))
    s.write(0x100 + sp - 1, bytes([0xf2, 0x83])); s.reg('S', sp - 2); s.reg('A', stage); s.reg('PC', 0x8244)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.call('set_breakpoint', {'address': '1F5C', 'memory_area': 'rom', 'execute': True})
    while True:
        s.call('debug_continue'); pc = wait(s)
        if pc == '1F5C': break
        s.call('debug_step_into')
    s.call('remove_breakpoint', {'address': '1F5C', 'memory_area': 'rom'})
    s.call('set_breakpoint', {'address': '1F5F', 'memory_area': 'rom', 'execute': True})
    s.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M', 'filters': ['cpu.instructions']})
    seq0 = s.call('get_trace_log', {'count': 1})['total_logged']
    s.call('debug_continue'); wait(s)
    seq1 = s.call('get_trace_log', {'count': 1})['total_logged']
    c = Counter(); start = seq0
    while start < seq1:
        tr = s.call('get_trace_log', {'start': start, 'count': min(1000, seq1 - start)})
        for line in tr['lines']:
            m = LINE.match(line)
            if m: c[f'{m.group(2)}:{int(m.group(3), 16) >> 12:X}xxx'] += int(m.group(1))
        start += len(tr['lines'])
        if not tr['lines']: break
    tot = sum(c.values())
    print(label, 'init draw', tot // 3, 'cycles', f'({tot / 358995:.3f} frames)')
    for k, v in c.most_common(14): print(f'   {k} {v // 3}')
