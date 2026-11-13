#!/usr/bin/env python3
"""Six-mode whole-recording replay with per-frame counters, gameplay fingerprints
and sub-frame clocks at marker frames (emulator evidence only).

    run:     one fresh headless Geargrafx session, power-on with MODE's backup-RAM
             image (menu never opened), the whole recording as one continuous
             input list (no re-syncing, no RAM writes). Every frame it reads the
             8 KiB of RAM and stores: the game-update counter delta ($2000),
             the master flags, stage, area, boss health, and two CRC32
             fingerprints (see CORE and WIDE below). In the frames listed in
             --windows it also arms execution breakpoints at the sound-driver
             command ($38:$4006) and the main-loop update ($2457 = CPU $8457) and
             records their master clocks (palette_lag.step_with_stops).
    compare: reads the six outputs and prints the tables.

    LD_LIBRARY_PATH=/workspace/build/toolchain/sdl3/lib \
      python3 scripts/longplay_six.py run --mode original --file F --out DIR [--windows W.json]
    python3 scripts/longplay_six.py compare DIR
"""
import argparse
import array
import json
import sys
import tempfile
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comparison_video import STAGE_NAMES                                      # noqa: E402
from longplay_lib import EMULATOR, ROM, MODE_BITS, Game, boot_to_first_update, FIRST_UPDATE_ROM  # noqa: E402
import palette_lag as pl                                                      # noqa: E402

ORIGINAL_ROM = Path('/workspace/DO_NOT_COMMIT_ROMS/Ninja Ryukenden (J).pce')   # read-only, never copied
UNMODIFIED = 'unmodified'
MODES = ['original', 'apocalypse', 'nes-a', 'nes-b', 'sms', 'gb dmg', UNMODIFIED]
FRAME = 358995
CLOCK_HZ = 21477270

# RAM offsets (CPU address - $2000).
# CORE: the gameplay state the game itself keeps, no palette or conversion data:
#   counter $2000; master flags $2240-41; camera/pages $220F-10,$2237; stage/area
#   $2E5F-60; Ryu block $2E9E-$2EB7; score/timer $2ED0-$2EDD; boss/enemy/object
#   slots $2F00-$30FF (first enemy slot $2F1C, boss health $3035).
CORE = [(0x000, 0x001), (0x240, 0x242), (0x20f, 0x211), (0x237, 0x238), (0xe5f, 0xe61),
        (0xe9e, 0xeb8), (0xed0, 0xede), (0xf00, 0x1100)]
# WIDE: all of RAM except the palette/conversion/mode areas and the stack page:
#   $2100-$21FF (options byte $2100, palette state $2104, save status $2105, stack
#   and its margin: depth/contents differ with the palette worker's code path),
#   $2260-$2283 palette upload queue/border/lock, $2286-$2A85 RAM palette + backup,
#   $37C0-$37FD WAITR + palette timing + worker scratch, $3C00-$3FFF SHADOW.
EXCLUDED = [(0x100, 0x200), (0x260, 0x284), (0x286, 0xa86), (0x17c0, 0x17fe), (0x1c00, 0x2000)]
WIDE = []
_p = 0
for a, b in EXCLUDED:
    if a > _p:
        WIDE.append((_p, a))
    _p = b
if _p < 0x2000:
    WIDE.append((_p, 0x2000))


def fp(ram, ranges):
    c = 0
    for a, b in ranges:
        c = zlib.crc32(ram[a:b], c)
    return c


def expand(run):
    inputs = []
    for n, buttons in run['segments']:
        inputs += [frozenset(buttons)] * n
    return inputs


def rss(pid):
    try:
        for line in open(f'/proc/{pid}/status'):
            if line.startswith('VmRSS'):
                return int(line.split()[1]) // 1024
    except OSError:
        pass
    return -1


