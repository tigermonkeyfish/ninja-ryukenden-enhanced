"""Trace-attributed cycles per update in 5-3 (castle routines by label range).
usage: tprof.py ROM LABEL [--area N] [--step PX] [--skip N] [--updates N]"""
import argparse, json, re, sys
from collections import Counter
sys.path.insert(0, __import__('os').path.dirname(__file__))
from reach import *
import core

ap = argparse.ArgumentParser()
ap.add_argument('rom', type=Path)
ap.add_argument('label')
ap.add_argument('--area', type=int, default=2)
ap.add_argument('--stage', type=int, default=14)
ap.add_argument('--step', type=int, default=2)
ap.add_argument('--skip', type=int, default=0)
ap.add_argument('--updates', type=int, default=40)
ap.add_argument('--detail', action='store_true')
ap.add_argument('--then', type=int, default=0, help='after --skip, reverse and skip this many more')
args = ap.parse_args()
RANGES = [('7C', 0x4A00, 0x4AA5, 'upload'), ('7C', 0x4B00, 0x4BB3, 'stars'), ('7C', 0x4F10, 0x4FC1, 'fixed'),
          ('7C', 0x54AA, 0x5527, 'horizon_start'), ('7C', 0x5527, 0x5A10, 'columns'), ('7C', 0x4319, 0x4400, 'rowplan'), ('7C', 0x4000, 0x6000, 'castle_main'),
          ('00', 0xFCD7, 0xFDC0, 'irq'), ('00', 0xFE00, 0x10000, 'hooks')]
LINE = re.compile(r'@\d+ \+(\d+)\s+([0-9A-F]{2}):([0-9A-F]{4})')


def region(bank, addr, prev):
    if bank == 'F8' and 0x2029 <= addr <= 0x2030:
        return prev
    for b, lo, hi, name in RANGES:
        if bank == b and lo <= addr < hi:
            return name
    return f'{bank}:{addr >> 12:X}xxx'


rows = []
pcs = Counter()
with core.Session(str(SP)) as s:
    sw = reach(s, args.rom, args.stage, args.area)
    ram = s.read(0, 0x2000)
    pages = ram[0x237]; max_cam = max(0, pages * 256 - 256)
    cam = int.from_bytes(ram[0x20f:0x211], 'little')
    direction = 1 if cam <= max_cam // 2 else -1
    for _ in range(args.skip):
        sw.forced_scroll(direction * args.step); sw.next_update()
    if args.then:
        direction = -direction
        for _ in range(args.then):
            sw.forced_scroll(direction * args.step); sw.next_update()
    s.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '5M', 'filters': ['cpu.instructions']})
    for i in range(args.updates):
        sw.forced_scroll(direction * args.step)
        seq0 = s.call('get_trace_log', {'count': 1})['total_logged']
        sw.next_update()
        seq1 = s.call('get_trace_log', {'count': 1})['total_logged']
        upd, prev, start = Counter(), None, seq0
        upc = Counter()
        while start < seq1:
            tr = s.call('get_trace_log', {'start': start, 'count': min(1000, seq1 - start)})
            for line in tr['lines']:
                m = LINE.match(line)
                if m:
                    prev = region(m.group(2), int(m.group(3), 16), prev)
                    upd[prev] += int(m.group(1))
                    if args.detail:
                        pcs[f'{m.group(2)}:{m.group(3)}'] += int(m.group(1))
                        upc[f'{m.group(2)}:{m.group(3)}'] += int(m.group(1))
            start += len(tr['lines'])
            if not tr['lines']:
                break
        cam = int.from_bytes(s.read(0x20f, 2), 'little')
        total = sum(upd.values())
        if args.detail:
            (SP / f'tpc-{args.label}-{i:03}.json').write_text(json.dumps(upc))
        rows.append({'cam': cam, 'frames': round(total / FRAME, 3), **{k: round(v / FRAME, 4) for k, v in upd.most_common()}})
        top = ', '.join(f'{k} {v / FRAME:.3f}' for k, v in upd.most_common(7))
        print(f'cam {cam:4} frames {total / FRAME:.3f} | {top}', flush=True)
(SP / f'tprof-{args.label}.json').write_text(json.dumps(rows))
if args.detail:
    (SP / f'tpcs-{args.label}.json').write_text(json.dumps(pcs))
