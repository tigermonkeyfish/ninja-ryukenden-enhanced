import sys,json
sys.path.insert(0,'/workspace/.claude/worktrees/longplay/scripts')
from longplay_lib import *
d=Path('/workspace/build/longplay/w'); d.mkdir(exist_ok=True)
full=json.load(open('/workspace/.claude/worktrees/longplay/research/longplay/full.json'))
btn=sys.argv[1] if len(sys.argv)>1 else ''
with Game(EMULATOR,d) as g:
    boot_to_first_update(g,ROM,'original',d/'entered.state')
    f=0
    play_segments(g,full['segments']); f=sum(n for n,_ in full['segments'])
    prev=None
    for i in range(1,8000):
        g.press(set()); g.checked_step(1)
        r=g.read(0,0x1000)
        s=(r[0x240],r[0x241],r[0xe5f],r[0xe60],r[0xeaf])
        if s!=prev: print(f+i,s,r[0],r[0xead],r[0xe9e:0xea1].hex()); prev=s
