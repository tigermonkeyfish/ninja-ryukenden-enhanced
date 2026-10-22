"""Original area change: per frame from the trigger to the first update, the
$83F3 main-loop hits and the share of cycles spent outside the RAM wait loop.
usage: areaidle.py ROM LABEL STAGE"""
import re, struct, sys
from collections import Counter, defaultdict
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage = Path(sys.argv[1]).resolve(), sys.argv[2], int(sys.argv[3])
SP = local.WORK / f'areaidle-{label}'; SP.mkdir(exist_ok=True)
LINE = re.compile(r'@\d+ \+(\d+)\s+([0-9A-F]{2}):([0-9A-F]{4})')
def clock(s):
    p = SP / 'clk.state'; s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]
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
    s.step(1); B0 = clock(s)
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    run_to(s)
    s.reg('PC', 0x8490)
    s.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M', 'filters': ['cpu.instructions']})
    seq0 = s.call('get_trace_log', {'count': 1})['total_logged']
    t_start = clock(s)
    hits = []
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    while True:
        pc = run_to(s)
        t = clock(s)
        if pc == '8457': break
        hits.append(f'f{(t - B0) // FRAME}+{(t - B0) % FRAME / FRAME:.3f}')
        s.call('debug_step_into')
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    seq1 = s.call('get_trace_log', {'count': 1})['total_logged']
    busy = defaultdict(int); idle = defaultdict(int); t = t_start; start = seq0; top = defaultdict(Counter)
    while start < seq1:
        tr = s.call('get_trace_log', {'start': start, 'count': min(1000, seq1 - start)})
        for line in tr['lines']:
            m = LINE.match(line)
            if not m: continue
            cyc = int(m.group(1)); f = (t - B0) // FRAME
            pc = m.group(3)
            if pc.startswith('220') or pc.startswith('221'): idle[f] += cyc
            else:
                busy[f] += cyc; top[f][f'{m.group(2)}:{pc[:3]}x'] += cyc
            t += cyc
        start += len(tr['lines'])
        if not tr['lines']: break
    print(label, '$83F3 hits:', hits)
    for f in sorted(set(busy) | set(idle)):
        print(label, f'frame {f}: busy {busy[f] / FRAME:.3f} idle(RAM loop) {idle[f] / FRAME:.3f}', top[f].most_common(4))
