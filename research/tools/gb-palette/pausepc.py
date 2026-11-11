"""Where is the main loop when the vblank interrupt comes, with the game
paused (Run) at frame AT of a stored run? Stops at the interrupt entry
($FCD7) a few times and reads the interrupted PC from the stack.
usage: pausepc.py ROM RUN AT"""
import sys

from gbtools import Session, cv, load_run

rom, run_name, at = sys.argv[1], sys.argv[2], int(sys.argv[3])
run = load_run(run_name)
inputs = [set(b) for c, b in run['segments'] for _ in range(c)]
with Session(rom, 0x10) as g:
    cv.start_stage(g, run['stage'])
    for f in range(at):
        g.press(inputs[f])
        g.checked_step(1)
    g.press({'run'})
    g.checked_step(2)
    g.press(set())
    g.checked_step(20)
    g.call('set_breakpoint', {'address': '1cd7', 'memory_area': 'rom', 'execute': True})
    for _ in range(6):
        g.run_to('FCD7', polls=40000)
        st = g.call('get_huc6280_status')
        s = int(st['S'], 16)
        stack = g.read(0x100 + s + 1, 3)
        print('interrupted PC', f'${stack[2]:02X}{stack[1]:02X}', 'bank', st['MPR'][(stack[2] >> 5)]['value'])
