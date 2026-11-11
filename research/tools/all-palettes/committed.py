"""Is an area change already decided at a frame? (research reference, not a
maintained tool). Replays stored run RUN to FRAME (as check_menu's sweep:
inputs 0..FRAME stepped), then plays N more frames with the run's own
inputs, with no buttons and with Left held, each from the same state, and
reports the frame of the next area change ($2E60) in each and a few fields
per frame (Ryu state $2EAB, $2E63, Ryu X $2E9F, camera $220F).
usage: committed.py ROM RUN FRAME,FRAME,... N"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
from gbtools import Session, cv, load_run  # noqa: E402

rom, run_name, frames, n = sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3].split(',')], int(sys.argv[4])
run = load_run(run_name)
inputs = [b for count, b in run['segments'] for _ in range(count)]
for frame in frames:
    with Session(rom, 0) as g:
        cv.start_stage(g, run['stage'])
        for buttons in inputs[:frame + 1]:
            g.press(set(buttons))
            g.step(1)
        state = Path(g.logdir) / 'at.state'
        g.call('save_state_file', {'file_path': str(state)})
        area0 = g.read(0xe60, 1)[0]
        for label, plan in (('run', inputs[frame + 1:frame + 1 + n]), ('none', [()] * n), ('left', [('left',)] * n)):
            g.call('load_state_file', {'file_path': str(state)})
            g.held = set()
            change, rows = None, []
            for k, buttons in enumerate(plan):
                g.press(set(buttons))
                g.step(1)
                ram = g.read(0, 0x1000)
                rows.append(f"{ram[0xeab]}/{ram[0xe63]}/{ram[0xe9f]}/{ram[0x20f] | ram[0x210] << 8}")
                if change is None and ram[0xe60] != area0:
                    change = frame + 1 + k
            print(run_name, frame, label, 'area change at', change, 'inputs', [''.join(b) for b in plan[:6]],
                  'ryu/e63/x/cam', rows[:7], flush=True)
