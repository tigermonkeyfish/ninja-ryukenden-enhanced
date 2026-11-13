import sys,json,itertools
sys.path.insert(0,'/workspace/.claude/worktrees/longplay/scripts')
from longplay_lib import *
d=Path('/workspace/build/longplay/w'); d.mkdir(exist_ok=True)
state=sys.argv[1]; fwd=sys.argv[2]
def info(g):
    r=g.read(0,0x1000)
    return (int.from_bytes(r[0xe9e:0xea0],'little'),r[0xea0],r[0xe60],r[0xead],r[0xe5f])
with Game(EMULATOR,d) as g:
    boot_to_first_update(g,ROM,'original',d/'entered.state')
    g.call('load_state_file',{'file_path':state}); g.held=set(); g.press(set())
    s0=info(g); print('start',s0)
    res=[]
    F={fwd}
    for a,b,c,att in itertools.product([0,3,6],[6,10,14,18,24],[0,8,16,28],[0,1]):
        g.call('load_state_file',{'file_path':state}); g.held=set(); g.press(set())
        segs=[]
        if a: segs.append((a,F))
        segs.append((b,F|{'I'}|({'II'} if att else set())))
        if c: segs.append((c,F))
        segs.append((50,set()))
        for n,btn in segs:
            g.press(set(btn)); g.step(n)
        i=info(g)
        res.append((i,(a,b,c,att)))
    res.sort(key=lambda t:(t[0][2],t[0][0] if fwd=='right' else -t[0][0]),reverse=True)
    for r in res[:12]: print(r)
