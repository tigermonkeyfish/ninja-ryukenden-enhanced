#!/usr/bin/env python3
"""Search a stage route with real button input for comparison videos.

Plays a stage from its first gameplay update (Level Select entry) on one ROM
and writes a run file for scripts/comparison_video.py. Depth-first search over
short moves: each move is simulated from a save state, followed by a few
lookahead policies, and scored on forward progress, area changes, health,
score and novelty. Fatal moves are dropped; a stretch without progress is
abandoned and its spot avoided. A fixed prefix (hand-scripted or an earlier
run) can be replayed first. See docs/COMPARISON-VIDEOS.md.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import tempfile

from comparison_video import STAGE_NAMES, Game, make_seed, start_point, start_stage

HEALTH, LIVES, X, Y, AREA, STAGE = 0xead, 0xeaf, 0xe9e, 0xea0, 0xe60, 0xe5f
SCORE = 0xed0  # six digits, least significant first
# Boss rooms: the boss's health (16, like Ryu's) and the side Ryu fights from.
BOSSES = {'5-4': {'hp': 0x1035, 'forward': 'left'}}
NOVELTY = 30
STALL = 20     # moves without 24 px across or 40 px up/down: abandon the stretch


def moves(fwd, back):
    f, b = {fwd}, {back}
    return {
        'run': [(8, f)],
        'run2': [(16, f)],
        # Every move ends with I and II released, so the next move's press
        # is a new press.
        'jump': [(20, f | {'I'}), (4, f)],
        'hop': [(6, f | {'I'}), (10, f)],
        'jumpup': [(20, {'I'}), (4, set())],
        'back': [(8, b)],
        'backjump': [(20, b | {'I'}), (4, b)],
        'attack': [(2, f | {'II'}), (6, f)],
        'waitattack': [(6, set()), (2, {'II'}), (8, set())],
        'runattack': [(8, f), (2, f | {'II'}), (6, f)],
        'run16attack': [(16, f), (2, f | {'II'}), (6, f)],
        'attackstill': [(2, {'II'}), (10, set())],
        'jumpattack': [(6, f | {'I'}), (2, f | {'I', 'II'}), (12, f | {'I'}), (4, f)],
        # A fresh I press is needed to jump off a wall.
        'walljump': [(10, b | {'I'}), (2, b), (14, f | {'I'}), (2, f)],
        'wallclimb': [(10, f | {'I'}), (2, f), (14, f | {'I'}), (2, f)],
        # Hanging on a wall: a short hop away and back regrabs it ~20 px
        # higher; repeated, it climbs onto the ledge.
        'wallhop': [(4, b | {'I'}), (12, f)],
        'wallhop3': [(3, b | {'I'}), (14, f)],
        'wallhopback': [(4, f | {'I'}), (12, b)],
        'wallhopback3': [(3, f | {'I'}), (14, b)],
        'up': [(12, {'up'})],
        'climbup': [(30, {'up'})],              # ladders
        # No down moves: down drops through one-way platforms.
        'wait': [(8, set())],
    }


def lookaheads(fwd):
    """Policies played after a move; the move scores by the best one."""
    return [
        [(10, {fwd}), (2, {fwd, 'II'})] * 3,   # run forward, slashing
        [(36, set())],                        # stand still
        [(20, {fwd, 'I'}), (16, {fwd})],      # jump forward
    ]


class Search:
    def __init__(self, game, states, boss=None):
        self.game = game
        self.states = states
        self.boss = boss
        self.n = 0
        self.visited = Counter()
        self.trap = Counter()

    def play(self, segments):
        for count, buttons in segments:
            self.game.press(set(buttons))
            self.game.step(count)

    def info(self):
        r = self.game.read(0, 0x1000)
        return {'x': int.from_bytes(r[X:X + 2], 'little'), 'y': r[Y], 'area': r[AREA], 'stage': r[STAGE],
                'lives': r[LIVES], 'health': r[HEALTH], 'cam': int.from_bytes(r[0x20f:0x211], 'little'),
                'score': sum(r[SCORE + i] * 10 ** i for i in range(6)),
                'pages': r[0x237],
                'boss': self.game.read(self.boss['hp'], 1)[0] if self.boss else 0,
                'master': self.game.read(0x240, 1)[0]}

    def save(self):
        self.n += 1
        path = str(self.states / f's{self.n}.state')
        self.game.call('save_state_file', {'file_path': path})
        return path, set(self.game.held)

    def load(self, snap):
        self.game.call('load_state_file', {'file_path': snap[0]})
        held = snap[1]
        self.game.press(set())
        self.game.held = set()
        self.game.press(held)

    @staticmethod
    def drop(snap):
        Path(snap[0]).unlink(missing_ok=True)

    @staticmethod
    def cell(info):
        return info['area'], info['x'] // 16, info['y'] // 16

    @staticmethod
    def lost(cur, info):
        """Dead, or back in an earlier area."""
        if info['stage'] != cur['stage']:
            return False
        return info['health'] == 0 or info['lives'] < cur['lives'] or info['area'] < cur['area']

    def evaluate(self, cur, fwd, back):
        out = []
        snap = self.save()
        for name, segs in moves(fwd, back).items():
            self.load(snap)
            self.play(segs)
            mid = self.info()
            if self.lost(cur, mid):
                continue
            after = self.save()
            best = None
            for policy in lookaheads(fwd):
                self.load(after)
                self.play(policy)
                end = self.info()
                if self.lost(cur, end):
                    continue
                if end['stage'] != cur['stage'] or end['area'] > cur['area'] or mid['area'] > cur['area'] \
                        or end['master'] != 0:
                    score = 1e6
                elif self.boss:
                    score = 200 * (cur['boss'] - end['boss'])
                else:
                    score = (cur['x'] - end['x']) if fwd == 'left' else (end['x'] - cur['x'])
                score -= 60 * (cur['health'] - min(mid['health'], end['health']))
                score += (end['score'] - cur['score']) / 2
                # At an area's far end the way on is up (4-2 ends on a wall
                # climb): height scores once the area cannot scroll further.
                edge = end['pages'] * 256 - 72 if fwd == 'right' else 72
                if (end['x'] >= edge) if fwd == 'right' else (end['x'] <= edge):
                    score += 2 * (cur['y'] - end['y'])
                score += NOVELTY / (1 + self.visited[self.cell(end)])
                score -= 150 * (self.trap[self.cell(end)] + self.trap[self.cell(mid)])
                best = score if best is None else max(best, score)
            self.drop(after)
            if best is not None:
                out.append((best, name))
        out.sort(reverse=True)
        return snap, out


def route(prefix, stack, dirs):
    """The committed input: the prefix, then each stack entry's chosen move."""
    log = list(prefix)
    for snap, cands, idx, info, frames in stack:
        log.extend([[n, sorted(b)] for n, b in moves(*dirs[info['area']])[cands[idx][1]]])
    return log


