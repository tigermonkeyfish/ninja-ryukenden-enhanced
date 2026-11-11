"""Stage loads in a palette mode (evidence c): with the hardware-event trace
on, enter each stage from the 1-1 main-loop hook as Level Select does
(start_stage: the native load and fade-in, to the first update), then step
FRAMES more frames. Reports the number of vblanks from the hook to the first
update (the load's length), and the worst vblank upload end, upload count
and HUD-split CPU entry (lines after vblank) over the load and the frames.
usage: entry_timing.py ROM FLAGS FRAMES STAGES(comma) OUT.json [SETTLE_FRAMES]"""
import json
import re
import sys
from pathlib import Path

from gbtools import Session, cv

LINE = 1365
EVENT = re.compile(r'@(\d+)\s.*?\[(VCE|VDC1|CPU)\]\s+(\S+)\s+(\S+)?')


def read_events(g, pos):
    end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    events = []
    while pos < end:
        chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
        lines = chunk.get('entries') or chunk.get('lines') or []
        if not lines:
            raise RuntimeError('trace read stalled')
        for ln in lines:
            m = EVENT.match(ln if isinstance(ln, str) else ln.get('text', ''))
            if m:
                events.append((int(m.group(1)), m.group(2), m.group(3), m.group(4) or ''))
        pos += len(lines)
    return events, pos


def windows(events):
    vbl = [i for i, e in enumerate(events) if e[1] == 'VDC1' and e[2] == 'VBLANK']
    out = []
    for k, i in enumerate(vbl):
        t0 = events[i][0]
        seg = events[i:vbl[k + 1] if k + 1 < len(vbl) else len(events)]
        rcr = next((e[0] for e in seg if e[1] == 'VDC1' and e[2] == 'SCANLINE'), None)
        cpu = [e[0] for e in seg if e[1] == 'CPU' and e[3] == 'IRQ1']
        vce = [e[0] for e in seg if e[1] == 'VCE' and e[2] == 'COLOR' and (rcr is None or e[0] < rcr)]
        out.append({'n': len(vce), 'end': round((vce[-1] - t0) / LINE, 3) if vce else 0,
                    'vl': round((cpu[0] - t0) / LINE, 3) if cpu else None,
                    'cpu': round((next((c for c in cpu if rcr and c >= rcr), rcr) - t0) / LINE, 3) if rcr else None})
    return out


def main():
    rom, flags, frames = sys.argv[1], int(sys.argv[2], 0), int(sys.argv[3])
    stages = [int(s) for s in sys.argv[4].split(',')]
    settle = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    result = {}
    for stage in stages:
        with Session(rom, flags) as g:
            if settle:
                # Let the mode settle (its first vblank re-uploads all 512
                # colours) before the load, then back to the main-loop hook.
                g.checked_step(settle)
                g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
                g.run_to('83F3', polls=20000)
                g.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
                state = g.logdir / 'settled.state'
                g.call('save_state_file', {'file_path': str(state)})
                g.call('load_state_file', {'file_path': str(state)})
            g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                                     'filters': ['cpu.irqs', 'vdc.irqs', 'vce.registers']})
            pos = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
            cv.start_stage(g, stage)
            load, pos = read_events(g, pos)
            g.checked_step(frames)
            after, pos = read_events(g, pos)
        wl, wa = windows(load), windows(after)
        allw = wl + wa
        result[cv.STAGE_NAMES[stage]] = {
            'load_vblanks': sum(1 for e in load if e[1] == 'VDC1' and e[2] == 'VBLANK'),
            'worst_end': max(w['end'] for w in allw), 'max_writes': max(w['n'] for w in allw),
            'worst_split_entry': max(w['cpu'] for w in allw if w['cpu']),
            'max_vblank_latency_with_upload': max((w['vl'] for w in allw if w['n'] > 1 and w['vl'] is not None), default=0),
            'uploads_after_line_22': [(i, w) for i, w in enumerate(allw) if w['end'] > 22.0][:5]}
        print(cv.STAGE_NAMES[stage], json.dumps(result[cv.STAGE_NAMES[stage]]), flush=True)
    Path(sys.argv[5]).write_text(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
