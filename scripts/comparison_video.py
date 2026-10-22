#!/usr/bin/env python3
"""Original-versus-Enhanced comparison videos from recorded button input.

A run file (research/comparison-runs/*.json) holds a stage and the button
input from that stage's first gameplay update. `record` replays it on one ROM
and saves every frame with a game-state trace, `compare` checks two traces
frame by frame, `render` stacks two recordings into a labelled 1440p60 MP4,
and `make` does all three for both games. See docs/COMPARISON-VIDEOS.md.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import tempfile
import zlib

import emulator_session as emulator

# Patch Level Select order and the progression byte it writes
# (src/options/options-text.inc, src/selector-hook).
STAGE_NAMES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2',
               '4-3', '4-4', '5-1', '5-2', '5-3', '5-4', '6-1', '6-2', '6-3',
               '6-4A', '6-4B', '6-4C']
NEXT_SEQUENCE = [4, 5, 7, 8, 9, 11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 25, 27, 28,
                 29, 31, 33, 35]
BUTTONS = ('left', 'right', 'up', 'down', 'I', 'II', 'select', 'run')
# Game RAM excluded from the trace hash: zero page (frame counter, scratch),
# the stack page and bytes Enhanced owns or sets by design (renderer
# workspace, English, boot path).
OWNED = (set(range(0x0000, 0x0200)) | {0x024b, 0x0250} | set(range(0x0257, 0x025b)) |
         set(range(0x0428, 0x0466)) | set(range(0x0828, 0x0866)) | {0x11ef, 0x1213, 0x1227})
GAMEPLAY = ('sat', 'ryu', 'timer', 'lives', 'health', 'cam', 'area', 'stage')


def unpack(result):
    texts = [item['text'] for item in result.get('content', []) if item['type'] == 'text']
    return json.loads(texts[0]) if texts else result


class StepError(RuntimeError):
    """A frame step did not report exactly the frames asked for."""


class Game:
    """One headless Geargrafx process; buttons change only between frames."""

    def __init__(self, emulator_path, logdir):
        self.binary = emulator.BINARY = Path(emulator_path).resolve()
        emulator.ROOT = Path(logdir).resolve()
        self.logdir = emulator.ROOT
        self.emu = emulator.Emulator()
        self.held = set()

    def __enter__(self):
        self.emu.__enter__()
        return self

    def __exit__(self, *exc):
        self.emu.__exit__(*exc)

    def call(self, name, arguments=None):
        return unpack(self.emu.call(name, arguments))

    def step(self, frames=1):
        try:
            return self.call('debug_step_frame', {'frames': frames, 'mode': 'sync'})
        except RuntimeError as exc:
            # A breakpoint stops a step early; boot() relies on that.
            if 'interrupted' in str(exc):
                return None
            raise

    def read(self, offset, size, area=0):
        return bytes.fromhex(self.call('read_memory', {
            'area': area, 'offset': f'{offset:04x}', 'size': size})['data'])

    def write(self, offset, data):
        self.call('write_memory', {'area': 0, 'offset': f'{offset:04x}', 'bytes': data.hex(' ')})

    def reg(self, name, value):
        self.call('write_huc6280_register', {'name': name, 'value': f'{value:x}'})

    def press(self, buttons):
        for b in self.held - buttons:
            self.call('controller_button', {'player': 1, 'button': b, 'action': 'release'})
        for b in buttons - self.held:
            self.call('controller_button', {'player': 1, 'button': b, 'action': 'press'})
        self.held = set(buttons)

    def checked_step(self, frames):
        """Step and require the emulator to report exactly `frames` executed."""
        result = self.step(frames)
        if not result or result.get('frames_executed') != frames:
            raise StepError(f'a {frames}-frame step reported {result}')

    def run_to(self, pc, polls=80000):
        """Continue to a breakpoint already set; return the stop address."""
        self.call('debug_continue')
        for _ in range(polls):
            status = self.call('debug_get_status')
            if status.get('paused'):
                if pc and status['pc'] != pc:
                    raise RuntimeError(f'Unexpected stop {status}')
                return status['pc']
        raise TimeoutError(pc)

    def screenshot(self):
        shot = self.emu.call('get_screenshot')
        return base64.b64decode(next(item['data'] for item in shot['content']
                                     if item['type'] == 'image'))


def boot(game, rom):
    """Cold boot, leave the splash/title with Run, stop at the main-loop hook."""
    game.call('load_media', {'file_path': str(Path(rom).resolve())})
    game.call('debug_pause')
    game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    previous, since, presses, title_pressed = None, 0, [200], False
    for frame in range(1, 20000):
        game.step(1)
        since += 1
        status = game.call('debug_get_status')
        if status.get('at_breakpoint') and status['pc'] == '83F3':
            break
        master = game.read(0x240, 2)
        if master != previous:
            previous, since = master, 0
        if master == b'\x01\x01' and since == 180 and not title_pressed:
            presses.append(frame)
            title_pressed = True
        # Enhanced's splash precedes the native master script; Run leaves it.
        if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150:
            presses.append(frame)
        for p in presses:
            if frame == p:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'press'})
            elif frame == p + 2:
                game.call('controller_button', {'player': 1, 'button': 'run', 'action': 'release'})
    else:
        raise RuntimeError('Gameplay not reached')
    game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    game.step(120)


def crc_payload(rom):
    """Geargrafx states fingerprint cartridge bytes, excluding a copier header."""
    if len(rom) % 8192 == 512:
        rom = rom[512:]
    return zlib.crc32(rom)


def make_seed(emulator_path, rom, path):
    """Cold-boot the original in a session of its own and save its machine
    state at the main-loop hook ($83F3) in 1-1 to `path`.

    The booting session is not used for play: after a cold boot, the first
    frame step after stage entry sometimes covers two game updates, even
    after a save and reload (2-2, 4-1, 5-2, 5-4 and 6-3 in one probe). A
    session that has only loaded the state never does."""
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with Game(emulator_path, Path(tempfile.mkdtemp(prefix='comparison-seed-'))) as game:
        boot(game, rom)
        game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        game.run_to('83F3')
        game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
        game.call('save_state_file', {'file_path': str(path)})
    shutil.rmtree(game.logdir, ignore_errors=True)
    return path


def start_point(game, rom, seed, enhanced=False):
    """Stop at the main-loop hook ($83F3) in 1-1, from where a stage is entered.

    Every session starts by loading the one saved machine state `seed` (from
    make_seed) into this ROM: cartridge CRC retargeted and, for Enhanced,
    its options $2100/$2101 at their defaults. A loaded state fixes both the
    game state (the boot paths leave counters that stage entry does not
    reset) and the emulator's frame-step phase, which otherwise depends on
    the session's history; replays are frame-exact only from the same loaded
    state in a session that has done nothing else.
    """
    game.call('load_media', {'file_path': str(Path(rom).resolve())})
    game.call('debug_pause')
    state = bytearray(Path(seed).read_bytes())
    struct.pack_into('<I', state, len(state) - 48, crc_payload(Path(rom).read_bytes()))
    retargeted = Path(game.logdir) / 'start.state'
    retargeted.write_bytes(state)
    game.call('load_state_file', {'file_path': str(retargeted)})
    if enhanced:
        game.write(0x100, b'\x00\x00')   # in the original, the stack page's floor


def start_stage(game, stage):
    """From the main-loop hook, enter a stage as the patch Level Select does
    (the same debugger writes in both games) and stop at its first update."""
    cpu = game.call('get_huc6280_status')
    assert cpu['PC'] == '83F3', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    game.write(0x241, bytes([stage]))
    game.write(0x247, bytes([NEXT_SEQUENCE[stage], 0]))
    game.write(0xe65, bytes(22))
    game.write(0xead, bytes([16]))                     # full health (1.09-dev)
    sp = saved['S']
    game.write(0x100 + sp - 1, bytes([0xf2, 0x83]))  # synthetic return to $83F3
    game.reg('S', sp - 2)
    game.reg('A', stage)
    game.reg('PC', 0x8244)
    game.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    game.run_to('83F3', polls=20000)
    for k in ('X', 'Y', 'P'):
        game.reg(k, saved[k])
    game.call('remove_breakpoint', {'address': '23f3', 'memory_area': 'rom'})
    game.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    game.run_to('8457')
    game.call('remove_breakpoint', {'address': '2457', 'memory_area': 'rom'})
    # The first frame step after a breakpoint stop sometimes covers one more
    # game update than other times (it varies between sessions); after a saved
    # state is loaded it does not. Save and reload here so frame 0 is defined.
    entered = Path(game.logdir) / 'entered.state'
    game.call('save_state_file', {'file_path': str(entered)})
    game.call('load_state_file', {'file_path': str(entered)})
    # Tripwire for the two-update first step (see make_seed): the low byte of
    # the stage timer counts down once per game update in every stage.
    before = game.read(0xeda, 1)[0]
    game.checked_step(1)
    after = game.read(0xeda, 1)[0]
    game.call('load_state_file', {'file_path': str(entered)})
    if (before - after) & 0xff != 1:
        raise StepError(f'the first step after stage entry covered {(before - after) & 0xff} game updates')


def record(emulator_path, rom, run, out, seed, enhanced=False, tail=60):
    out = Path(out)
    frames = out / 'frames'
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir(parents=True)
    segments = run['segments'] + [[tail, []]]
    trace, n = [], 0
    with Game(emulator_path, out) as game:
        # The emulator's own build string (Geargrafx reports its git commit)
        # and the host OS, for the video's recording note.
        (out / 'emulator.json').write_text(json.dumps({
            'emulator': 'Geargrafx', 'version': game.emu.server.get('version', 'unknown'),
            'host': platform.system()}) + '\n')
        start_point(game, rom, seed, enhanced)
        start_stage(game, run['stage'])
        for count, buttons in segments:
            game.press(set(buttons))
            for _ in range(count):
                game.checked_step(1)
                (frames / f'{n:06d}.png').write_bytes(game.screenshot())
                ram = game.read(0, 0x2000)
                trace.append({
                    'f': n, 'ram': hashlib.sha1(bytes(b for k, b in enumerate(ram) if k not in OWNED)).hexdigest()[:12],
                    'sat': hashlib.sha1(game.read(0, 512, area=6)).hexdigest()[:12],
                    'ryu': ram[0xe9e:0xeb8].hex(), 'timer': ram[0xeda:0xede].hex(),
                    'stage': ram[0xe5f], 'area': ram[0xe60], 'lives': ram[0xeaf],
                    'health': ram[0xead], 'cam': int.from_bytes(ram[0x20f:0x211], 'little'),
                    'master': ram[0x240], 'boss': ram[0x1035]})
                n += 1
    (out / 'trace.json').write_text(json.dumps(trace))
    return trace


def retried(function, *args, tries=3, **kwargs):
    """Run a recording again if the emulator reports a mis-step (StepError)."""
    for attempt in range(tries):
        try:
            return function(*args, **kwargs)
        except StepError as exc:
            print(f'{exc}; recording again ({attempt + 1}/{tries})', flush=True)
    raise SystemExit(f'Emulator steps kept mis-stepping after {tries} tries')


def cinema_after(emulator_path, rom, run, out, seed, enhanced=False, max_frames=40000):
    """Replay a run, complete the following stages natively and capture the
    next cinema.

    Later stages render 120 frames and then leave through the native
    completion path ($8457 -> $8478), as scripts/audit_cutscenes.py does, so
    the cinema follows a full play of the run's stage. Native English is set
    in both games so their text matches. Returns [(scene, png sha256)].
    """
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    with Game(emulator_path, out) as game:
        start_point(game, rom, seed, enhanced)
        game.write(0x1227, b'\x01')
        start_stage(game, run['stage'])
        for count, buttons in run['segments']:
            game.press(set(buttons))
            game.checked_step(count)
        game.press(set())
        for _ in range(max_frames):
            kind, scene = game.read(0x240, 2)
            if kind == 0 and frames:
                break                               # gameplay again: cinema over
            if kind == 0:
                game.step(120)
                game.call('debug_run_to_cursor', {'address': '8457'})
                for _ in range(20000):
                    status = game.call('debug_get_status')
                    if status.get('paused'):
                        break
                if not (status['paused'] and status['pc'] == '8457'):
                    raise RuntimeError(f'Gameplay completion boundary not reached: {status}')
                game.reg('PC', 0x8478)
                for _ in range(1200):
                    game.step(1)
                    if game.read(0x240, 2) != bytes([kind, scene]):
                        break
                continue
            if kind != 1:
                break                               # ending sequence
            game.checked_step(1)
            png = game.screenshot()
            digest = hashlib.sha256(png).hexdigest()
            path = out / f'{digest}.png'
            if not path.exists():
                path.write_bytes(png)
            frames.append((scene, digest))
        else:
            raise RuntimeError('Frame budget exhausted before the cinema ended')
    (out / 'cinema.json').write_text(json.dumps(frames))
    return frames


def finishes(run, trace):
    """Whether a recording reaches the end of its stage: the next stage, a
    cinema, or (5-4) the boss defeated."""
    last = trace[-1]
    return (last['stage'] != run['stage'] or last['master'] != 0
            or (STAGE_NAMES[run['stage']] == '5-4' and last['boss'] == 0))


def compare(a, b):
    """Frames where the two traces differ, per field."""
    diff = {field: [x['f'] for x, y in zip(a, b) if x[field] != y[field]]
            for field in GAMEPLAY + ('ram',)}
    same = len(a) == len(b) and not any(diff[f] for f in GAMEPLAY)
    return same, diff


def font(name, fallback):
    path = Path(fallback)
    if path.exists():
        return str(path)
    found = subprocess.run(['fc-match', '-f', '%{file}', name], capture_output=True, text=True)
    return found.stdout.strip()


def render(top, bottom, out, stage, version, crf=12):
    """Stack two recordings, 3x nearest-neighbour, into a 2560x1440 MP4."""
    W, H, GW, GH = 2560, 1440, 768, 672      # display rows 18-241 of 256x242, 3x
    GX, TOP_Y, BOT_Y = (W - GW) // 2, 40, H - 40 - GH
    bold = font('Noto Sans:bold', '/usr/share/fonts/noto/NotoSans-Bold.ttf')
    regular = font('Noto Sans', '/usr/share/fonts/noto/NotoSans-Regular.ttf')
    mono = font('Noto Sans Mono:bold', '/usr/share/fonts/noto/NotoSansMono-Bold.ttf')
    orange, cyan, white, grey = '0xffb347', '0x5ad1ff', '0xf2f2f2', '0x9a9aa6'
    setup = [json.loads((Path(d) / 'emulator.json').read_text()) for d in (top, bottom)]
    if setup[0] != setup[1]:
        raise ValueError(f'Recordings come from different emulator setups: {setup}')
    build = setup[0]['version'].removesuffix('-dirty')
    tmp = Path(tempfile.mkdtemp(prefix='comparison-video-'))
    texts = []

    def text(content, fontfile, size, color, x, y):
        f = tmp / f't{len(texts)}.txt'
        f.write_text(content)
        texts.append(f)
        return f'drawtext=fontfile={fontfile}:textfile={f}:fontsize={size}:fontcolor={color}:x={x}:y={y}'

    def side(title, lines, color, game_y):
        edge = GX - 48
        y = game_y + (GH - (110 + 58 * len(lines))) // 2
        parts = [f'drawbox=x={GX - 24}:y={game_y}:w=10:h={GH}:color={color}:t=fill',
                 text(title, bold, 96, color, f'{edge}-text_w', y)]
        for i, line in enumerate(lines):
            parts.append(text(line, regular, 44, white if i == 0 else grey, f'{edge}-text_w', y + 124 + 58 * i))
        return parts

    right = GX + GW + 48
    draw = (side('ORIGINAL', ['Ninja Ryukenden', 'PC Engine, unmodified'], orange, TOP_Y) +
            side('ENHANCED', ['Ninja Ryukenden Enhanced', version], cyan, BOT_Y) + [
        text(f'STAGE {stage}', bold, 110, white, right, TOP_Y + 40),
        text('Top', bold, 44, orange, right, TOP_Y + 200),
        text('Original', regular, 44, white, right + 190, TOP_Y + 200),
        text('Bottom', bold, 44, cyan, right, TOP_Y + 262),
        text(f'Enhanced {version}', regular, 44, white, right + 190, TOP_Y + 262),
        text('Same button inputs,', regular, 40, grey, right, TOP_Y + 380),
        text('frame-synchronized', regular, 40, grey, right, TOP_Y + 432),
        text('RECORDING', bold, 40, grey, right, BOT_Y + 40),
        text(f'{setup[0]["emulator"]} emulator', regular, 40, white, right, BOT_Y + 98),
        text(f'build {build}, {setup[0]["host"]}', regular, 36, grey, right, BOT_Y + 150),
        text('Emulated PC Engine, HuCard', regular, 36, grey, right, BOT_Y + 198),
        text('Not real-hardware footage', regular, 36, grey, right, BOT_Y + 246),
        text('No audio recorded', regular, 36, grey, right, BOT_Y + 294),
        text('FRAME', bold, 40, grey, right, BOT_Y + GH - 150),
        f"drawtext=fontfile={mono}:text='%{{eif\\:n\\:d\\:6}}':fontsize=72:fontcolor={white}:x={right}:y={BOT_Y + GH - 100}"])
    crop = f'crop=256:224:0:18,scale={GW}:{GH}:flags=neighbor'
    graph = (f'color=c=0x0e0e12:s={W}x{H}:r=60[bg];[0:v]{crop}[t];[1:v]{crop}[b];'
             f'[bg][t]overlay={GX}:{TOP_Y}:shortest=1[a];[a][b]overlay={GX}:{BOT_Y}:shortest=1,'
             + ','.join(draw) + ',scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]')
    (tmp / 'graph.txt').write_text(graph)
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
        '-framerate', '60', '-i', str(Path(top) / 'frames' / '%06d.png'),
        '-framerate', '60', '-i', str(Path(bottom) / 'frames' / '%06d.png'),
        '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
        '-/filter_complex', str(tmp / 'graph.txt'), '-map', '[v]', '-map', '2:a', '-shortest',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', str(crf), '-profile:v', 'high', '-g', '30', '-bf', '2',
        '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
        '-r', '60', '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', str(out)], check=True)
    shutil.rmtree(tmp)


def report(same, diff, frames):
    for field, where in diff.items():
        note = ' (informational: game RAM outside Enhanced-owned bytes)' if field == 'ram' else ''
        print(f'{field:7s} {len(where)} of {frames} frames differ' + (f', first {where[:5]}' if where else '') + note)
    print('IDENTICAL GAMEPLAY' if same else 'GAMEPLAY DIFFERS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, required=True, help='Geargrafx binary')
    sub = parser.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record', help='Replay a run on one ROM')
    rec.add_argument('rom', type=Path)
    rec.add_argument('run', type=Path)
    rec.add_argument('out', type=Path)
    rec.add_argument('--seed', type=Path, required=True,
                     help='Start state; made from the original (--original) if it does not exist yet')
    rec.add_argument('--original', type=Path, help='Original ROM, to make the start state')
    rec.add_argument('--enhanced', action='store_true', help='The ROM is Enhanced (options at their defaults)')
    cmp_ = sub.add_parser('compare', help='Compare two recordings')
    cmp_.add_argument('a', type=Path)
    cmp_.add_argument('b', type=Path)
    ren = sub.add_parser('render', help='Stack two recordings into an MP4')
    ren.add_argument('top', type=Path)
    ren.add_argument('bottom', type=Path)
    ren.add_argument('out', type=Path)
    ren.add_argument('--version', required=True, help='Enhanced label, e.g. v1.08-dev')
    ren.add_argument('--stage', required=True)
    cin = sub.add_parser('cinema', help='After each run, compare the next cinema frame by frame')
    cin.add_argument('--original', type=Path, required=True)
    cin.add_argument('--enhanced', type=Path, required=True)
    cin.add_argument('--work', type=Path, required=True)
    cin.add_argument('runs', type=Path, nargs='+')
    make = sub.add_parser('make', help='Record both games, compare, render')
    make.add_argument('--original', type=Path, required=True)
    make.add_argument('--enhanced', type=Path, required=True)
    make.add_argument('--version', required=True)
    make.add_argument('--work', type=Path, required=True, help='Recordings (frames) go here')
    make.add_argument('--videos', type=Path, required=True)
    make.add_argument('runs', type=Path, nargs='+')
    args = parser.parse_args()

    if args.command == 'record':
        if not args.seed.exists():
            if not args.original:
                raise SystemExit('No start state yet: give --original to make it')
            make_seed(args.emulator, args.original, args.seed)
        trace = retried(record, args.emulator, args.rom, json.loads(args.run.read_text()), args.out,
                        args.seed, args.enhanced)
        print(args.rom.name, len(trace), 'frames')
    elif args.command == 'compare':
        a, b = (json.loads((p / 'trace.json').read_text()) for p in (args.a, args.b))
        report(*compare(a, b), len(a))
    elif args.command == 'render':
        render(args.top, args.bottom, args.out, args.stage, args.version)
    elif args.command == 'cinema':
        failed = []
        for path in args.runs:
            run = json.loads(path.read_text())
            stage = STAGE_NAMES[run['stage']]
            seed = make_seed(args.emulator, args.original, args.work / f'{stage}-start.state')
            for attempt in range(2):
                a = retried(cinema_after, args.emulator, args.original, run, args.work / f'{stage}-cinema-original', seed)
                b = retried(cinema_after, args.emulator, args.enhanced, run, args.work / f'{stage}-cinema-enhanced',
                            seed, enhanced=True)
                scenes = sorted({s for s, _ in a})
                diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
                same = len(a) == len(b) and not diff
                if same:
                    break
                if not attempt:
                    print(f'After {stage}: cinema differs; recording both games again in fresh sessions', flush=True)
            print(f'After {stage}: cinema scene(s) {scenes}, {len(a)}/{len(b)} frames, '
                  + ('every frame identical' if same else f'{len(diff)} frames differ, first {diff[:5]}'))
            if not same:
                failed.append(stage)
        if failed:
            raise SystemExit(f'Cinema differs after {failed}')
    else:
        args.videos.mkdir(parents=True, exist_ok=True)
        for path in args.runs:
            run = json.loads(path.read_text())
            stage = STAGE_NAMES[run['stage']]
            top, bottom = args.work / f'{stage}-original', args.work / f'{stage}-enhanced'
            # One emulator at a time: replays are compared frame by frame anyway.
            seed = make_seed(args.emulator, args.original, args.work / f'{stage}-start.state')
            for attempt in range(2):
                a = retried(record, args.emulator, args.original, run, top, seed)
                b = retried(record, args.emulator, args.enhanced, run, bottom, seed, enhanced=True)
                same, diff = compare(a, b)
                print(f'Stage {stage}:')
                report(same, diff, len(a))
                if same:
                    break
                # A real difference repeats; a rare emulator mis-step under
                # heavy host load (one extra frame) does not.
                if not attempt:
                    print('Recording both games again in fresh sessions', flush=True)
            if not same:
                raise SystemExit(f'Stage {stage}: gameplay differs; no video written')
            if not finishes(run, a):
                raise SystemExit(f'Stage {stage}: the run no longer finishes the stage; search it again')
            out = args.videos / f'Ninja Ryukenden - Stage {stage} - Original vs Enhanced {args.version}.mp4'
            render(top, bottom, out, stage, args.version)
            print('wrote', out)


if __name__ == '__main__':
    main()
