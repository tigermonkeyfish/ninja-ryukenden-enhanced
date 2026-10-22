"""Real input: hold right (and jump repeatedly) through a stage area and record
the camera per frame and per-update frame counts.
usage: runspeed.py ROM LABEL STAGE FRAMES [jump]"""
import sys, struct
from pathlib import Path
import core
import local
FRAME = 358995   # master clocks per frame: 1365 x 263 lines (HuC6260)
rom, label, stage, nf = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
jump = len(sys.argv) > 5
SP = local.WORK / f'run-{label}'
SP.mkdir(exist_ok=True)
with core.Session(str(SP)) as s:
    core.boot_to_gameplay(s, rom, log=lambda m: None)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(120)
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    core.run_to_hook(s)
    s.write(0x325e, bytes([0xea] * 3), area=3)
    core.jump_to_stage(s, stage)
    s.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    s.step(90)
    s.write(0x100, bytes([s.read(0x100, 1)[0] | 2]))     # No Damage: keep running through enemies
    s.button('right', 'press')
    cams, upd = [], []
    last_counter = None
    for f in range(nf):
        if jump and f % 40 == 0: s.button('II', 'press')
        if jump and f % 40 == 20: s.button('II', 'release')
        s.step(1)
        r = s.read(0, 0x300)
        cams.append(int.from_bytes(r[0x20f:0x211], 'little'))
        if f % 150 == 0: print(label, 'frame', f, 'cam', cams[-1], 'x', s.read(0xe9e, 2).hex(), 'lives', s.read(0xeaf, 1).hex(), flush=True)
    s.button('right', 'release')
    d = [cams[i + 1] - cams[i] for i in range(len(cams) - 1)]
    print(label, 'camera from', cams[0], 'to', cams[-1], '| max step per frame', max(d), '| steps histogram', {v: d.count(v) for v in sorted(set(d))})