def memory(game):
    import os
    avail = next(int(l.split()[1]) // 1024 for l in open('/proc/meminfo') if l.startswith('MemAvailable'))
    return f'RSS python {rss(os.getpid())} MB, geargrafx {rss(game.emu.proc.pid)} MB, MemAvailable {avail} MB'


def boot_unmodified(game, rom, entered, shortcut=False):
    """longplay_lib.boot_to_first_update for the unpatched HuCard: no backup RAM,
    no settings (patch-only addresses $2100/$2105 are not read). Same title
    handling (Run), same stop at 1-1's first main-loop update ($8457)."""
    game.power_on(rom, None)
    previous, since, presses, pressed, title = None, 0, [200], False, False
    for frame in range(1, 20000):
        game.checked_step(1)
        since += 1
        master = bytes(game.read(0x240, 2))
        if master != previous:
            previous, since = master, 0
        if master == b'\x01\x01':
            title = True
        if shortcut and master == b'\x01\x01' and since in (10, 12, 14, 16):
            # the game's own language switch: hold I + II, tap Select (real input)
            act = {10: [('I', 'press'), ('II', 'press')], 12: [('select', 'press')],
                   14: [("select", "release")], 16: [('I', 'release'), ('II', 'release')]}[since]
            for b, ac in act:
                game.call('controller_button', {'player': 1, 'button': b, 'action': ac})
        if shortcut and master == b'\x01\x01' and since == 30:
            print('language byte after shortcut:', game.read(0x1227, 1)[0], flush=True)
        if master == b'\x01\x01' and since == 180 and not pressed:
            presses.append(frame)
            pressed = True
        if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150 and not title:
            presses.append(frame)
        for p in presses:
            if frame == p:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'press'})
            elif frame == p + 2:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'release'})
        if title and master[0] == 0 and frame > presses[-1] + 2:
            break
    else:
        raise RuntimeError('gameplay not reached')
    status = {'boot_frames': frame, 'presses': presses, 'language': game.read(0x1227, 1)[0], 'shortcut': shortcut}
    game.call('set_breakpoint', {'address': f'{FIRST_UPDATE_ROM:x}', 'memory_area': 'rom', 'execute': True})
    game.run_to('8457', polls=400000)
    game.call('remove_breakpoint', {'address': f'{FIRST_UPDATE_ROM:x}', 'memory_area': 'rom'})
    game.call('save_state_file', {'file_path': str(entered)})
    game.call('load_state_file', {'file_path': str(entered)})
    game.held = set()
    return status


