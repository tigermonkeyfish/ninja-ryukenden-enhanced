#!/usr/bin/env python3
"""Extend research/longplay/full.json by one stage (emulator evidence only).

Boots the ROM under test with ORIGINAL in backup RAM (longplay_lib), replays
full.json so far, then runs the comparison_route depth-first search from that
state until the stage changes (or the boss dies), plays the transition idle
until gameplay of the next stage is ready, and appends the segments plus a
stage marker to full.json. --prefix-extra FILE adds hand-scripted segments
before the search (same [frames,[buttons]] format).
"""
import argparse
import json
import sys
import tempfile
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import comparison_route as cr                                            # noqa: E402
from longplay_lib import EMULATOR, ROM, boot_to_first_update, Game        # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / 'research/longplay/full.json'


def load_full():
    if FULL.exists():
        return json.loads(FULL.read_text())
    return {'rom': ROM.name, 'mode': 'original', 'stages': [], 'segments': []}


def play(game, segments):
    for count, buttons in segments:
        game.press(set(buttons))
        game.checked_step(count)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True, help='label of the stage being searched, e.g. 1-2')
    ap.add_argument('--boss-hp', type=lambda s: int(s, 0), help='RAM address of the boss health')
    ap.add_argument('--forward', choices=['left', 'right'], help='boss room fighting direction')
    ap.add_argument('--budget', type=int, default=4000)
    ap.add_argument('--frames', type=int, default=9000, help='frame limit for this stage')
    ap.add_argument('--extra', type=Path, help='hand-scripted segments played before the search')
    ap.add_argument('--extra-frames', type=int, default=10 ** 9)
    ap.add_argument('--out', type=Path, help='write the extended run here instead of full.json')
    ap.add_argument('--commit-partial', action='store_true', help='write unfinished search into the output as a partial stage')
    args = ap.parse_args()
    full = load_full()
    states = Path(tempfile.mkdtemp(prefix='longplay-', dir='/workspace/build/longplay'))
    boss = None
    if args.boss_hp:
        boss = {'hp': args.boss_hp, 'forward': args.forward or 'right'}
    try:
        with Game(EMULATOR, states) as game:
            t0 = time.time()
            boot_to_first_update(game, ROM, 'original', states / 'entered.state')
            search = cr.Search(game, states, boss)
            base = [[n, sorted(b)] for n, b in full['segments']]
            search.play(base)
            total0 = sum(n for n, _ in base)
            extra = []
            if args.extra:
                got = 0
                for n, b in json.loads(args.extra.read_text())['segments']:
                    if got + n > args.extra_frames:
                        break
                    extra.append([n, sorted(b)])
                    got += n
                search.play(extra)
            print(f'replayed {total0} + {sum(n for n, _ in extra)} frames in {time.time() - t0:.0f}s', search.info(), flush=True)
            prefix = extra
            start = search.info()
            stage_byte = start['stage']
            dirs = {start['area']: cr.entry_direction(start, boss)}
            snap, cands = search.evaluate(start, *dirs[start['area']])
            stack = [[snap, cands, 0, start, 0]]
            finished, nodes = None, 0
            tmpout = states / 'partial.json'
            while stack and nodes < args.budget:
                nodes += 1
                top = stack[-1]
                snap, cands, idx, info, frames = top
                if idx >= len(cands):
                    search.drop(snap)
                    stack.pop()
                    if stack:
                        stack[-1][2] += 1
                    continue
                segs = cr.moves(*dirs[info['area']])[cands[idx][1]]
                search.load(snap)
                search.play(segs)
                frames2 = frames + sum(n for n, _ in segs)
                new = search.info()
                if new['stage'] != stage_byte or new['master'] != 0 or frames2 >= args.frames \
                        or (boss and new['boss'] == 0):
                    finished = new
                    break
                dirs.setdefault(new['area'], cr.entry_direction(new, boss))
                recent = [e[3] for e in stack[-cr.STALL:]] + [new]
                if (len(recent) > cr.STALL and all(e['area'] == new['area'] for e in recent)
                        and recent[0]['boss'] == new['boss']
                        and max(e['x'] for e in recent) - min(e['x'] for e in recent) < 24
                        and max(e['y'] for e in recent) - min(e['y'] for e in recent) < 40):
                    search.trap[search.cell(new)] += 1
                    for e in stack[-cr.STALL + 1:]:
                        search.drop(e[0])
                    del stack[-cr.STALL + 1:]
                    stack[-1][2] += 1
                    print(f'trap at area {new["area"]} x {new["x"]} y {new["y"]}; back to frame {stack[-1][4]}', flush=True)
                    continue
                snap2, cands2 = search.evaluate(new, *dirs[new['area']])
                if not cands2:
                    search.drop(snap2)
                    top[2] += 1
                    continue
                stack.append([snap2, cands2, 0, new, frames2])
                search.visited[search.cell(new)] += 1
                if len(stack) % 25 == 0:
                    log = cr.route(prefix, stack, dirs)
                    Path(f'/workspace/build/longplay/{args.stage}.partial.json').write_text(json.dumps({'segments': log}))
                    print(f'frame {frames2} area {new["area"]} x {new["x"]} y {new["y"]} cam {new["cam"]} '
                          f'health {new["health"]} lives {new["lives"]} boss {new["boss"]} nodes {nodes} t={time.time() - t0:.0f}s', flush=True)
            log = cr.route(prefix, stack, dirs)
            done = finished is not None and (finished['stage'] != stage_byte or finished['master'] != 0
                                             or bool(boss and finished['boss'] == 0))
            print('done: finished' if done else 'done: NOT finished', sum(n for n, _ in log), finished or '', 'nodes', nodes, flush=True)
            if not done and not args.commit_partial:
                Path(f'/workspace/build/longplay/{args.stage}.partial.json').write_text(json.dumps({'segments': log}))
                return 1
            # replay the final log from the stage's start and let the transition idle
            # settle: idle until gameplay of the next stage is ready
            seen, idle = [], 0
            if done:
                for i in range(1, 1500):
                    game.press(set())
                    game.checked_step(1)
                    r = game.read(0, 0x300)
                    s = (r[0x240], r[0x241], r[0xe5f], r[0xe60])
                    if not seen or seen[-1][1] != s:
                        seen.append((i, s))
                    idle = i
                    if i > 5 and r[0x240] == 0 and r[0xe5f] != stage_byte and r[0xe60] == 0 and i > 20:
                        break
                print('transition', seen, 'idle', idle, flush=True)
            out = args.out or FULL
            segs = base + log + ([[idle, []]] if done and idle else [])
            data = {'rom': ROM.name, 'mode': 'original', 'stages': full['stages'] + [
                {'name': args.stage, 'start_frame': total0, 'finished': done,
                 'end_frame': total0 + sum(n for n, _ in log), 'idle_after': idle}],
                'segments': segs, 'frames': sum(n for n, _ in segs)}
            data['notes'] = full.get('notes', {})
            data['notes'][args.stage] = f'bot search, budget {args.budget}, nodes {nodes}'
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data, separators=(',', ':')) + '\n')
            print('wrote', out, data['frames'])
    finally:
        shutil.rmtree(states, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main() or 0)
