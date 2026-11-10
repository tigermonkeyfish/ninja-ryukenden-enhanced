"""Measure the vblank upload's end line for synthetic queues: at the 1-1
main-loop hook ($83F3), write a queue, run one frame with the hardware-event
trace on and report when the last VCE write of that vblank lands (lines after
the VDC vblank interrupt), the number of writes and the CPU entry latency.
usage: upload_cost.py ROM FLAGS"""
import re
import sys
from gbtools import Session, cv

LINE = 1365
EVENT = re.compile(r'@(\d+)\s.*?\[(VCE|VDC1|CPU)\]\s+(\S+)')
CASES = {
    'one 512': [(0, 512)],
    'one 192': [(0, 192)],
    'one 128': [(0, 128)],
    'one 64': [(0, 64)],
    'one 16': [(16, 16)],
    'one 1': [(16, 1)],
    '256 + 7 singles': [(0, 256)] + [(241 + i, 1) for i in range(7)],
    '8 x 16': [(256 + 16 * i, 16) for i in range(8)],
    '8 x 64': [(64 * i, 64) for i in range(8)],
    '2 x 256': [(0, 256), (256, 256)],
    '8 x 512': [(0, 512)] * 8,
    '3 x 16': [(256, 16), (272, 16), (288, 16)],
}


def main():
    rom, flags = sys.argv[1], int(sys.argv[2], 0)
    with Session(rom, flags) as g:
        cv.start_stage(g, 0)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.run_to('83F3', polls=20000)
        g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        state = g.logdir / 'hook.state'
        g.call('save_state_file', {'file_path': str(state)})
        for name, queue in CASES.items():
            g.call('load_state_file', {'file_path': str(state)})
            q = bytearray(33)
            q[0] = len(queue)
            for k, (idx, n) in enumerate(queue):
                q[1 + k], q[9 + k] = (2 * n) & 0xff, (2 * n) >> 8
                q[17 + k], q[25 + k] = idx & 0xff, idx >> 8
            g.write(0x260, bytes(q))
            g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '100K',
                                     'filters': ['cpu.irqs', 'vdc.irqs', 'vce.registers']})
            start = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
            g.step(2)
            end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
            lines = []
            pos = start
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
            cpu = next(t for t, k, w in ev if k == 'CPU' and t >= vbl)
            rcr = next(t for t, k, w in ev if k == 'VDC1' and w == 'SCANLINE' and t > vbl)
            vce = [t for t, k, w in ev if k == 'VCE' and vbl <= t < rcr]
            r = g.read(0x260, 1)[0]
            first = (vce[0] - vbl) / LINE if vce else 0
            per = (vce[-2] - vce[0]) / max(1, len(vce) - 2) if len(vce) > 2 else 0
            print(f'{name:18s} writes {len(vce):4d}  first {first:6.3f}  end {(vce[-1] - vbl) / LINE:6.3f} '
                  f'lines  latency {(cpu - vbl) / LINE:.3f}  clocks/colour {per:6.1f}  left in queue {r}',
                  flush=True)


if __name__ == '__main__':
    main()