def run_mode(a):
    run = json.loads(a.file.read_text())
    inputs = expand(run)
    total = len(inputs)
    windows = set(json.loads(a.windows.read_text())) if a.windows else set()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    tag = (a.tag or a.mode).replace(' ', '')
    work = Path(tempfile.mkdtemp(prefix='longplay-six-', dir='/workspace/build/longplay'))
    tmp = work / 'clock.state'
    cnt, mas, m2s, stg, are, bos = (array.array('B') for _ in range(6))
    core, wide = array.array('I'), array.array('I')
    hits = []          # (frame, pc, clock) inside windows
    ends = {}          # frame -> clock of the frame end (windows only)
    t0 = time.time()

    def dump(f):
        # partial output at each progress line: a killed run leaves data up to frame f
        for nm, arr in (('cnt', cnt), ('mas', mas), ('m2', m2s), ('stg', stg), ('are', are), ('bos', bos),
                        ('core', core), ('wide', wide)):
            (out / f'{tag}.{nm}.partial.bin').write_bytes(arr.tobytes())
        (out / f'{tag}.partial.json').write_text(json.dumps({'last_frame': f, 'hits': hits}))

    with Game(EMULATOR, work) as game:
        if a.mode == UNMODIFIED:
            status = boot_unmodified(game, a.rom, work / 'entered.state', a.shortcut)
        else:
            status = boot_to_first_update(game, a.rom, a.mode, work / 'entered.state', a.language)
            status['language'] = game.read(0x1227, 1)[0]
        entered = pl.master_clock(game, tmp)
        game.frame_end = None
        game.leftover = False
        prev = game.read(0, 0x2000)
        print(f'{a.mode}: start {memory(game)}', flush=True)
        in_window = False
        for f in range(1, total + 1):
            game.press(set(inputs[f - 1]))
            want = f in windows
            if want and not in_window:
                game.stop_areas = {'4006': ('rom', pl.MUSIC_ENTRY), '8457': ('rom', FIRST_UPDATE_ROM)}
                for _, (area, addr) in game.stop_areas.items():
                    game.call('set_breakpoint', {'address': f'{addr:x}', 'memory_area': area, 'execute': True})
                game.frame_end = None
                game.leftover = False
                in_window = True
            if in_window:
                def on_stop(pc, clock, f=f):
                    hits.append((f, pc, clock))
                    return False
                pl.step_with_stops(game, tmp, f, on_stop)
                ends[f] = game.frame_end
                if f + 1 not in windows:
                    for _, (area, addr) in game.stop_areas.items():
                        game.call('remove_breakpoint', {'address': f'{addr:x}', 'memory_area': area})
                    # normalise after breakpoint stops (EMULATOR.md): save and reload
                    game.call('save_state_file', {'file_path': str(work / 'norm.state')})
                    game.call('load_state_file', {'file_path': str(work / 'norm.state')})
                    game.held = set()
                    game.press(set(inputs[f - 1]))
                    in_window = False
            else:
                game.checked_step(1)
            ram = game.read(0, 0x2000)
            cnt.append(ram[0])
            mas.append(ram[0x240]); m2s.append(ram[0x241])
            stg.append(ram[0xe5f]); are.append(ram[0xe60]); bos.append(ram[0x1035])
            core.append(fp(ram, CORE)); wide.append(fp(ram, WIDE))
            if f % 20000 == 0:
                print(f'{a.mode}: frame {f} ({time.time() - t0:.0f} s) {memory(game)}', flush=True)
                dump(f)
        final = game.read(0, 0x1100)
    for nm, arr in (('cnt', cnt), ('mas', mas), ('m2', m2s), ('stg', stg), ('are', are), ('bos', bos),
                    ('core', core), ('wide', wide)):
        (out / f'{tag}.{nm}.bin').write_bytes(arr.tobytes())
    (out / f'{tag}.clocks.json').write_text(json.dumps(
        {'mode': a.mode, 'status': status, 'entered_clock': entered, 'hits': hits,
         'frame_ends': {str(k): v for k, v in ends.items()}, 'total': total, 'seconds': round(time.time() - t0)}))
    # the checker's PASS/FAIL (same criteria as longplay_check.py)
    ok = True
    lines = []
    first = {}
    for f in range(0, total + 1):
        pass
    arrs = {'mas': mas, 'stg': stg, 'are': are, 'm2': m2s}
    for s in run['stages']:
        idx = STAGE_NAMES.index(s['name'])
        m = s['start_frame']
        f0 = next((f for f in range(max(1, m - 400), m + 1) if stg[f - 1] == idx and mas[f - 1] == 0), None)
        good = (m == 0) or (stg[m - 1] == idx and mas[m - 1] == 0 and are[m - 1] == 0)
        ok &= good
        lines.append(f'{"PASS" if good else "FAIL"} {s["name"]:5s} gameplay from frame {f0 if f0 else 0:6d} marker {m}')
    end = run.get('end')
    if end:
        good = all({'master': mas, 'm2': m2s}[k][end['frame'] - 1] == v for k, v in end['state'].items())
        ok &= good
        lines.append(f'{"PASS" if good else "FAIL"} end reached at frame {end["frame"]}: master {mas[end["frame"]-1]} m2 {m2s[end["frame"]-1]}')
    print('\n'.join(lines))
    print(f'replayed {total} frames (+{status["boot_frames"]} boot) in {time.time() - t0:.0f} s; status {status}; entered clock {entered}')
    print('RESULT', 'PASS' if ok else 'FAIL')
    (out / f'{tag}.result.txt').write_text('\n'.join(lines) + f'\nRESULT {"PASS" if ok else "FAIL"}\n')
    return 0 if ok else 1


def probe(a):
    """Plain replay of the first max(frames) frames, saving the whole RAM after each listed frame
    (diagnostic for where the fingerprints differ; no breakpoints, no writes)."""
    run = json.loads(a.file.read_text())
    inputs = expand(run)
    frames = sorted(set(a.frames))
    work = Path(tempfile.mkdtemp(prefix='longplay-six-', dir='/workspace/build/longplay'))
    a.out.mkdir(parents=True, exist_ok=True)
    dumps = {}
    with Game(EMULATOR, work) as game:
        if a.mode == UNMODIFIED:
            boot_unmodified(game, a.rom, work / 'entered.state')
        else:
            boot_to_first_update(game, a.rom, a.mode, work / 'entered.state', a.language)
        for f in range(1, frames[-1] + 1):
            game.press(set(inputs[f - 1]))
            game.checked_step(1)
            if f in frames:
                dumps[str(f)] = game.read(0, 0x2000).hex()
    (a.out / f'{(a.tag or a.mode).replace(" ", "")}.probe.json').write_text(json.dumps(dumps))
    return 0


