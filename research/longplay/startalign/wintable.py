"""start-pos: markdown table of startwin.py results.

    wintable.py OLD.json NEW.json      (startwin.py outputs for the previous build and this one)

Start window = first visible .. the frame before the camera first moves (startwin.py). Columns: the
dark run (load black / area-change transition), the start window, the first differing frame after it,
and whether the previous build was the same.
"""
import json, sys
from capture import EVENTS
LABEL = {1:'1-1 start',2846:'1-2 a0',10151:'2-1 a0',11343:'2-1 a1',12421:'2-1 a2',12546:'2-1 a3',13256:'2-2 a0',14030:'2-2 a1',14671:'2-2 a2',16547:'2-3 a0',27793:'3-1 a0',31416:'3-2 a0',34867:'3-3 a0',53302:'4-1 a0',55309:'4-1 a1',55429:'4-1 a2',57134:'4-2 a0',60369:'4-3 a0',60708:'4-3 a1',61795:'4-3 a2',63544:'4-3 a3',64436:'4-4 a0',70025:'5-1 a0',73278:'5-2 a0',74531:'5-2 a1',75459:'5-2 a2',76157:'5-2 a3',77219:'5-3 a0',77972:'5-3 a1',78669:'5-3 a2',79287:'5-3 a3',80296:'5-3 a4',80630:'5-3 a5',80887:'5-3 a6',82897:'5-4 a0',86521:'6-1 a0',88458:'6-2 a0',90754:'6-2 a1',91716:'6-2 a2',91820:'6-2 a3',92931:'6-2 a4',93822:'6-3 a0',94460:'6-3 a1',94579:'6-3 a2',96625:'6-3 a3',102317:'6-4A a0',106481:'6-4B a0',111242:'6-4C a0'}

old, new = (json.load(open(p)) for p in sys.argv[1:3])
print('| # | Event | Frame | Camera | Dark run (frames) identical | First visible | Camera first moves | Start window frames | Start window identical | First differing frame from first visible | Previous build |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for n, ev in enumerate(EVENTS, 1):
    a, b = old[str(ev)], new[str(ev)]
    keys = ('dark_identical', 'window_identical', 'first_diff_from_visible')
    prev = 'same' if all(a[k] == b[k] for k in keys) else 'dark %s, window %s' % (
        'yes' if a['dark_identical'] else 'NO', 'yes' if a['window_identical'] else 'NO')
    dark = (b['first_visible'] - b['dark_from']) if ev != 1 else 0
    print(f"| {n} | {LABEL[ev]} | {ev} | {b['camera']} | {dark}: {'yes' if b['dark_identical'] else 'NO'} | "
          f"{b['first_visible']} | {b['first_move'] or 'not in window'} | {b['window_frames']} | "
          f"{'yes' if b['window_identical'] else 'NO'} | {b['first_diff_from_visible'] or '-'} | {prev} |")
