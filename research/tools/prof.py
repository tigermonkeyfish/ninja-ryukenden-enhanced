"""Per-update segment timing in 5-3: early hook, game logic, late hook, tail
(to the frame loop's vblank wait at $E0FE) and frames per update.
usage: prof.py ROM LABEL [--area N] [--step PX] [--updates N]"""
import argparse, json, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from reach import *
import core

ap = argparse.ArgumentParser()
ap.add_argument('rom', type=Path)
ap.add_argument('label')
ap.add_argument('--stage', type=int, default=14)
ap.add_argument('--area', type=int, default=2)
ap.add_argument('--step', type=int, default=2)
ap.add_argument('--updates', type=int, default=128)
args = ap.parse_args()
POINTS = {'245D': 'early', '2472': 'logic', '2475': 'late', '00FE': 'tail'}


def wait(s, polls=40000):
    for _ in range(polls):
        st = s.status()
        if st['paused']:
            return st
    raise TimeoutError


rows = []
with core.Session(str(SP)) as s:
    sw = reach(s, args.rom, args.stage, args.area)
    ram = s.read(0, 0x2000)
    pages = ram[0x237]; max_cam = max(0, pages * 256 - 256)
    cam = int.from_bytes(ram[0x20f:0x211], 'little')
    direction = 1 if cam <= max_cam // 2 else -1
    last = None
    for i in range(args.updates):
        sw.forced_scroll(direction * args.step)
        t0 = clock(s, f'clk-{args.label}.state')
        for a in POINTS:
            s.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
        mark = {'start': t0}
        while True:
            s.call('debug_step_into')
            s.call('debug_continue')
            st = wait(s)
            phys = s.cpu()['physical_PC'][-4:].upper()
            if phys in POINTS and POINTS[phys] not in mark:
                mark[POINTS[phys]] = clock(s, f'clk-{args.label}.state')
            if phys == '2457':
                break
        for a in POINTS:
            s.call('remove_breakpoint', {'address': a, 'memory_area': 'rom'})
        end = clock(s, f'clk-{args.label}.state')
        seg = {}
        prev = t0
        for k in ('early', 'logic', 'late', 'tail'):
            if k in mark:
                seg[k] = round((mark[k] - prev) / FRAME, 3); prev = mark[k]
        seg['busy'] = round((mark.get('tail', end) - t0) / FRAME, 3)
        seg['frames'] = round((end - t0) / FRAME, 2)
        seg['cam'] = int.from_bytes(s.read(0x20f, 2), 'little')
        rows.append(seg)
(SP / f'prof-{args.label}.json').write_text(json.dumps(rows))
late = [r for r in rows if r['frames'] > 1.5]
print(args.label, 'updates', len(rows), 'late', len(late))
for k in ('early', 'logic', 'late', 'tail', 'busy'):
    v = [r.get(k, 0) for r in rows]
    print(f'  {k}: max {max(v):.3f} mean {sum(v) / len(v):.3f}')
for r in late[:12]:
    print('  late update', r)