def load(out, mode):
    tag = mode.replace(' ', '')
    d = {}
    for nm, code in (('cnt', 'B'), ('mas', 'B'), ('m2', 'B'), ('stg', 'B'), ('are', 'B'), ('bos', 'B'),
                     ('core', 'I'), ('wide', 'I')):
        arr = array.array(code)
        arr.frombytes((out / f'{tag}.{nm}.bin').read_bytes())
        d[nm] = arr
    d['clk'] = json.loads((out / f'{tag}.clocks.json').read_text())
    return d


def events(d):
    """Per mode: the frame (state after that many frames) of each named event."""
    mas, m2, stg, are, bos, cnt = d['mas'], d['m2'], d['stg'], d['are'], d['bos'], d['cnt']
    n = len(mas)
    ev = {}
    for f in range(1, n + 1):
        i = f - 1
        if stg[i] == 21 and mas[i] == 0 and '6-4C start' not in ev:
            ev['6-4C start'] = f
        if stg[i] == 21 and bos[i] > 0 and 'boss seen' not in ev:
            ev['boss seen'] = f
        if 'boss seen' in ev and stg[i] == 21 and bos[i] == 0 and 'boss hp 0' not in ev:
            ev['boss hp 0'] = f
        if stg[i] == 21 and are[i] == 1 and 'area 1' not in ev:
            ev['area 1'] = f
        if stg[i] == 21 and mas[i] != 0 and 'master leaves 0' not in ev:
            ev['master leaves 0'] = f
        if mas[i] == 1 and m2[i] == 14 and 'ending (1,14)' not in ev:
            ev['ending (1,14)'] = f
    if 'master leaves 0' in ev:
        ev['last gameplay frame (master 0)'] = ev['master leaves 0'] - 1
    ev['recording end'] = n
    return ev


def updates(d):
    """(updates, lag frames) from the counter deltas; a frame with no change is a lag frame."""
    c = d['cnt']
    upd = lag = multi = 0
    prev = None
    for v in c:
        if prev is not None:
            dd = (v - prev) & 255
            if dd == 0:
                lag += 1
            else:
                upd += dd
                multi += dd > 1
        prev = v
    return upd, lag, multi


def first_diff(a, b):
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            return i + 1
    return None if len(a) == len(b) else min(len(a), len(b)) + 1


def stops_in(d, f, pc):
    return [c for ff, p, c in d['clk']['hits'] if ff == f and p == pc]


