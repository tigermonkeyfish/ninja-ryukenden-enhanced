"""Reach every area of a stage without a route: enter the stage by Level
Select, and at each area move the area's exit box ($2E87 page, $2E81/$2E82
point; native test bank 1 $84AB) onto Ryu's current box ($2E9F page,
$2EB5-$2EB8 x, $2EB7-$2EBA y), so the game's own area change runs on the
next update ($8490: inc $2E60, $8503). A debugger intervention (named here):
only the exit box is written; Ryu, camera and enemies are the game's. At
each area: a screenshot (and VCE, SAT) after ENTER frames, then after HOLD
frames holding BUTTONS. Health is refilled each frame (No Damage is the
caller's flag).
usage: areawarp.py ROM FLAGS OUTDIR TAG STAGE[,STAGE..] [ENTER HOLD BUTTONS] [index]"""
import io
import os
import sys
from pathlib import Path

from ntools import Session, cv

rom, flags, out, tag = sys.argv[1], int(sys.argv[2], 0), Path(sys.argv[3]), sys.argv[4]
stages = [int(s) for s in sys.argv[5].split(',')]
enter = int(sys.argv[6]) if len(sys.argv) > 6 else 60
hold = int(sys.argv[7]) if len(sys.argv) > 7 else 120
buttons = set(sys.argv[8].split('+')) if len(sys.argv) > 8 and sys.argv[8] else {'right'}
index = len(sys.argv) > 9 and sys.argv[9] == 'index'
out.mkdir(parents=True, exist_ok=True)
IDENT = b''.join(bytes([i & 0xff, i >> 8]) for i in range(512)).hex(' ')


def save(g, name):
    (out / f'{name}.png').write_bytes(g.screenshot())
    (out / f'{name}.vce').write_bytes(g.read(0, 1024, 8))
    (out / f'{name}.sat').write_bytes(g.read(0, 512, 6))
    if index:
        st = Path(g.logdir) / 'idx.state'
        g.call('save_state_file', {'file_path': str(st)})
        g.call('write_memory', {'area': 8, 'offset': '0000', 'bytes': IDENT})
        g.write(0x283, b'\x01')
        g.checked_step(1)
        (out / f'{name}-index.png').write_bytes(g.screenshot())
        g.call('load_state_file', {'file_path': str(st)})


def frames(g, n, b):
    g.press(b)
    for _ in range(n):
        g.write(0xead, bytes([16]))
        g.checked_step(1)


for stage in stages:
    with Session(rom, flags) as g:
        cv.start_stage(g, stage)
        area = 0
        while True:
            frames(g, enter, set())
            save(g, f'{tag}-ls{stage:02d}-a{area}-start')
            frames(g, hold, buttons)
            save(g, f'{tag}-ls{stage:02d}-a{area}-hold')
            # Exit box onto Ryu: page, then the middle of Ryu's box.
            r = g.read(0xe9f, 1)[0]
            box = g.read(0xeb5, 6)
            g.write(0xe87, bytes([r]))
            g.write(0xe81, bytes([(box[0] + box[3]) // 2, (box[2] + box[5]) // 2]))
            moved = False
            for _ in range(240):
                g.write(0xead, bytes([16]))
                g.checked_step(1)
                ram = g.read(0x240, 1) + g.read(0xe5f, 2)
                if ram[1] != stage or ram[0] != 0:
                    break
                if ram[2] != area:
                    area = ram[2]
                    moved = True
                    break
            print(tag, stage, 'area', area, 'moved' if moved else 'end', flush=True)
            if not moved or area > 12:
                break
