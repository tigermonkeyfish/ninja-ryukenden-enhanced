"""Replay a log with 1-frame steps, logging interrupted steps and the CPU clock.
usage: stepcheck.py ROM LOG LABEL [FRAMES]"""
import sys, json, struct
from pathlib import Path
import core
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, logf, label = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
limit = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
log = json.load(open(logf))['segments']
SP = Path(f'stepcheck-{label}').resolve(); SP.mkdir(exist_ok=True)
def clock(s):
    p = SP / 'clk.state'; s.call('save_state_file', {'file_path': str(p)})
    return struct.unpack_from('<Q', p.read_bytes(), 1)[0]
def setb(s, held, want):
    for x in held - want: s.button(x, 'release')
    for x in want - held: s.button(x, 'press')
    return set(want)
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    core.jump_to_stage(s, 3)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    s.call('debug_continue')
    for _ in range(80000):
        if s.status()['paused']: break
    s.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    print('breakpoints now:', s.call('list_breakpoints') if True else '', flush=True)
    t0 = clock(s); held = set(); f = 0; bad = []; clocks = []
    for n, b in log:
        held = setb(s, held, set(b))
        for _ in range(n):
            try:
                s.call('debug_step_frame', {'frames': 1, 'mode': 'sync'})
            except RuntimeError as exc:
                bad.append((f, str(exc)[:120]))
            f += 1
            if f % 50 == 0 or 740 <= f <= 770 or 1740 <= f <= 1770:
                clocks.append((f, round((clock(s) - t0) / FRAME, 3), s.status().get('pc')))
            if f >= limit: break
        if f >= limit: break
    print(label, 'interrupted steps:', bad[:20], len(bad))
    for c in clocks:
        if 740 <= c[0] <= 770 or 1740 <= c[0] <= 1770 or c[0] % 500 == 0: print(label, c)
