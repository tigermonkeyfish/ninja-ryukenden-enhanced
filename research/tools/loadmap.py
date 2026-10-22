"""Per-frame busy/idle map of a stage load (from $8244 entry to the first
gameplay update): idle = time in short loops outside the IRQ handlers.
Also marks frames where VRAM writes ($0002/$0003 data port) happen.
usage: loadmap.py ROM LABEL STAGE FRAMES"""
import sys, re
from collections import defaultdict
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage, nf = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
SP = local.WORK / f'loadmap-{label}'
SP.mkdir(exist_ok=True)
LINE = re.compile(r'@\d+ \+(\d+)\s+([0-9A-F]{2}):([0-9A-F]{4})')
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
    s.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M', 'filters': ['cpu.instructions']})
    seq0 = s.call('get_trace_log', {'count': 1})['total_logged']
    s.step(nf)
    seq1 = s.call('get_trace_log', {'count': 1})['total_logged']
    busy, idle, banks = defaultdict(int), defaultdict(int), defaultdict(set)
    start, cyc, run = seq0, 0, []
    while start < seq1:
        tr = s.call('get_trace_log', {'start': start, 'count': min(1000, seq1 - start)})
        for line in tr['lines']:
            m = LINE.match(line)
            if not m: continue
            c = int(m.group(1)); b = m.group(2); a = int(m.group(3), 16)
            cyc += c
            f = cyc // FRAME
            if b == '00' and 0xFCD7 <= a <= 0xFDC0:
                busy[f] += c; continue
            run.append((b, a))
            if len(run) > 12: run.pop(0)
            if len(run) == 12 and len(set(run)) <= 4: idle[f] += c
            else: busy[f] += c; banks[f].add(b)
        start += len(tr['lines'])
        if not tr['lines']: break
    for f in range(nf):
        tot = busy[f] + idle[f]
        if tot: print(f'{label} frame {f:3}: busy {busy[f] / FRAME:.2f} idle {idle[f] / FRAME:.2f} banks {sorted(banks[f])[:8]}')
