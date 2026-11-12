"""Exact per-update accounting from an instruction trace: each event's cost = next event clock - its clock.
For each update (waking vblank IRQ1 entry .. STZ $12 at FD67), split: vblank handler (to its RTI), main, other IRQs; and left = next vblank IRQ entry - STZ."""
import gzip, re, sys
from collections import Counter
INS = re.compile(r'^(\d+) @(\d+)\s+\+?(\d*)\s+([0-9A-F]{2}):([0-9A-F]{4})\s+A:.*?S:\w\w\s+\S+\s+(\w+)')
IRQ = re.compile(r'^(\d+) @(\d+).*\[CPU\]\s+IRQ\s+(\S+)')
def events(path):
    ev=[]
    with gzip.open(path,'rt') as fh:
        for ln in fh:
            m=INS.match(ln)
            if m:
                f,clk,cyc,b,pc,op=m.groups(); ev.append((int(clk),b,int(pc,16),op,int(f))); continue
            m=IRQ.match(ln)
            if m: ev.append((int(m.group(2)),'IRQ',m.group(3),'IRQ',int(m.group(1))))
    return ev
def attribute(ev):
    """yield (clock, cost, bank, pc, op, ctx, irq_instance_id)"""
    stack=[]; out=[]; inst=0
    for i,e in enumerate(ev[:-1]):
        cost=ev[i+1][0]-e[0]
        if e[1]=='IRQ':
            inst+=1; stack.append((e[2],inst)); out.append((e[0],cost,'IRQ',e[2],'IRQ',e[2],inst)); continue
        ctx,iid=(stack[-1] if stack else ('main',0))
        out.append((e[0],cost,e[1],e[2],e[3],ctx,iid))
        if e[3]=='RTI' and stack: stack.pop()
    return out
def per_update(path, region=None):
    a=attribute(events(path))
    # vblank handler instance = IRQ1 instance which executes FD1F (INC $12)
    vb=set(r[6] for r in a if r[2]=='00' and r[3]==0xFD1F)
    vbt={}
    for r in a:
        if r[2]=='IRQ' and r[6] in vb: vbt[r[6]]=r[0]
    stz=[r[0] for r in a if ((r[2]=='00' and r[3]==0xFD67) or r[3]==0x37C0) and r[5]=='main']
    vbl=sorted(vbt.items(), key=lambda x:x[1])
    rows=[]
    for s0,s1 in zip(stz,stz[1:]):
        wakes=[(i,t) for i,t in vbl if s0<t<s1]
        if not wakes: continue
        wi,wt=wakes[0]
        nxt=[t for i,t in vbl if t>s1]
        c=Counter(); reg=Counter()
        for r in a:
            if wt<=r[0]<s1:
                k='vblank-wake' if r[6]==wi else ('main' if r[5]=='main' else ('vblank-late' if r[6] in vb else r[5]))
                c[k]+=r[1]
                if region and r[2]!='IRQ': reg[(k,r[2],r[3]&0xff00)]+=r[1]
        rows.append({'wake':wt,'stz':s1,'busy':s1-wt,'left':(nxt[0]-s1) if nxt else None,'n_wakes':len(wakes),**c,'reg':reg})
    return rows
if __name__=='__main__':
    for p in sys.argv[1:]:
        print(p)
        for r in per_update(p):
            print('  wake',r['wake'],'busy',r['busy'],'left',r['left'],'vblanks in update',r['n_wakes'], {k:v for k,v in r.items() if k not in('wake','stz','busy','left','n_wakes','reg')})
