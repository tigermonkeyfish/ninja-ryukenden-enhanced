"""Switching the palette mode at run time (evidence d).

The switch is what a menu row would do: change $2100 bits 3-4 and call the
native full re-queue $F394. Here the debugger writes the bits and calls $F394
by a synthetic JSR at the vblank-wait loop ($FD69), then normalizes the
session with a save and reload (docs/pc-engine/EMULATOR.md).

paused: replay RUN to frame PAUSE_AT, press Run (pause), check the game is
  paused, take the VCE, switch to GB DMG and count the frames until every
  VCE entry equals the table value of its RAM colour, switch back and count
  the frames until the VCE equals the snapshot exactly.
fade: replay RUN into a fade at FADE_AT twice in fresh sessions, a reference
  (same stops, no switch) and a test that switches to GB at FADE_AT and back
  at FADE_AT + HOLD; per frame the test must match map(RAM) while in GB
  (after the stated lag) and the reference VCE exactly after switching back
  (after the lag).
usage: switch.py ROM RUN PAUSE_AT FADE_AT HOLD [SHOTS_DIR]"""
import json
import sys
from pathlib import Path

from gbtools import Session, cv, load_run, ram_palette, vce_words
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table  # noqa: E402

GB = gb_dmg_table()


def frames_of(run):
    out = []
    for count, buttons in run['segments'] + [[600, []]]:
        out += [set(buttons)] * count
    return out


def call_requeue(g):
    """Synthetic JSR to $F394 at the vblank-wait loop, then normalize."""
    g.call('set_breakpoint', {'address': '1d69', 'memory_area': 'rom', 'execute': True})
    g.run_to('FD69', polls=40000)
    g.call('remove_breakpoint', {'address': '1d69', 'memory_area': 'rom'})
    cpu = g.call('get_huc6280_status')
    saved = {k: int(cpu[k], 16) for k in ('A', 'X', 'Y', 'P', 'S')}
    sp = saved['S']
    g.write(0x100 + sp - 1, bytes([0x68, 0xfd]))
    g.reg('S', sp - 2)
    g.reg('PC', 0xf394)
    g.call('set_breakpoint', {'address': '1d69', 'memory_area': 'rom', 'execute': True})
    g.run_to('FD69', polls=40000)
    g.call('remove_breakpoint', {'address': '1d69', 'memory_area': 'rom'})
    for k in ('A', 'X', 'Y', 'P'):
        g.reg(k, saved[k])
    state = Path(g.logdir) / 'norm.state'
    g.call('save_state_file', {'file_path': str(state)})
    g.call('load_state_file', {'file_path': str(state)})


def stop_only(g):
    """The same stop and normalization without a call (reference session)."""
    g.call('set_breakpoint', {'address': '1d69', 'memory_area': 'rom', 'execute': True})
    g.run_to('FD69', polls=40000)
    g.call('remove_breakpoint', {'address': '1d69', 'memory_area': 'rom'})
    state = Path(g.logdir) / 'norm.state'
    g.call('save_state_file', {'file_path': str(state)})
    g.call('load_state_file', {'file_path': str(state)})


def gb_bad(g):
    ram = g.read(0, 0x2000)
    vce, pal = vce_words(g.read(0, 1024, area=8)), ram_palette(ram)
    border = GB[(ram[0x281] | ram[0x282] << 8) & 0x1ff]
    return [i for i in range(512) if vce[i] != GB[pal[i] & 0x1ff] and not (i == 256 and vce[i] == border)]


def set_mode(g, bits):
    opts = g.read(0x100, 1)[0]
    g.write(0x100, bytes([(opts & ~0x18) | bits]))


def paused(rom, run, at, shots):
    inputs = frames_of(run)
    out = {}
    with Session(rom, 0) as g:
        cv.start_stage(g, run['stage'])
        for f in range(at):
            g.press(inputs[f])
            g.checked_step(1)
        g.press({'run'})
        g.checked_step(2)
        g.press(set())
        g.checked_step(20)
        before = g.read(0xe9e, 0x40)
        g.checked_step(10)
        out['paused'] = before == g.read(0xe9e, 0x40)
        vce0 = g.read(0, 1024, area=8)
        if shots:
            (shots / f'switch-{run["name"]}-paused-original.png').write_bytes(g.screenshot())
        set_mode(g, 0x10)
        call_requeue(g)
        lag = None
        for k in range(1, 16):
            g.checked_step(1)
            if not gb_bad(g) and lag is None:
                lag = k
        out['to_gb_frames'] = lag
        out['gb_all_match_after_15'] = not gb_bad(g)
        if shots:
            (shots / f'switch-{run["name"]}-paused-gb.png').write_bytes(g.screenshot())
        set_mode(g, 0)
        call_requeue(g)
        back = None
        for k in range(1, 16):
            g.checked_step(1)
            if g.read(0, 1024, area=8) == vce0 and back is None:
                back = k
        out['back_frames'] = back
        out['back_exact_after_15'] = g.read(0, 1024, area=8) == vce0
        out['still_paused'] = before == g.read(0xe9e, 0x40)
    return out


def fade(rom, run, at, hold):
    inputs = frames_of(run)
    total = at + hold + 40
    ref = []
    with Session(rom, 0) as g:
        cv.start_stage(g, run['stage'])
        for f in range(total):
            if f in (at, at + hold):
                stop_only(g)
            g.press(inputs[f])
            g.checked_step(1)
            ram = g.read(0, 0x2000)
            ref.append((g.read(0, 1024, area=8), ram[0xa8a:0xa97].hex(), ram[0x260], ram[0xeda:0xede]))
    test = []
    with Session(rom, 0) as g:
        cv.start_stage(g, run['stage'])
        for f in range(total):
            if f == at:
                set_mode(g, 0x10)
                call_requeue(g)
            if f == at + hold:
                set_mode(g, 0)
                call_requeue(g)
            g.press(inputs[f])
            g.checked_step(1)
            test.append((g.read(0, 1024, area=8), len(gb_bad(g)), g.read(0xeda, 4)))
    result = {'frames': total, 'switch_to_gb': at, 'switch_back': at + hold,
              'fade_state_at_switch': ref[at][1], 'timers_equal': all(r[3] == t[2] for r, t in zip(ref, test))}
    result['gb_mismatch_counts'] = [t[1] for t in test[at:at + hold]]
    result['vce_differs_from_reference'] = [f for f in range(total) if ref[f][0] != test[f][0]]
    result['reference_queue_counts'] = [r[2] for r in ref[at - 2:at + hold + 10]]
    return result


def main():
    rom, run_name, pause_at, fade_at, hold = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    shots = Path(sys.argv[6]) if len(sys.argv) > 6 else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    run = dict(load_run(run_name), name=run_name)
    print(json.dumps({'run': run_name, 'paused': paused(rom, run, pause_at, shots)}), flush=True)
    print(json.dumps({'run': run_name, 'fade': fade(rom, run, fade_at, hold)}), flush=True)


if __name__ == '__main__':
    main()
