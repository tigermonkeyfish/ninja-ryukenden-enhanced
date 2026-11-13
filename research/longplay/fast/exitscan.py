"""Poke-scan an area for exit zones: write Ryu x/y, step 12 frames, see if the area/stage changes (diagnostic only).
Usage: exitscan.py STATE [WIDTH]"""
import sys, json
sys.path.insert(0,'/workspace/.claude/worktrees/longplay/research/longplay/fast')
from fastemu import Fast
f = Fast(); f.load(sys.argv[1]); base = f.save(); i0 = f.info()
W = int(sys.argv[2]) if len(sys.argv) > 2 else i0['pages']*256
hits = []
for x in range(8, W, 16):
    row = ''
    for y in range(8, 200, 16):
        f.load(base)
        f.ram[0xe9e] = x & 255; f.ram[0xe9f] = x >> 8; f.ram[0xea0] = y
        f.step(12, [])
        i = f.info()
        if i['area'] != i0['area'] or i['stage'] != i0['stage'] or i['master']: hits.append((x, y, i['area'], i['stage'], i['master'])); row += 'E'
        elif i['health'] == 0 or i['lives'] < i0['lives']: row += 'x'
        else: row += '.'
    print(f'{x:5d} {row}')
print(hits)
