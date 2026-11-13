import sys,json
sys.path.insert(0,'/workspace/.claude/worktrees/longplay/scripts')
from longplay_lib import *
d=Path('/workspace/build/longplay/w'); d.mkdir(exist_ok=True)
full=json.load(open('/workspace/.claude/worktrees/longplay/research/longplay/full.json'))
part=json.load(open(sys.argv[1]))
with Game(EMULATOR,d) as g:
    boot_to_first_update(g,ROM,'original',d/'entered.state')
    play_segments(g,full['segments']+part['segments']); g.press(set()); g.checked_step(1)
    r=g.read(0,0x1000)
    print('x',int.from_bytes(r[0xe9e:0xea0],'little'),'y',r[0xea0],'area',r[0xe60],'cam',int.from_bytes(r[0x20f:0x211],'little'),'pages',r[0x237],'hp',r[0xead])
    open('/workspace/build/longplay/shot.png','wb').write(g.screenshot())
    g.call('save_state_file',{'file_path':'/workspace/build/longplay/stuck.state'})
