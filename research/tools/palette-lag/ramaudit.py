#!/usr/bin/env python3
"""RAM audit: read/write watch on candidate spans; scenario = boot | run:NAME | stage:N."""
import sys, json
sys.path.insert(0,'/workspace/.claude/worktrees/palette-lag/scripts')
from palette_lag import *
from comparison_video import boot
SPANS=[(0x3400,0x37ff),(0x3c00,0x3fff),(0x3234,0x33ff)]
import os
if os.environ.get('CONTROL'): SPANS=[(0x2e55,0x2e5e)]
rom=Path(sys.argv[1]); scen=sys.argv[2]
hits={}
def arm(g):
    for lo,hi in SPANS:
        if (lo,hi) in hits: continue
        g.call('set_breakpoint_range', {'start_address': f'{lo:04x}', 'end_address': f'{hi:04x}','memory_area':'cpu_addr','read':True,'write':True})
def step(g, frames=1):
    r=g.step(frames)
    if r is None:
        st=g.call('get_huc6280_status')
        bp=g.call('list_breakpoints')
        # identify span by trying: record PC; remove all range bps and re-arm the rest after recording
        hits[('stop',len(hits))]={'pc':st['PC'],'mpr':[m['value'] for m in st['MPR']]}
        return False
    return True
frames=0
with Game(EMULATOR, OUT/'work'/'ramaudit') as g:
    if scen=='boot':
        g.call('load_media', {'file_path': str(rom.resolve())}); g.call('debug_pause')
        after=None
        for _ in range(30): g.step(1); frames+=1
        arm(g)
        while frames<12000 and len(hits)<10:
            gp=g.read(0x240,1)[0]==0 and frames>60
            g.press({'run'} if frames%20<2 and not gp and frames>3000 else set())
            if gp and after is None: after=frames
            if after is not None and frames>after+600: break
            if step(g): frames+=1
    else:
        start_point(g, rom, seed_state(), True)
        kind,arg=scen.split(':')
        if kind=='run':
            run=load_run(arg); start_stage(g, run['stage'])
            inputs=[]
            for c,b in run['segments']: inputs+=[frozenset(b)]*c
            inputs+=[frozenset()]*1500
        else:
            start_stage(g, int(arg))
            inputs=[frozenset({'right'})]*200+[frozenset({'right','II'})]*40+[frozenset({'left'})]*200+[frozenset()]*300
        arm(g)
        for b in inputs:
            g.press(set(b))
            while not step(g) and len(hits)<10: pass
            frames+=1
            if len(hits)>=10: break
print(json.dumps({'scen':scen,'frames':frames,'stops':list(hits.values())[:5]}), flush=True)
