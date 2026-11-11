"""Measure the vblank upload for synthetic queues (as research/tools/gb-palette/
upload_cost.py): at the 1-1 main-loop hook ($83F3) write a queue, run one
frame with the hardware-event trace on and report, for that vblank, the VCE
colour writes, the first and last (lines after the VDC vblank interrupt), the
median master clocks between consecutive writes within a run of writes
(a TIA: native rate; the mapped loop: ~156), the biggest gaps (chunk set-up
costs) and what is left queued. FLAGS: $2100 for the session (0x18 HELL,
0x10 GB DMG, 0 Original).
usage: upload_cost.py ROM FLAGS"""
import re
import statistics
import sys

from helltools import Session, cv

LINE = 1365
EVENT = re.compile(r'@(\d+)\s.*?\[(VCE|VDC1|CPU)\]\s+(\S+)')
CASES = {
    'one 512': [(0, 512)],
    'mapped 128': [(0, 128)],
    'mapped 16': [(16, 16)],
    'raw 1 (256)': [(256, 1)],
    'raw 16 (256)': [(256, 16)],
    'raw 64 (256)': [(256, 64)],
    'raw 128 (256)': [(256, 128)],
    'raw 256 (256)': [(256, 256)],
    'raw 272 (240)': [(240, 272)],
    'HUD 16 (240)': [(240, 16)],
    '8 x 16 sprites': [(256 + 16 * i, 16) for i in range(8)],
    '3 x 16 sprites': [(256, 16), (272, 16), (288, 16)],
    '2 x 256': [(0, 256), (256, 256)],
    '256 + 7 singles': [(0, 256)] + [(241 + i, 1) for i in range(7)],
}


def measure(g, state, queue):
    g.call('load_state_file', {'file_path': str(state)})
    q = bytearray(33)
    q[0] = len(queue)
    for k, (idx, n) in enumerate(queue):
        q[1 + k], q[9 + k] = (2 * n) & 0xff, (2 * n) >> 8
        q[17 + k], q[25 + k] = idx & 0xff, idx >> 8
    g.write(0x260, bytes(q))
    opts = g.read(0x100, 1)[0]
    g.write(0x100, bytes([opts & ~0x60]))      # new work, not a left-over entry; main loop idle before
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
    vce = [t for t, k, w in ev if k == 'VCE' and w == 'COLOR' and vbl <= t < rcr]
    gaps = [b - a for a, b in zip(vce, vce[1:])]
    left = g.read(0x260, 1)[0]
    return {'writes': len(vce), 'first': (vce[0] - vbl) / LINE if vce else 0,
            'end': (vce[-1] - vbl) / LINE if vce else 0,
            'median_gap': statistics.median(gaps) if gaps else 0,
            'big_gaps': sorted(gaps)[-4:], 'left': left}


def main():
    rom, flags = sys.argv[1], int(sys.argv[2], 0)
    with Session(rom, flags) as g:
        cv.start_stage(g, 0)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.run_to('83F3', polls=20000)
        g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        state = g.logdir / 'hook.state'
        g.call('save_state_file', {'file_path': str(state)})
        print('options at the hook', hex(g.read(0x100, 1)[0]), flush=True)
        for name, queue in CASES.items():
            r = measure(g, state, queue)
            print(f'{name:18s} writes {r["writes"]:4d}  first {r["first"]:6.3f}  end {r["end"]:6.3f} lines  '
                  f'median clocks/write {r["median_gap"]:6.1f}  largest gaps {r["big_gaps"]}  left {r["left"]}',
                  flush=True)


if __name__ == '__main__':
    main()
