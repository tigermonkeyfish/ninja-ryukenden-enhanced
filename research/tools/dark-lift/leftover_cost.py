"""Time the mapped upload of a left-over entry with and without the fade
rule (research reference, not a maintained tool): sms-palette/upload_cost.py's
measurement (the hardware-event trace of one vblank from the 1-1 main-loop
hook) for a queue of one left-over entry ($2104 bit 5 set, the main loop
idle), with the native fade's level $2A8A written to 8 (after a fade-in:
LEFTOVER_CAP colours go) and to $FF (a fade-out has ended on black:
FADE_CAP colours go). Printed per case: the VCE colour writes, the first and the
last in master clocks and lines after the VDC vblank interrupt, the
scanline interrupt's CPU entry after it, and what is left queued. Run on the
build before the rule and on the build with it: with level 8 the figures
must be equal to the master clock (the rule costs the path nothing).
usage: leftover_cost.py ROM FLAGS   (GB_WORK: seed.state, original.pce)"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'sms-palette'))
from smstools import Session, cv  # noqa: E402

LINE = 1365
EVENT = re.compile(r'@(\d+)\s.*?\[(VCE|VDC1|CPU)\]\s+(\S+)')
CASES = {
    'left over 336 from 176': [(176, 336)],
    'left over 512 from 59': [(59, 512)],
    'left over 64 from 480 (wraps)': [(480, 64)],
    'left over 300 from 250': [(250, 300)],
    'left over 10 from 3': [(3, 10)],
}


def measure(g, state, queue, level, busy=False):
    g.call('load_state_file', {'file_path': str(state)})
    q = bytearray(33)
    q[0] = len(queue)
    for k, (idx, n) in enumerate(queue):
        q[1 + k], q[9 + k] = (2 * n) & 0xff, (2 * n) >> 8
        q[17 + k], q[25 + k] = idx & 0xff, idx >> 8
    g.write(0x260, bytes(q))
    st = g.read(0x104, 1)[0]
    g.write(0x104, bytes([(st & ~0x60) | 0x20 | (0x40 if busy else 0)]))
    g.write(0xa8a, bytes([level]))
    g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '100K',
                             'filters': ['cpu.irqs', 'vdc.irqs', 'vce.registers']})
    start = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    g.step(2)
    end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    lines, pos = [], start
    while pos < end:
        chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
        got = chunk.get('entries') or chunk.get('lines') or []
        if not got:
            break
        lines += [x if isinstance(x, str) else x.get('text', '') for x in got]
        pos += len(got)
    g.call('set_trace_log', {'enabled': False})
    ev = [(int(m.group(1)), m.group(2), m.group(3)) for m in map(EVENT.match, lines) if m]
    vbl = next(t for t, k, w in ev if k == 'VDC1' and w == 'VBLANK')
    rcr = next(t for t, k, w in ev if k == 'VDC1' and w == 'SCANLINE' and t > vbl)
    cpu = next((t for t, k, w in ev if k == 'CPU' and t > rcr), None)
    vce = [t for t, k, w in ev if k == 'VCE' and w == 'COLOR' and vbl <= t < rcr]
    ram = g.read(0x260, 0x21)
    left = [(ram[17 + k] | ram[25 + k] << 8, (ram[1 + k] | ram[9 + k] << 8) // 2) for k in range(ram[0])]
    return {'writes': len(vce), 'first': vce[0] - vbl if vce else 0, 'end': vce[-1] - vbl if vce else 0,
            'split': cpu - vbl if cpu else 0, 'left': left, 'state': g.read(0x104, 1)[0]}


def main():
    rom, flags = sys.argv[1], int(sys.argv[2], 0)
    with Session(rom, flags) as g:
        cv.start_stage(g, 0)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.run_to('83F3', polls=20000)
        g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        state = g.logdir / 'hook.state'
        g.call('save_state_file', {'file_path': str(state)})
        print(Path(rom).name, 'options', hex(g.read(0x100, 1)[0]), flush=True)
        for name, queue in CASES.items():
            for level, busy in ((8, False), (0xff, False), (8, True), (0xff, True)):
                r = measure(g, state, queue, level, busy)
                print(f'{name:30s} level ${level:02X} {"busy before" if busy else "idle       "}: {r["writes"]:4d} writes, '
                      f'first {r["first"]:6d} ({r["first"] / LINE:6.3f} lines), last {r["end"]:6d} '
                      f'({r["end"] / LINE:6.3f}), split entry {r["split"]:6d} ({r["split"] / LINE:6.3f}), '
                      f'left {r["left"]}, state ${r["state"]:02X}', flush=True)


if __name__ == '__main__':
    main()
