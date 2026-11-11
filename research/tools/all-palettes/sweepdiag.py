"""Diagnose a check_menu sweep case (research reference, not a maintained
tool): replay stored run RUN to frame FRAME (fresh session from the shared
start state, $2100 = FLAGS), press Select there and run check_menu's sweep
cycle (exact_cycle with the sweep's actions), then step N frames after the
menu's return and the same N frames of the run without the menu (pad bytes
as the menu left them; with SAME_MUSIC=1 also the music driver's RAM).
For every frame end of both: where the CPU is (PC; 'wait' when in the
main loop's vblank wait $FD67-$FD6F, i.e. the update finished), the
VRAM/SAT/VCE hashes and, where they differ, the differing VRAM words
(ranges) and SAT/VCE entries; the frame counter, area, Ryu state and the
area-change fields (ALIGN=hook: both from the next update's Select hook
$FF73 instead of from the return; ALIGN=vblank: from the next vblank
interrupt $FCD7, as check_menu does); and the timer interrupts (CPU IRQ2) and VDC interrupts
in the frame from the trace log, in master clocks after the frame's vblank;
and the PSG state (get_psg_status: per channel enable, amplitude,
frequency, balance, waveform, noise; main amplitude) at each frame end.
usage: sweepdiag.py ROM RUN FRAME FLAGS N OUT.json"""
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault('GB_WORK', '/workspace/build/all-palettes')
sys.path.insert(0, str(HERE.parent / 'gb-palette'))
sys.path.insert(0, str(HERE.parents[2] / 'scripts'))
from gbtools import Session, cv, load_run  # noqa: E402
import check_menu as CM  # noqa: E402

EVENT = re.compile(r'^\s*(\d+)\s+(\S+)\s+(\S+)\s*(\S*)')
LINE = 1365


def ranges(idx):
    out = []
    for i in idx:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def trace_on(g):
    g.call('set_trace_log', {'enabled': True, 'output': 'memory', 'memory_size': '1M',
                             'filters': ['cpu.irqs', 'vdc.irqs']})
    return g.call('get_trace_log', {'count': 1}).get('total_logged', 0)


def trace_read(g, pos):
    end = g.call('get_trace_log', {'count': 1}).get('total_logged', 0)
    events = []
    while pos < end:
        chunk = g.call('get_trace_log', {'start': pos, 'count': 1000})
        lines = chunk.get('entries') or chunk.get('lines') or []
        if not lines:
            break
        for ln in lines:
            text = ln if isinstance(ln, str) else ln.get('text', '')
            m = EVENT.match(text)
            if m:
                events.append((int(m.group(1)), m.group(2), m.group(3), m.group(4)))
        pos += len(lines)
    return pos, events


def frame_states(g, n):
    """n whole frames from a normalized state: per frame the video state and CPU."""
    state = Path(g.logdir) / 'diag.state'
    g.call('save_state_file', {'file_path': str(state)})
    g.call('load_state_file', {'file_path': str(state)})
    pos = trace_on(g)
    out = []
    for _ in range(n):
        g.checked_step(1)
        pos, ev = trace_read(g, pos)
        cpu = g.call('get_huc6280_status')
        ram = g.read(0, 0x2000)
        vbl = [e[0] for e in ev if e[1].startswith('VDC') and e[2] == 'VBLANK']
        t0 = vbl[0] if vbl else (ev[0][0] if ev else 0)
        psg = g.call('get_psg_status')
        out.append({'psg': [(c['enabled'], c['amplitude'], c['frequency'], c['vol_left'], c['vol_right'],
                             c['wave_index'], c['noise']) for c in psg['channels']] + [psg['main_amplitude']],
                    'pc': cpu['PC'], 'wait': 0xfd67 <= int(cpu['PC'], 16) <= 0xfd6f, 'sp': cpu['SP'],
                    'vram': g.read(0, 0x10000, area=4), 'sat': g.read(0, 512, area=6),
                    'vce': g.read(0, 1024, area=8), 'png': g.screenshot(),
                    'ram': ram, 'fields': {'area': ram[0xe60], 'ryu': ram[0xeab], 'e63': ram[0xe63],
                                           'e45': ram[0xe45], 'lock': ram[0x283], 'cr': ram[0x0e]},
                    'irqs': [(e[1], e[2], e[3], round((e[0] - t0) / LINE, 2)) for e in ev
                             if not (e[1] == 'CPU' and e[3] == 'IRQ1')]})
    return out


