"""Where in the frame the area-change work falls: frame-boundary-relative
clocks of $80AB entry/return (native init) and, in Enhanced, the draw.
usage: areawin.py ROM LABEL STAGE [CHANGES]"""
import struct, sys
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage = Path(sys.argv[1]).resolve(), sys.argv[2], int(sys.argv[3])
changes = int(sys.argv[4]) if len(sys.argv) > 4 else 2
SP = local.WORK / f'areawin-{label}'; SP.mkdir(exist_ok=True)
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
    for change in range(changes):
        s.step(1); B0 = clock(s)                     # a frame boundary
        s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
        run_to(s)
        s.reg('PC', 0x8490)
        t0 = clock(s)
        pos = lambda t: f'f{(t - B0) // FRAME}+{(t - B0) % FRAME / FRAME:.3f}'
        events = [('trigger', pos(t0))]
        bps = ['20ab', '1f63', '1f66']
        for a in bps: s.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
        ret = None
        while True:
            pc = run_to(s)
            t = clock(s)
            if pc == '8457':
                events.append(('first update', pos(t))); break
            if pc == '80AB':
                cpu = s.cpu(); sp = int(cpu['S'], 16)
                st = s.read(0x100 + sp + 1, 2); ret = (st[0] | st[1] << 8) + 1
                events.append((f'$80AB entry (returns to ${ret:04X})', pos(t)))
                s.call('set_breakpoint', {'address': f'{ret:04x}', 'memory_area': 'cpu_addr', 'execute': True})
                s.call('debug_step_into')
            elif ret is not None and pc == f'{ret:04X}':
                events.append(('$80AB return', pos(t)))
                s.call('remove_breakpoint', {'address': f'{ret:04x}', 'memory_area': 'cpu_addr'})
                ret = None
            elif pc == 'FF63': events.append(('draw start', pos(t)))
            elif pc == 'FF66': events.append(('draw end', pos(t)))
        for a in bps: s.call('remove_breakpoint', {'address': a, 'memory_area': 'rom'})
        s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
        print(label, f'change {change}:', '; '.join(f'{k} {v}' for k, v in events), flush=True)
        s.step(30)
