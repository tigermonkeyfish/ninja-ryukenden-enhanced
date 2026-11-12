import sys, json, time, shutil
sys.stdout.reconfigure(line_buffering=True)
sys.path.insert(0, '/workspace/.claude/worktrees/palette-video/scripts')
from pathlib import Path
import palette_video as pv
from comparison_video import Game, start_point
EM='/workspace/build/toolchain/geargrafx/platforms/linux/geargrafx'
W=Path('/workspace/build/palette-video/work'); B=W/'beam'
if B.exists(): shutil.rmtree(B)
B.mkdir()
OPT=int(sys.argv[1]); WIDTH=int(sys.argv[2]); GOALX=int(sys.argv[3]); OUT=sys.argv[4]
run=json.loads(Path('/workspace/.claude/worktrees/palette-video/research/comparison-runs/2-2.json').read_text())
inputs=[]
for c,b in run['segments']: inputs+=[frozenset(b)]*c
F0=1098
pre=[frozenset(p) for p in json.load(open('prefix1.json'))]
ACT=[]
for a in (['left'],['left','I'],['left','I','II'],['II','left'],['I'],[],['right'],['right','I'],['II']):
    for d in (4,8,12,18):
        ACT.append((tuple(a),d))
def rd(g):
    ram=g.read(0,0x2000)
    return dict(x=int.from_bytes(ram[0xe9e:0xea0],'little'),y=ram[0xea0],st=ram[0xeab],h=ram[0xead],lives=ram[0xeaf],area=ram[0xe60],wheel=5 in ram[0x110e:0x1113],master=ram[0x240])
with Game(EM,W/'bm') as g:
    start_point(g,'/workspace/build/palette-video/enh.pce',W/'start.state',True)
    pv.enter_stage(g,3,'original',OPT)
    for n in range(F0):
        g.press(set(inputs[n])); g.checked_step(1)
    for b in pre:
        g.press(set(b)); g.checked_step(1)
    s0=rd(g); print('start',s0)
    g.call('save_state_file',{'file_path':str(B/'n0.state')})
    beam=[(0,'n0',[],s0)]; cnt=1; lives0=s0['lives']
    for level in range(60):
        cand=[]
        for score,name,plan,st in beam:
            for a,d in ACT:
                g.call('load_state_file',{'file_path':str(B/f'{name}.state')}); g.held=set()
                g.press(set(a))
                for _ in range(d): g.checked_step(1)
                s=rd(g)
                if s['lives']!=lives0 or s['h']==0 or s['master']!=0 or s['area'] not in (1,2) or s['y']>150 or not s['wheel'] and len(plan)>0 and False: continue
                cand.append(((-1000 if s['area']==2 else s['x'])+0.02*len(plan),a,d,name,plan,s))
        cand.sort(key=lambda c:c[0])
        seen=set(); new=[]
        for sc,a,d,name,plan,s in cand:
            key=(s['x']//6,s['y']//10,s['st'])
            if key in seen: continue
            seen.add(key)
            nn=f'n{cnt}'; cnt+=1
            g.call('load_state_file',{'file_path':str(B/f'{name}.state')}); g.held=set()
            g.press(set(a))
            for _ in range(d): g.checked_step(1)
            g.call('save_state_file',{'file_path':str(B/f'{nn}.state')})
            new.append((sc,nn,plan+[(a,d)],s))
            if len(new)>=WIDTH: break
        for sc,nn,plan,s in beam:
            if sc==0 and False: pass
        for _,nm,_,_ in beam:
            (B/f'{nm}.state').unlink(missing_ok=True)
        beam=new
        if not beam: print('beam empty'); break
        print(level,'best',beam[0][3],'frames',sum(d for a,d in beam[0][2]),flush=True)
        json.dump([(list(a),d) for a,d in beam[0][2]],open(OUT,'w'))
        if beam[0][3]['x']<=GOALX or beam[0][3]['area']==2:
            json.dump([(list(a),d) for a,d in beam[0][2]],open(OUT,'w')); print('GOAL',beam[0][3]); break
