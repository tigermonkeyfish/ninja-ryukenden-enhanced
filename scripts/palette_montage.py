#!/usr/bin/env python3
"""Six-panel palette montage (Palettes video), in phases:

  pick      replay each clip's stage once (Original panel, no pictures) and
            choose a damage-free window near the trailer's choice
  record    for each clip, six fresh sessions (one per palette), pictures
            for the window, a sync check across the six, a lossless clip
  assemble  intro card, clips, end card, audio; YouTube and X files

Needs ffmpeg with libx264 and drawtext on PATH, the audio-capture build of
Geargrafx (profile/video-tools) and the headerless original ROM; see
docs/COMPARISON-VIDEOS.md. Everything it writes goes to --work.
"""
import argparse
import array
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import palette_video as pv
from comparison_video import make_seed

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / 'research/comparison-runs'
ROUTES = ROOT / 'research/palette-video'
COUNT = 180
EXTRA = 45                  # last clip's frames under the dissolve into the end card
SR = 44100
W, H = pv.W, pv.H
END = 7.0
# (name, run file, firewheel, banner, trailer's start frame or explicit window)
CLIPS = [
    ('1-1', RUNS / '1-1.json', 0, 'STAGE 1-1', 2280, COUNT),
    ('2-2-original-wheel', ROUTES / '2-2-firewheel.json', 0, 'STAGE 2-2  ·  ORIGINAL FIRE WHEEL', 1090, 400),
    ('2-2-nes-wheel', ROUTES / '2-2-firewheel.json', 1, 'STAGE 2-2  ·  NES FIRE WHEEL', 1090, 400),
    ('3-1', RUNS / '3-1.json', 0, 'STAGE 3-1', 660, COUNT),
    ('3-2', RUNS / '3-2.json', 0, 'STAGE 3-2', 2450, COUNT),
    ('4-1', RUNS / '4-1.json', 0, 'STAGE 4-1', 150, COUNT),
    ('4-2', RUNS / '4-2.json', 0, 'STAGE 4-2', 1300, COUNT),
    ('5-2', RUNS / '5-2.json', 0, 'STAGE 5-2', 960, COUNT),
    ('5-3', RUNS / '5-3.json', 0, 'STAGE 5-3', 2510, COUNT),
    ('6-1', RUNS / '6-1.json', 0, 'STAGE 6-1', 632, COUNT),
    ('6-3', RUNS / '6-3.json', 0, 'STAGE 6-3', 2730, COUNT + EXTRA),
]
SYNC_FIELDS = ('sat', 'ryu', 'timer', 'stage', 'area', 'lives', 'health', 'cam', 'master', 'fx', 'wheel', 'state')


def trace_window_ok(trace, a, n):
    w = trace[a:a + n]
    return (len(w) == n and all(w[j]['health'] >= w[j - 1]['health'] for j in range(1, n))
            and len({x['area'] for x in w}) == 1 and len({x['lives'] for x in w}) == 1)


def pick_window(trace, target, n, wide=False):
    best = None
    lo, hi = (0, len(trace) - n + 1) if wide else (max(0, target - 180), min(len(trace) - n, target + 181))
    for i in range(lo, hi, 5):
        if not trace_window_ok(trace, i, n):
            continue
        w = trace[i:i + n]
        travel = sum(abs(w[j]['cam'] - w[j - 1]['cam']) for j in range(1, n)
                     if abs(w[j]['cam'] - w[j - 1]['cam']) < 16)
        score = travel - abs(i - target) * 0.3
        if best is None or score > best[0]:
            best = (score, i)
    return best and best[1]


