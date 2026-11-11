"""Where is the main loop when the vblank interrupt comes, FRAMES frames
after entering STAGE? Stops at the interrupt entry ($FCD7) a few times and
reads the interrupted PC from the stack. usage: idlepc.py ROM STAGE FRAMES"""
import sys

from gbtools import Session, cv

rom, stage, frames = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
with Session(rom, 0x10) as g:
    cv.start_stage(g, stage)
    g.checked_step(frames)
    g.call('set_breakpoint', {'address': '1cd7', 'memory_area': 'rom', 'execute': True})
    for _ in range(12):
        g.run_to('FCD7', polls=40000)
        st = g.call('get_huc6280_status')
        s = int(st['S'], 16)
        stack = g.read(0x100 + s + 1, 3)
        vdc = g.call('get_huc6270_status')
        print('interrupted PC', f'${stack[2]:02X}{stack[1]:02X}', 'bank', st['MPR'][stack[2] >> 5]['value'],
              str(vdc)[:80])