def main():
    rom, run_name, frame, flags, n, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4], 0), \
        int(sys.argv[5]), Path(sys.argv[6])
    same_music = os.environ.get('SAME_MUSIC') == '1'
    run = load_run(run_name)
    inputs = [b for count, b in run['segments'] for _ in range(count)]
    with Session(rom, flags) as g:
        cv.start_stage(g, run['stage'])
        for buttons in inputs[:frame + 1]:
            g.press(set(buttons))
            g.step(1)
        work = Path(g.logdir)
        if not CM.select_at_hook(g):
            raise SystemExit('no update saw Select')
        sp = int(g.call('get_huc6280_status')['SP'], 16) - 0x2000
        state = work / 'cycle.state'
        g.call('save_state_file', {'file_path': str(state)})
        at_hook = g.call('get_huc6280_status')
        hook_ram = g.read(0, 0x2000)
        if not CM.opens(g):
            raise SystemExit('refused')
        g.press(set())
        g.step(4)
        open_psg = g.call('get_psg_status')
        open_psg = [(c['enabled'], c['amplitude']) for c in open_psg['channels']] + [open_psg['main_amplitude']]
        print('PSG while the menu is open (enabled, amplitude):', open_psg, flush=True)
        for button in ['down', 'right', 'down', 'right']:
            g.press({button})
            g.step(2)
            g.press(set())
            g.step(3)
        g.press({'select'})
        g.step(2)
        g.press(set())
        pc = CM.run_until(g, [CM.HOOK_RETURN])
        after = g.read(0, 0x2000)
        pad = after[0xe55:0xe5f]
        music_diff = [f'${0x2000 + i:04x}:{hook_ram[i]:02x}>{after[i]:02x}' for i in list(range(0x80, 0x90)) +
                      list(range(0x1800, 0x1c00)) if hook_ram[i] != after[i]]
        print('music RAM at the return against the hook:', len(music_diff), music_diff[:40], flush=True)
        align = os.environ.get('ALIGN') == 'hook'
        if align:
            # Compare from the next update's hook in both runs (update-aligned).
            CM.stop_at(g, CM.HOOK_AFTER_DRAW)
        elif os.environ.get('ALIGN') == 'vblank':
            CM.run_until(g, [CM.VBLANK_ENTRY])
        menu = frame_states(g, n)
        g.call('load_state_file', {'file_path': str(state)})
        g.held = set()
        g.write(0xe55, pad)
        if same_music:
            g.write(0x080, after[0x080:0x090])
            g.write(0x1800, after[0x1800:0x1c00])
        CM.stop_at(g, CM.HOOK_RETURN)
        if align:
            CM.stop_at(g, CM.HOOK_AFTER_DRAW)
        elif os.environ.get('ALIGN') == 'vblank':
            CM.run_until(g, [CM.VBLANK_ENTRY])
        ref = frame_states(g, n)
    report = {'rom': rom, 'run': run_name, 'frame': frame, 'flags': flags, 'same_music': same_music,
              'menu_returned_at': pc, 'hook_cpu': at_hook,
              'music_diff_at_return': music_diff, 'frames': []}
    for k, (a, b) in enumerate(zip(menu, ref)):
        e = {'k': k, 'menu': {x: a[x] for x in ('pc', 'wait', 'sp', 'fields', 'irqs', 'psg')},
             'ref': {x: b[x] for x in ('pc', 'wait', 'sp', 'fields', 'irqs', 'psg')},
             'picture_same': a['png'] == b['png'],
             'psg_differs': [c for c, (x, y) in enumerate(zip(a['psg'], b['psg'])) if x != y]}
        for area in ('vram', 'sat', 'vce'):
            if a[area] != b[area]:
                words = [i // 2 for i in range(0, len(a[area]), 2) if a[area][i:i + 2] != b[area][i:i + 2]]
                e[area] = [[f'{lo:04x}', f'{hi:04x}'] for lo, hi in ranges(words)][:24]
                e[area + '_words'] = len(words)
        dram = [i for i in range(0x2000) if a['ram'][i] != b['ram'][i] and not CM.allowed(i, 0x2000 + sp)]
        e['ram_differs'] = [f'${0x2000 + i:04x}' for i in dram][:24]
        report['frames'].append(e)
        print(k, 'menu', a['pc'], 'wait' if a['wait'] else 'BUSY', 'ref', b['pc'], 'wait' if b['wait'] else 'BUSY',
              'same' if not any(x in e for x in ('vram', 'sat', 'vce')) else
              {x: e[x + '_words'] for x in ('vram', 'sat', 'vce') if x in e},
              'pic same' if e['picture_same'] else 'pic DIFF', 'ram', e['ram_differs'][:6],
              'psg same' if not e['psg_differs'] else 'PSG DIFF ' + str(e['psg_differs']), flush=True)
    out.write_text(json.dumps(report, indent=1, default=str))


if __name__ == '__main__':
    main()
