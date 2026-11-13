import sys,json
sys.path.insert(0,'/workspace/.claude/worktrees/longplay/scripts')
from longplay_lib import *
d=Path('/workspace/build/longplay/w')
state=sys.argv[1]; wall=sys.argv[2]   # side of the wall: left/right
away='right' if wall=='left' else 'left'
def info(g):
    r=g.read(0,0x1000)
    return (int.from_bytes(r[0xe9e:0xea0],'little'),r[0xea0],r[0xe60],r[0xead])
with Game(EMULATOR,d) as g:
    boot_to_first_update(g,ROM,'original',d/'entered.state')
    for a in (2,3,4,5):
      for b in (8,10,12,14,16):
        g.call('load_state_file',{'file_path':state}); g.held=set(); g.press(set())
        ys=[]
        for k in range(6):
            g.press({away,'I'}); g.step(a); g.press({wall}); g.step(b); g.press(set()); g.step(1)
            ys.append(info(g))
        print(a,b,ys[-1],[y[1] for y in ys])