def inputs_of(run):
    out = []
    for count, buttons in run['segments']:
        out += [frozenset(buttons)] * count
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('phase', choices=['pick', 'record', 'assemble'])
    ap.add_argument('--emulator', type=Path, required=True)
    ap.add_argument('--rom', type=Path, required=True, help='Enhanced build under the emulator sandbox')
    ap.add_argument('--original', type=Path, required=True)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--only', help='comma list of clip names')
    ap.add_argument('--fonts', type=Path)
    ap.add_argument('--watermark', type=Path)
    ap.add_argument('--banner', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    work = args.work
    work.mkdir(parents=True, exist_ok=True)
    seed = work / 'start.state'
    if not seed.exists():
        make_seed(args.emulator, args.original, seed)
    clips = [c for c in CLIPS if not args.only or c[0] in args.only.split(',')]
    wfile = work / 'windows.json'
    windows = json.loads(wfile.read_text()) if wfile.exists() else {}
    if args.phase == 'pick':
        for name, runfile, fw, banner, target, n in clips:
            run = json.loads(runfile.read_text())
            if name.startswith('2-2-'):
                windows[name] = [target, n]
                continue
            tr = pv.record(args.emulator, args.rom, seed, run, run['stage'], 'original', fw,
                           work / 'pick', [(0, sum(c for c, _ in run['segments']))], shots=False)
            a = pick_window(tr, target, n)
            print(name, 'target', target, 'window', a, 'of', len(tr), flush=True)
            windows[name] = [a, n]
            shutil.rmtree(work / 'pick', ignore_errors=True)
        wfile.write_text(json.dumps(windows, indent=1))
    elif args.phase == 'record':
        record_phase(args, clips, windows, seed)
    else:
        assemble(args, windows)


def first_mismatch(report):
    """The earliest frame at which any panel differs from the Original panel."""
    frames = [v[0] for fields in report['mismatches'].values() if isinstance(fields, dict)
              for v in fields.values() if v[:-1]]
    return min(frames) if frames else None


def record_phase(args, clips, windows, seed):
    work = args.work
    fonts = fonts_of(args.fonts)
    for name, runfile, fw, banner, target, n in clips:
        a, n = windows[name]
        run = json.loads(runfile.read_text())
        tail = 700 if name == '6-3' else 0     # audio for the end card to fade over
        for attempt in range(3):
            traces, dirs = {}, []
            for mode in pv.MODES:
                out = work / f'{name}-{mode.replace(" ", "")}'
                audio = work / (f'{name}.s16' if mode == 'original' else f'{name}-{mode.replace(" ", "")}.s16')
                traces[mode] = pv.record(args.emulator, args.rom, seed, run, run['stage'], mode, fw, out,
                                         [(a, a + n)], audio=audio, tail=tail)
                dirs.append(out)
                if mode != 'original':
                    audio.unlink(missing_ok=True)
            report = sync_report(traces)
            (work / f'{name}-sync.json').write_text(json.dumps(report, indent=1))
            print(name, 'window', a, n, 'sync', report['summary'], flush=True)
            if not report['mismatched_frames']:
                break
            f = first_mismatch(report)
            print(f'{name}: panels first differ at frame {f} ({json.dumps(report["mismatches"])[:600]})', flush=True)
            for d in dirs:
                shutil.rmtree(d / 'frames', ignore_errors=True)
            # Use a damage-free window that ends before the panels part.
            base = traces['original'][:f]
            new = (pick_window(base, min(a, f - n), n) or pick_window(base, min(a, f - n), n, wide=True)) if f and f > n else None
            if new is None:
                raise SystemExit(f'{name}: no window before frame {f}')
            a = new
            windows[name] = [a, n]
            (work / 'windows.json').write_text(json.dumps(windows, indent=1))
        else:
            raise SystemExit(f'{name}: panels still differ')
        pv.compose_clip(dirs, a, n, banner, '', work / f'{name}.mkv', fonts, args.watermark, work / f'{name}-tmp')
        for d in dirs:
            shutil.rmtree(d / 'frames', ignore_errors=True)


def sync_report(traces):
    base = traces['original']
    bad = {}
    for mode, tr in traces.items():
        if len(tr) != len(base):
            bad[mode] = ['length']
            continue
        for field in SYNC_FIELDS:
            frames = [i for i, (x, y) in enumerate(zip(base, tr)) if x[field] != y[field]]
            if frames:
                bad.setdefault(mode, {})[field] = frames[:5] + [len(frames)]
    return {'frames': len(base), 'fields': SYNC_FIELDS, 'modes': list(traces), 'mismatches': bad,
            'mismatched_frames': bool(bad), 'summary': 'all six identical' if not bad else 'DIFFERENT'}



def fonts_of(d):
    return tuple(str(Path(d) / f) for f in ('SourceSansPro-Bold.ttf', 'SourceSansPro-Semibold.ttf', 'SourceSansPro-Regular.ttf'))


def clip_audio(work, name, a, n, extra_s=0.0):
    """The Original panel's audio for frames a..a+n (+extra seconds), levelled
    as the trailer is (RMS towards 2800, gain^0.7) with 8 ms fades."""
    offsets = {int(k): v for k, v in json.loads((work / f'{name}-original/audio-offsets.json').read_text()).items()}
    pcm = (work / f'{name}.s16').read_bytes()
    length = int((n / 60 + extra_s) * SR)
    raw = pcm[offsets[a]:offsets[a] + length * 4].ljust(length * 4, b'\0')
    samples = array.array('h', raw)
    head = array.array('h', raw[:int(min(n / 60, 3) * SR) * 4])
    rms = math.sqrt(sum(x * x for x in head) / max(1, len(head))) or 1.0
    return samples, (2800 / rms) ** 0.7


def assemble(args, windows):
    work, out = args.work, args.out
    fonts = fonts_of(args.fonts)
    tmp = work / 'assemble'
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    version = (ROOT / 'VERSION').read_text().strip()
    card = [('NINJA RYUKENDEN ENHANCED', 0, 104, 'white', 170),
            ('Smooth Parallax Scrolling Patch', 0, 54, '0xf2d060', 295),
            ('Six palettes: Original  ·  Apocalypse  ·  NES-A  ·  NES-B  ·  SMS  ·  GB DMG', 0, 38, 'white', 672),
            ('Optional NES-style Fire Wheel', 2, 34, '0xf2d060', 728),
            ('Saves your settings to backup memory on supported systems', 2, 32, '0xf2d060', 772),
            (f'Version {version}  ·  Free patch for PC Engine / TurboGrafx-16', 2, 40, '0xf2d060', 830),
            ('github.com/tigermonkeyfish/ninja-ryukenden-enhanced', 0, 42, 'white', 880),
            None,
            ('Development build, emulator recordings: hardware testing pending', 0, 30, '0xf2d060', 976),
            ('Gameplay and audio recorded in the Geargrafx emulator from scripted button-input replays', 2, 28, '0xc8c8d4', 1018)]
    intro = [('NINJA RYUKENDEN ENHANCED', 0, 104, 'white', 170),
             ('Palette Modes', 0, 54, '0xf2d060', 295),
             ('Six palettes, six panels, one input: frame-synchronized', 2, 40, '0xc8c8d4', 700),
             (f'Version {version}', 2, 42, '0xf2d060', 770)]
    for kind, links in (('YouTube', 'youtube.com/@TigerMonkeyFish'),
                        ('X', 'youtube.com/@TigerMonkeyFish   ·   tigermonkeyfish.itch.io   ·   ko-fi.com/tigermonkeyfish')):
        lines = [(links, 0, 34, 'white', 934) if c is None else c for c in card]
        lines = [c for c in lines if c[4] < 2000]
        pv.end_card(tmp / f'end-{kind}.png', args.banner, fonts, lines, tmp / f'e-{kind}')
    pv.end_card(tmp / 'intro.png', args.banner, fonts, intro, tmp / 'i')
    names = [c[0] for c in CLIPS]
    pcm, bounds, frames = array.array('h'), [], 0
    IN = 150                                           # intro card frames, silent
    pcm.extend(array.array('h', bytes(int(IN / 60 * SR) * 4)))
    for name in names:
        a, n = windows[name]
        last = name == names[-1]
        main = n - EXTRA if last else n
        samples, gain = clip_audio(work, name, a, main, END if last else 0)
        fade = int(SR * 0.008)
        total = len(samples) // 2
        for i in range(len(samples)):
            k, v = i // 2, samples[i] * gain
            if k < fade:
                v *= k / fade
            if not last and total - 1 - k < fade:
                v *= (total - 1 - k) / fade
            if last and k >= int(main / 60 * SR):      # the dissolve: fade away over 3.6 s
                v *= max(0, 1 - (k - int(main / 60 * SR)) / int(3.6 * SR)) ** 2
            samples[i] = int(max(-32768, min(32767, v)))
        pcm.extend(samples)
        bounds.append(frames)
        frames += main
    games = frames
    (tmp / 'mix.s16').write_bytes(pcm.tobytes())
    total_t = (IN + games) / 60 + END
    inputs = ['-framerate', '60', '-loop', '1', '-t', f'{IN / 60:.4f}', '-i', str(tmp / 'intro.png')]
    for name in names:
        inputs += ['-i', str(work / f'{name}.mkv')]
    inputs += ['-loop', '1', '-framerate', '60', '-i', '__END__']
    src = ['-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', str(tmp / 'mix.s16')]
    nclip = len(names)
    trims = [f'[0:v]scale={W}:{H},format=gbrp,fps=60,setsar=1[c0]']
    for i, name in enumerate(names):
        a, n = windows[name]
        trims.append(f'[{i + 1}:v]format=gbrp,setsar=1[c{i + 1}]')
    cat = ''.join(f'[c{i}]' for i in range(nclip + 1))
    graph = (';'.join(trims) + f';{cat}concat=n={nclip + 1}:v=1:a=0,fps=60,settb=1/60,setpts=N[g];'
             f'[{nclip + 1}:v]scale={W}:{H}:flags=lanczos,format=gbrp,fps=60,trim=duration={END + EXTRA / 60:.4f},setpts=N,settb=1/60[e];'
             f'[g][e]xfade=transition=fade:duration={EXTRA / 60:.4f}:offset={(IN + games) / 60:.4f},'
             'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]')
    (tmp / 'graph.txt').write_text(graph)
    # Loudness: measure, then normalise to -14 LUFS as the trailer does.
    m = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', *src, '-af', 'loudnorm=I=-14:TP=-2.5:LRA=9:print_format=json',
                        '-f', 'null', '-'], capture_output=True, text=True).stderr
    j = json.loads(re.search(r'\{[^{}]*"input_i"[^{}]*\}', m, re.S).group(0))
    af = (f"loudnorm=I=-14:TP=-2.5:LRA=9:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true,aresample=48000")
    out.mkdir(parents=True, exist_ok=True)
    for kind in ('YouTube', 'X'):
        crf = '14' if kind == 'YouTube' else '16'
        target = work / f'palettes-{kind}.mp4'          # copied to --out only when complete
        cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y'] + [str(tmp / f'end-{kind}.png') if x == '__END__' else x for x in inputs] + src + [
            '-/filter_complex', str(tmp / 'graph.txt'), '-map', '[v]', '-map', f'{nclip + 2}:a', '-af', af,
            '-t', f'{total_t:.4f}', '-c:v', 'libx264', '-preset', 'slow', '-crf', crf, '-profile:v', 'high', '-level', '4.2',
            '-g', '60', '-bf', '2', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
            '-color_range', 'tv', '-r', '60', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', str(target)]
        subprocess.run(cmd, check=True)
        final = out / f'Ninja Ryukenden Enhanced v{version} - Palettes ({kind}).mp4'
        k = 2
        while final.exists():                          # never overwrite what is there
            final = out / f'Ninja Ryukenden Enhanced v{version} - Palettes ({kind}) ({k}).mp4'
            k += 1
        shutil.copyfile(target, final)
        print('wrote', final, flush=True)
    (work / 'build.json').write_text(json.dumps({'bounds': bounds, 'intro_frames': IN, 'game_frames': games, 'total_s': total_t,
                                                 'clips': {n: windows[n] for n in names}}, indent=1))

if __name__ == '__main__':
    main()