def compare(a):
    out = a.out
    D = {m: load(out, m) for m in MODES}
    ref = D['original']
    evs = {m: events(D[m]) for m in MODES}
    print('## per mode: updates, lag frames, first divergence vs ORIGINAL (frame = state after that many frames)')
    for m in MODES:
        w = D[m]['wide']; r = ref['wide']
        n = sum(1 for i in range(len(w)) if w[i] != r[i])
        c = sum(1 for i in range(len(w)) if D[m]['core'][i] != ref['core'][i])
        print(f'{m}: WIDE differs in {n} of {len(w)} frames, CORE in {c}')
    print('mode | frames | game updates | lag frames | multi-update frames | first diff counter | first diff master/stage/area/boss | first diff CORE | first diff WIDE | boot frames | entered clock')
    for m in MODES:
        d = D[m]
        u, l, mu = updates(d)
        sig = lambda x: list(zip(x['mas'], x['m2'], x['stg'], x['are'], x['bos']))
        fd = first_diff(sig(d), sig(ref))
        print(f'{m} | {len(d["cnt"])} | {u} | {l} | {mu} | {first_diff(d["cnt"], ref["cnt"])} | {fd} | '
              f'{first_diff(d["core"], ref["core"])} | {first_diff(d["wide"], ref["wide"])} | '
              f'{d["clk"]["status"]["boot_frames"]} | {d["clk"]["entered_clock"]}')
    print('\n## events (frame per mode)')
    names = list(evs['original'])
    print('event | ' + ' | '.join(MODES))
    for nme in names:
        print(nme + ' | ' + ' | '.join(str(evs[m].get(nme)) for m in MODES))
    print('\n## sub-frame clocks (master clock from power-on; phase = clock mod 358995; delta vs ORIGINAL in ticks and ms)')
    ms = lambda t: t * 1000 / CLOCK_HZ
    points = []     # (label, frame in ORIGINAL, pc)
    run = json.loads(a.file.read_text()) if a.file else None
    o = D['original']
    if run:
        for st in run['stages']:
            idx = STAGE_NAMES.index(st['name'])
            f0 = next((f for f in range(max(1, st['start_frame'] - 400), st['start_frame'] + 1)
                       if o['stg'][f - 1] == idx and o['mas'][f - 1] == 0), 1)
            # the sound command of the stage load is the last one before the stage's first gameplay frame
            snd = [f for f, pc, c in o['clk']['hits'] if pc == '4006' and f0 - 2 <= f <= f0 + 1]
            if snd:
                points.append((f'{st["name"]} start (first sound cmd)', snd[0], '4006', 'first'))
    for nme, pc, which in (('boss hp 0', '8457', 'first'), ('area 1', '8457', 'first'),
                           ('master leaves 0', '4006', 'first'), ('ending (1,14)', '4006', 'first')):
        points.append((f'{nme} (first {"main-loop update" if pc == "8457" else "sound cmd"})', evs['original'][nme], pc, which))
    print('point | ORIGINAL frame, clock, phase | ' + ' | '.join(f'{m}: frame, d-frames, d-ticks, d-ms' for m in MODES[1:]))
    for label, f, pc, which in points:
        rc = [c for ff, p, c in o['clk']['hits'] if ff == f and p == pc]
        if not rc:
            print(label, 'no stop in ORIGINAL'); continue
        row = f'{label} | {f}, {rc[0]}, {rc[0] % FRAME} | '
        for m in MODES[1:]:
            mc = [c for ff, p, c in D[m]['clk']['hits'] if ff == f and p == pc]
            if not mc:
                fs = sorted({ff for ff, p, c in D[m]['clk']['hits'] if p == pc and abs(ff - f) < 40})
                row += f'{m}: no stop in that frame (nearby {fs[:3]}) | '; continue
            dt = mc[0] - rc[0]
            row += f'{m}: {f}, 0, {dt:+d}, {ms(dt):+.6f} | '
        print(row)
    print('\nframe-end clocks: ORIGINAL frame 113213 end', o['clk']['frame_ends'].get('113213'),
          '; recording end frame 126003 end', {m: D[m]['clk']['frame_ends'].get('126003') for m in MODES})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--mode', default='original', choices=sorted(MODE_BITS) + [UNMODIFIED])
    r.add_argument('--file', type=Path, required=True)
    r.add_argument('--rom', type=Path, default=ROM)
    r.add_argument('--out', type=Path, required=True)
    r.add_argument('--tag', help='output file prefix (default: the mode)')
    r.add_argument('--shortcut', action='store_true', help='unmodified boot: select English with the title shortcut')
    r.add_argument('--language', type=int, default=1, help='saved language for patched modes (0 Japanese, 1 English)')
    r.add_argument('--windows', type=Path, help='JSON list of frames to step with breakpoints armed')
    w = sub.add_parser('windows', help='frames to measure with breakpoints, from a plain ORIGINAL run')
    w.add_argument('out', type=Path)
    w.add_argument('--file', type=Path, required=True)
    w.add_argument('dest', type=Path)
    pr = sub.add_parser('probe')
    pr.add_argument('--mode', default='original', choices=sorted(MODE_BITS) + [UNMODIFIED])
    pr.add_argument('--file', type=Path, required=True)
    pr.add_argument('--rom', type=Path, default=ROM)
    pr.add_argument('--out', type=Path, required=True)
    pr.add_argument('--tag')
    pr.add_argument('--language', type=int, default=1)
    pr.add_argument('--frames', type=int, nargs='+', required=True)
    c = sub.add_parser('compare')
    c.add_argument('out', type=Path)
    c.add_argument('--file', type=Path)
    a = ap.parse_args()
    if a.cmd == 'run':
        return run_mode(a)
    if a.cmd == 'probe':
        return probe(a)
    if a.cmd == 'windows':
        d = load(a.out, 'original')
        run = json.loads(a.file.read_text())
        ws = set()
        for st in run['stages']:
            idx = STAGE_NAMES.index(st['name'])
            f0 = next((f for f in range(max(1, st['start_frame'] - 400), st['start_frame'] + 1)
                       if d['stg'][f - 1] == idx and d['mas'][f - 1] == 0), 1)
            for c in (f0, st['start_frame']):
                ws.update(range(max(1, c - 2), c + 4))
        for f in events(d).values():
            ws.update(range(max(1, f - 3), min(len(d['cnt']), f + 3) + 1))
        a.dest.write_text(json.dumps(sorted(ws)))
        print(len(ws), 'window frames')
        return 0
    return compare(a)


if __name__ == '__main__':
    sys.exit(main())