def checkpoint(out, stage, name, prefix, stack, dirs):
    """Write the route so far (unfinished), so a search can be resumed with --prefix."""
    log = route(prefix, stack, dirs)
    out.write_text(json.dumps({'stage': stage, 'name': name, 'frames': sum(n for n, _ in log),
                               'finished': False, 'segments': log}, separators=(',', ':')) + '\n')


def entry_direction(info, boss=None):
    """An area that opens scrolled to its right end is played leftward."""
    if boss:
        return (boss['forward'], 'right' if boss['forward'] == 'left' else 'left')
    return ('left', 'right') if info['cam'] > 0 else ('right', 'left')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True, help='Original ROM (routes replay on both)')
    parser.add_argument('--stage', required=True, choices=STAGE_NAMES)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, help='Run file whose segments are replayed first, unchanged')
    parser.add_argument('--prefix-frames', type=int, default=10 ** 9, help='Replay whole prefix segments up to this frame')
    parser.add_argument('--budget', type=int, default=8000, help='Search nodes')
    parser.add_argument('--frames', type=int, default=15000)
    args = parser.parse_args()
    stage = STAGE_NAMES.index(args.stage)
    states = Path(tempfile.mkdtemp(prefix='comparison-route-'))
    try:
        with Game(args.emulator, states) as game:
            start_point(game, args.rom, make_seed(args.emulator, args.rom, states / 'seed.state'))
            start_stage(game, stage)
            boss = BOSSES.get(args.stage)
            search = Search(game, states, boss)
            prefix, total = [], 0
            if args.prefix:
                for count, buttons in json.loads(args.prefix.read_text())['segments']:
                    if total + count > args.prefix_frames:
                        break
                    prefix.append([count, sorted(buttons)])
                    total += count
                search.play(prefix)
                print('replayed prefix frames', total, search.info(), flush=True)
            start = search.info()
            dirs = {start['area']: entry_direction(start, boss)}
            snap, cands = search.evaluate(start, *dirs[start['area']])
            stack = [[snap, cands, 0, start, total]]   # snap, candidates, index, info, frames
            finished, nodes = None, 0
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
                segs = moves(*dirs[info['area']])[cands[idx][1]]
                search.load(snap)
                search.play(segs)
                frames2 = frames + sum(n for n, _ in segs)
                new = search.info()
                if new['stage'] != start['stage'] or new['master'] != 0 or frames2 >= args.frames \
                        or (boss and new['boss'] == 0):
                    finished = new
                    break
                dirs.setdefault(new['area'], entry_direction(new, boss))
                recent = [e[3] for e in stack[-STALL:]] + [new]
                if (len(recent) > STALL and all(e['area'] == new['area'] for e in recent)
                        and recent[0]['boss'] == new['boss']
                        and max(e['x'] for e in recent) - min(e['x'] for e in recent) < 24
                        and max(e['y'] for e in recent) - min(e['y'] for e in recent) < 40):
                    search.trap[search.cell(new)] += 1
                    for e in stack[-STALL + 1:]:
                        search.drop(e[0])
                    del stack[-STALL + 1:]
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
                    checkpoint(args.out, stage, args.stage, prefix, stack, dirs)
                    print(f'frame {frames2} area {new["area"]} x {new["x"]} y {new["y"]} cam {new["cam"]} '
                          f'health {new["health"]} lives {new["lives"]} nodes {nodes}', flush=True)
            log = route(prefix, stack, dirs)
            last = finished or (stack[-1][3] if stack else start)
            frames = sum(n for n, _ in log)
            done = bool(finished and (finished['stage'] != start['stage'] or finished['master'] != 0
                                      or (boss and finished['boss'] == 0)))
            print('done: stage finished' if done else 'done: NOT finished',
                  'frames', frames, last, 'nodes', nodes)
            args.out.write_text(json.dumps({
                'stage': stage, 'name': args.stage, 'frames': frames,
                'finished': done,
                'segments': log}, separators=(',', ':')) + '\n')
    finally:
        shutil.rmtree(states, ignore_errors=True)


if __name__ == '__main__':
    main()
