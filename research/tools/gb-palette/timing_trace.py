"""Vblank palette-upload and HUD-split timing over a whole stored run, from
the emulator's hardware-event trace (no breakpoints, so the replay is the
same as record.py's): VDC vblank and scanline (RCR) interrupts, the CPU's
interrupt entries and every VCE colour write, all in master clocks.

Per frame (one frame step) it logs, in lines after the vblank interrupt
(1 line = 1365 master clocks):
  'vl'  CPU entry latency of the vblank interrupt,
  'n'   VCE colour writes between vblank and the scanline interrupt,
  'end' the last of them (0 if none),
  'rcr' when the VDC raised the scanline interrupt, 'cpu' when the CPU took it
        (its handler writes BYR a fixed number of cycles later),
and the stage timer, camera and Ryu state for the update-count check.
usage: timing_trace.py ROM RUN OUT.json FLAGS|orig"""
import json
import re
import sys
from pathlib import Path

from gbtools import Session, cv, h, load_run

LINE = 1365
EVENT = re.compile(r'@(\d+)\s.*?\[(VCE|VDC1|CPU)\]\s+(\S+)\s+(\S+)?')


def main():
    rom, run_name, out = sys.argv[1:4]
    flags = None if sys.argv[4] == 'orig' else int(sys.argv[4], 0)
    run = load_run(run_name)

    def once():
        frames = []
        with Session(rom, flags) as g:
            cv.start_stage(g, run['stage'])
            g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                                     'filters': ['cpu.irqs', 'vdc.irqs', 'vce.registers']})
            pos = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
            events = []
            n = 0
            for count, buttons in run['segments'] + [[60, []]]:
                g.press(set(buttons))
                for _ in range(count):
                    g.checked_step(1)
                    end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
                    while pos < end:
                        chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
                        lines = chunk.get('entries') or chunk.get('lines') or []
                        if not lines:
                            raise RuntimeError(f'trace read stalled at {pos}: {list(chunk)}')
                        for ln in lines:
                            text = ln if isinstance(ln, str) else ln.get('text', '')
                            m = EVENT.match(text)
                            if m:
                                events.append((int(m.group(1)), m.group(2), m.group(3), m.group(4) or ''))
                        pos += len(lines)
                    ram = g.read(0, 0x1000)
                    frames.append({'f': n, 'timer': ram[0xeda:0xede].hex(), 'ryu': ram[0xe9e:0xeb8].hex(),
                                   'cam': int.from_bytes(ram[0x20f:0x211], 'little'), 'area': ram[0xe60],
                                   'master': ram[0x240], 'stage': ram[0xe5f], 'events_upto': len(events),
                                   'sat': h(g.read(0, 512, area=6))})
                    n += 1
        return frames, events

    frames, events = cv.retried(once)
    # Split the event stream at each VDC vblank interrupt.
    vbl = [i for i, e in enumerate(events) if e[1] == 'VDC1' and e[2] == 'VBLANK']
    windows = []
    for k, i in enumerate(vbl):
        t0 = events[i][0]
        stop = vbl[k + 1] if k + 1 < len(vbl) else len(events)
        seg = events[i:stop]
        cpu = [e[0] for e in seg if e[1] == 'CPU' and e[2] == 'IRQ' and e[3] == 'IRQ1']
        rcr = next((e[0] for e in seg if e[1] == 'VDC1' and e[2] == 'SCANLINE'), None)
        vce = [e[0] for e in seg if e[1] == 'VCE' and e[2] == 'COLOR' and (rcr is None or e[0] < rcr)]
        cpu_rcr = next((c for c in cpu if rcr is not None and c >= rcr), None)
        windows.append({'t': t0, 'vl': round((cpu[0] - t0) / LINE, 3) if cpu else None,
                        'n': len(vce), 'end': round((vce[-1] - t0) / LINE, 3) if vce else 0,
                        'rcr': round((rcr - t0) / LINE, 3) if rcr else None,
                        'cpu': round((cpu_rcr - t0) / LINE, 3) if cpu_rcr else None})
    Path(out).write_text(json.dumps({'frames': frames, 'vblanks': windows}))
    worst_end = max((w['end'] for w in windows), default=0)
    worst_cpu = max((w['cpu'] for w in windows if w['cpu']), default=0)
    print(Path(rom).name, run_name, sys.argv[4], len(frames), 'frames', len(windows), 'vblanks',
          'worst upload end', worst_end, 'worst split entry', worst_cpu, flush=True)


if __name__ == '__main__':
    main()
