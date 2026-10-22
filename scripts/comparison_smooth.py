#!/usr/bin/env python3
"""Smooth a comparison run: replace hesitant stretches with plain input.

The route bot reaches the end of a stage but dithers (turns, stops, small
hops). This replays a finished run on the original and edits it in passes,
each edit tried from a saved state (default: reroute, unhit, unturn):

- reroute: play the stage again from checkpoint to checkpoint of the old run
  with a small search over plain moves (the bot's own moves where those
  fail), preferring a way on without a hit; where no search passes (a wall
  climb), the old input from the latest checkpoint at which it still
  finishes the stage.
- shortcut: where the next stretch turns back or stalls, plain input (hold
  forward, a running jump, run and slash) that reaches a later point of the
  run sooner (same area and spot, standing, no less health); the run's own
  input continues from that point.
- calm: a stretch in which Ryu turns back and forth is replaced by walking
  straight to where he is at its end and waiting there (or waiting, then
  walking), arriving on the same frame, so enemies keep their timing.
- unhit: before each hit, the same input with slashes or an earlier jump,
  kept only if the stage then ends with more health.
- unturn: each short burst of backward input is replaced by forward input
  or by standing still, and each stall (standing input) is cut out or
  replaced by forward input.

An edit is kept only if the rest of the run still finishes the stage with no
less health and no lost life. A calm edit's replay stops early once the
game's RAM matches the old run again for CONVERGE frames: from there on, the
same input gives the same game. See docs/COMPARISON-VIDEOS.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from comparison_video import STAGE_NAMES, Game, StepError, make_seed, start_point, start_stage

TAIL = 60          # frames after the input, as comparison_video records
STATE_EVERY = 15   # frames between saved states
HORIZON = 240      # frames a shortcut policy may run
MIN_SAVING = 15    # frames a shortcut must save
WINDOW = 200       # look this far ahead for a turn or stall
STALL = 12         # standing frames without moving that count as a stall
CALM = (30, 150)   # frames a calm edit may cover
CONVERGE = 20      # frames of identical RAM that end a calm edit's replay


def expand(segments):
    out = []
    for count, buttons in segments:
        out += [frozenset(buttons)] * count
    return out


def compress(frames):
    segments = []
    for buttons in frames:
        if segments and segments[-1][1] == sorted(buttons):
            segments[-1][0] += 1
        else:
            segments.append([1, sorted(buttons)])
    return segments


def policies(forward):
    """Plain inputs, each a function from frame t to the buttons held."""
    f = {forward}
    out = {'forward': lambda t: f}
    for start in (0, 8, 16, 24, 32):
        for hold in (12, 20):
            out[f'jump{start}/{hold}'] = (lambda s, h: lambda t: f | {'I'} if s <= t < s + h else f)(start, hold)
    out['slash'] = lambda t: f | {'II'} if t % 12 >= 10 else f
    return out


def turns(trace, a, b):
    """On-screen turns of Ryu between frames a and b."""
    xs = [trace[k]['x'] for k in range(a, b + 1)]
    moves = [y - x for x, y in zip(xs, xs[1:]) if y != x and abs(y - x) < 8]
    return sum(1 for m, n in zip(moves, moves[1:]) if (m > 0) != (n > 0))


def turns_or_stalls(trace, p):
    xs = [i['x'] for i in trace[p:p + WINDOW] if i['area'] == trace[p]['area']]
    moving = [b - a for a, b in zip(xs, xs[1:]) if b != a]
    if any((a > 0) != (b > 0) for a, b in zip(moving, moving[1:])):
        return True
    still = 0
    for a, b, i in zip(xs, xs[1:], trace[p + 1:]):
        still = still + 1 if a == b and i['ground'] else 0
        if still >= STALL:
            return True
    return False


class Smoother:
    def __init__(self, game, states, stage, log):
        self.game, self.states, self.stage, self.log = game, states, stage, log
        self.saved = 0

    def info(self):
        r = self.game.read(0, 0x2000)
        return {'area': r[0xe60], 'stage': r[0xe5f], 'master': r[0x240], 'x': int.from_bytes(r[0xe9e:0xea0], 'little'),
                'y': r[0xea0], 'health': r[0xead], 'lives': r[0xeaf], 'boss': r[0x1035],
                'ground': r[0xea7] == 0 and r[0xeaa] in (0, 1), 'ram': hashlib.sha1(r).hexdigest()}

    def done(self, i):
        """The end of the stage, as comparison_video.finishes sees it."""
        return (i['stage'] != self.stage or i['master'] != 0
                or (STAGE_NAMES[self.stage] == '5-4' and i['boss'] == 0))

    def save(self):
        self.saved += 1
        path = self.states / f'{self.saved}.state'
        self.game.call('save_state_file', {'file_path': str(path)})
        return path

    def load(self, path):
        """Load a state with no buttons held (a state does not carry the pad)."""
        self.game.call('load_state_file', {'file_path': str(path)})
        self.game.press(set())

    def step(self, buttons):
        self.game.press(set(buttons))
        self.game.checked_step(1)
        return self.info()

    def finishes(self, frames, start, snap, snaps, old=None, join=None):
        """From the state at frame start, play frames + tail, saving states.

        With `old` (a trace aligned frame for frame), stop once the RAM has
        matched it for CONVERGE frames from frame `join` on and take the rest
        from `old`. Returns (trace from start, frame of convergence or None),
        trace None if the stage does not finish."""
        self.load(snap)
        trace, same = [], 0
        try:
            for n, buttons in enumerate(list(frames) + [frozenset()] * TAIL):
                k = start + n
                if k % STATE_EVERY == 0:
                    snaps[k] = self.save()
                trace.append(self.step(buttons))
                if old is not None and k >= join and trace[-1]['ram'] == old[k]['ram']:
                    same += 1
                    if same >= CONVERGE:
                        trace += old[k + 1:]
                        return trace, k
                else:
                    same = 0
        except StepError:
            return None, None
        return (trace if any(self.done(i) for i in trace) else None), None

    def splice(self, frames, snaps, trace, end, p, replacement, resume, what):
        """Try frames[:p] + replacement + frames[resume:]; the new (frames, snaps,
        trace) if the stage still finishes no worse, else None."""
        spliced = frames[:p] + list(replacement) + frames[resume:]
        aligned = len(replacement) == resume - p
        new_snaps = {k: v for k, v in snaps.items() if k <= p}
        tail, joined = self.finishes(spliced[p:], p, snaps[p], new_snaps,
                                     old=trace if aligned else None, join=resume)
        ok = tail is not None and tail[-1]['health'] >= end['health'] and tail[-1]['lives'] >= end['lives']
        if ok and joined is not None:
            new_snaps.update({k: v for k, v in snaps.items() if k > joined})
        # Delete the states the losing version no longer needs.
        old, new = set(snaps.values()), set(new_snaps.values())
        for path in (old - new) if ok else (new - old):
            Path(path).unlink(missing_ok=True)
        if not ok:
            return None
        self.log(f'frame {p}: {what}' + (f'; rejoins the old run at frame {joined}' if joined is not None else ''))
        return spliced, new_snaps, trace[:p] + tail

    def shortcuts(self, frames, snaps, trace, end):
        p = 0
        while p < len(frames):
            if p % STATE_EVERY or p not in snaps or not turns_or_stalls(trace, p):
                p += 1
                continue
            here = trace[p - 1] if p else trace[0]
            later = [q for q in range(p + MIN_SAVING, min(len(frames), p + WINDOW + HORIZON))
                     if trace[q]['ground'] and trace[q]['area'] == here['area']]
            ahead = trace[min(len(frames) - 1, p + WINDOW)]
            forward = 'right' if ahead['x'] >= here['x'] else 'left'
            best = []
            for name, policy in policies(forward).items():
                self.load(snaps[p])
                for t in range(HORIZON):
                    try:
                        i = self.step(policy(t))
                    except StepError:
                        break
                    if i['health'] == 0 or i['lives'] < here['lives'] or i['area'] != here['area']:
                        break
                    if not i['ground']:
                        continue
                    for q in later:
                        r = trace[q]
                        if (q - (p + t) >= MIN_SAVING and abs(r['x'] - i['x']) <= 2 and r['y'] == i['y']
                                and i['health'] >= r['health']):
                            best.append((q - (p + t), -t, name, t + 1, q))
            best.sort(reverse=True)
            result = None
            for saving, _, name, length, q in best[:4]:
                # After `length` policy frames Ryu is where the run was after frame q.
                policy = policies(forward)[name]
                result = self.splice(frames, snaps, trace, end, p, [frozenset(policy(t)) for t in range(length)],
                                     q + 1, f'{name} for {length} frames reaches frame {q}; saves {saving}')
                if result:
                    frames, snaps, trace = result
                    break
            p += 1
        return frames, snaps, trace

    def walk_and_wait(self, snap, here, target, length, wait_first, slash):
        """Walk straight to target's x and stand, for exactly `length` frames."""
        self.load(snap)
        d = 'right' if target['x'] > here['x'] else 'left'
        sign = 1 if d == 'right' else -1
        out, reached, i = [], abs(target['x'] - here['x']) <= 1, here
        for t in range(length):
            if t < wait_first or reached:
                buttons = {'II'} if slash and t % 16 == 15 else set()
            else:
                buttons = {d}
            try:
                i = self.step(buttons)
            except StepError:
                return None
            out.append(frozenset(buttons))
            if i['area'] != here['area'] or i['health'] == 0 or i['lives'] < here['lives']:
                return None
            if not reached and (i['x'] - target['x']) * sign >= -1:
                reached = True
        if (i['ground'] and abs(i['x'] - target['x']) <= 2 and i['y'] == target['y']
                and i['health'] >= target['health']):
            return out
        return None

    def unturn(self, frames, snaps, trace, end):
        ahead = forward_by_area(trace)
        done = set()
        while True:
            todo = [b for b in bursts(frames, trace, ahead) if (b[0], b[2]) not in done]
            if not todo:
                return frames, snaps, trace
            a, e, kind = todo[0]
            done.add((a, kind))
            fwd = ahead[trace[a]['area']]
            k = max(x for x in snaps if x <= a)
            keep = frames[k:a]
            swap = lambda b: frozenset((b - {'left', 'right'}) | {fwd})
            if kind == 'back':
                edits = [('forward', [swap(b) for b in frames[a:e]]),
                         ('stand', [frozenset(b - {'left', 'right'}) for b in frames[a:e]])]
            else:
                edits = [('cut', []), ('forward', [swap(b) for b in frames[a:e]])]
            for name, edit in edits:
                result = self.splice(frames, snaps, trace, end, k, keep + edit, e,
                                     f'{kind} input {a}-{e} -> {name}')
                if result:
                    frames, snaps, trace = result
                    if name == 'cut':                    # later bursts moved
                        done = {(x if x < a else x - (e - a), kd) for x, kd in done}
                    break

    def unhit(self, frames, snaps, trace, end):
        """For each hit, the same input with slashes (in the air, which keeps
        the path, or anywhere) or an earlier jump in the second or so before
        it; kept if the stage then finishes with more health."""
        done = set()
        while True:
            hits = [k for k in range(1, len(frames))
                    if trace[k]['health'] < trace[k - 1]['health'] and k not in done]
            if not hits:
                return frames, snaps, trace
            h = hits[0]
            done.add(h)
            better = dict(trace[-1], health=trace[-1]['health'] + 1)
            for back in (15, 30, 45, 60):
                p = max([x for x in snaps if x <= h - back], default=None)
                if p is None:
                    break
                window = list(zip(range(p, h + 1), frames[p:h + 1]))
                variants = {
                    'air slashes': [b | {'II'} if not trace[k - 1]['ground'] and (k - p) % 12 < 2 else b
                                    for k, b in window],
                    'slashes': [b | {'II'} if (k - p) % 12 < 2 else b for k, b in window],
                    'an earlier jump': [b | {'I'} if k - p < 20 else b for k, b in window]}
                result = None
                for name, edit in variants.items():
                    if edit == frames[p:h + 1]:
                        continue
                    result = self.splice(frames, snaps, trace, better, p, edit, h + 1,
                                         f'hit at {h}: {name} from frame {p}')
                    if result:
                        frames, snaps, trace = result
                        break
                if result:
                    break

    def calm(self, frames, snaps, trace, end):
        p = 0
        while p < len(frames) - CALM[0]:
            if p % STATE_EVERY or p not in snaps:
                p += 1
                continue
            here = trace[p - 1] if p else trace[0]
            ends = [q for q in range(min(len(frames) - 1, p + CALM[1]), p + CALM[0] - 1, -1)
                    if trace[q]['ground'] and trace[q]['area'] == here['area'] and turns(trace, p, q) >= 2]
            result = None
            for q in ends[::8][:4]:
                length = q - p + 1
                walk = int(abs(trace[q]['x'] - here['x']) / 1.5) + 3
                for wait_first, slash in ((0, False), (max(0, length - walk), False), (0, True), (max(0, length - walk), True)):
                    replacement = self.walk_and_wait(snaps[p], here, trace[q], length, wait_first, slash)
                    if replacement is None:
                        continue
                    result = self.splice(frames, snaps, trace, end, p, replacement, q + 1,
                                         f'calm {length} frames ({turns(trace, p, q)} turns) to frame {q}')
                    break                                # one replay per end point
                if result:
                    break
            if result:
                frames, snaps, trace = result
                p = q + 1
            else:
                p += 1
        return frames, snaps, trace


def forward_by_area(trace):
    """The direction each area is played in (None where Ryu mostly climbs)."""
    first, last = {}, {}
    for i in trace:
        first.setdefault(i['area'], i['x'])
        last[i['area']] = i['x']
    return {a: None if abs(last[a] - first[a]) < 64 else ('right' if last[a] > first[a] else 'left') for a in first}


def bursts(frames, trace, ahead):
    """(start, end, kind) runs of backward input ('back') or standing input
    on the ground ('still'), in frame order."""
    out, k = [], 0
    while k < len(frames):
        fwd = ahead.get(trace[k]['area'])
        back = {'left': 'right', 'right': 'left'}.get(fwd)
        kind = 'back' if back in frames[k] else 'still' if not frames[k] & {'left', 'right', 'I'} else None
        e = k
        while e < len(frames) and kind and trace[e]['area'] == trace[k]['area'] and (
                (back in frames[e]) if kind == 'back' else not frames[e] & {'left', 'right', 'I'}):
            e += 1
        if kind == 'back' and fwd and not ('I' in frames[k] and e - k <= 4):   # keep wall hops
            out.append((k, e, kind))
        elif kind == 'still' and fwd and e - k >= STALL and trace[k]['ground']:
            out.append((k, e, kind))
        k = max(e, k + 1)
    return out


def smooth_moves(f, b):
    """Plain moves a player would use; each ends with I and II released."""
    return {
        'run8': [(8, {f})], 'run16': [(16, {f})],
        'jump': [(20, {f, 'I'}), (4, {f})], 'hop': [(8, {f, 'I'}), (8, {f})],
        'jumpup': [(20, {'I'}), (4, set())],
        'slash': [(2, {f, 'II'}), (10, {f})], 'standslash': [(2, {'II'}), (10, set())],
        'jumpslash': [(6, {f, 'I'}), (2, {f, 'I', 'II'}), (12, {f, 'I'}), (4, {f})],
        'wait': [(8, set())]}


def all_moves(f, b):
    """The route bot's moves too (back steps, wall hops, climbing), where plain moves fail."""
    from comparison_route import moves
    return {**{name: [(n, set(x)) for n, x in segs] for name, segs in moves(f, b).items()}, **smooth_moves(f, b)}


REROUTE_EVERY = 90   # old-run frames between waypoints (plus every area change)
REROUTE_WIDTH = 6
REROUTE_DEPTH = 12
WIDE = (16, 24)      # (width, depth) of the last search before the old input
HIT_DEPTH = 4        # further moves searched for a way on without a hit
HIT_COST = 150       # old-run frames of progress a hit is worth giving up


def waypoints(trace, length):
    w = set(range(REROUTE_EVERY, length, REROUTE_EVERY))
    w |= {k for k in range(1, length) if trace[k]['area'] != trace[k - 1]['area']}
    return sorted(w)


def dy(a, b):
    """Vertical distance; Ryu's y byte wraps above the top of the screen."""
    d = abs(a - b) % 256
    return min(d, 256 - d)


def nearest(i, old, lo, hi):
    """(score, old frame, distance) of the furthest-along point of the old run
    near i, between frames lo and hi."""
    near = [(abs(old[k]['x'] - i['x']) + dy(old[k]['y'], i['y']), k)
            for k in range(max(0, lo), hi + 1) if old[k]['area'] == i['area']]
    if not near:
        return (hi + 50, hi, 0) if i['area'] > old[hi]['area'] else (lo - 100, lo, 999)
    d = min(near)[0]
    k = max(k for e, k in near if e <= d + 4)      # the old run passes a spot more than once
    return k - 0.5 * d, k, d


class Rerouter:
    """Play a stage again with plain moves, from waypoint to waypoint of an old run."""

    def __init__(self, smoother, old, length):
        self.s, self.old, self.length = smoother, old, length

    @staticmethod
    def reach(j, hi, elapsed):
        """How far along the old path a match may be after `elapsed` new frames:
        positions repeat (shafts, backtracking), so progress must be continuous."""
        return min(hi, j + 2 * elapsed + 60)

    def rank(self, i, j, targets, elapsed):
        """Index of the furthest target Ryu is at or past along the old path, or None."""
        _, k, d = nearest(i, self.old, j, self.reach(j, targets[-1], elapsed))
        if d > 10:
            return None
        return next((r for r in range(len(targets) - 1, -1, -1) if k >= targets[r]), None)

    def direction(self, k):
        a, b = self.old[k], self.old[min(k + 45, self.length - 1)]
        return 'right' if b['area'] != a['area'] or b['x'] >= a['x'] else 'left'

    def beam(self, snap, info, j, targets, moveset, width=REROUTE_WIDTH, depth=REROUTE_DEPTH):
        """Search moves from (snap, info); (rank, inputs, snap, info) of the target
        reached at the first depth that reaches one (or up to HIT_DEPTH moves later,
        if that way takes a hit): with the least health lost, then the furthest,
        then the soonest; or None."""
        s, hi = self.s, targets[-1]
        frontier = [(nearest(info, self.old, j, self.reach(j, hi, 0))[0], [], snap, info)]
        live, found, first = set(), None, None
        try:
            for d in range(depth + HIT_DEPTH):
                if d >= depth and not found:
                    return None
                children = {}
                for _, inputs, node, at in frontier:
                    f = self.direction(nearest(at, self.old, j, self.reach(j, hi, len(inputs)))[1])
                    b = 'left' if f == 'right' else 'right'
                    for name, segs in moveset(f, b).items():
                        s.load(node)
                        seq, i, ok = [], at, True
                        for n, buttons in segs:
                            for _ in range(n):
                                try:
                                    i = s.step(buttons)
                                except StepError:
                                    ok = False
                                    break
                                seq.append(frozenset(buttons))
                                if i['health'] == 0 or i['lives'] < info['lives']:
                                    ok = False
                                    break
                                rank = len(targets) if s.done(i) else self.rank(i, j, targets, len(inputs) + len(seq))
                                if rank is not None and (found is None or (i['health'], rank, -len(inputs) - len(seq)) >
                                                         (found[3]['health'], found[0], -len(found[1]))):
                                    if found:
                                        live.discard(found[2])
                                        Path(found[2]).unlink(missing_ok=True)
                                    found = (rank, inputs + seq, s.save(), i)
                                    live.add(found[2])
                            if not ok:
                                break
                        if not ok:
                            continue
                        score = (nearest(i, self.old, j, self.reach(j, hi, len(inputs) + len(seq)))[0]
                                 - HIT_COST * (info['health'] - i['health'])
                                 - 0.05 * (len(inputs) + len(seq)) - (0 if name in smooth_moves(f, b) else 25))
                        cell = (i['area'], i['x'] // 8, i['y'] // 8)
                        if cell not in children or score > children[cell][0]:
                            if cell in children:
                                Path(children[cell][2]).unlink(missing_ok=True)
                            children[cell] = (score, inputs + seq, s.save(), i)
                for _, _, node, _ in frontier:
                    if node != snap and node not in live:
                        Path(node).unlink(missing_ok=True)
                if found and first is None:
                    first = d
                if found and (found[3]['health'] >= info['health'] or d >= first + HIT_DEPTH):
                    for c in children.values():
                        Path(c[2]).unlink(missing_ok=True)
                    frontier = []
                    return found
                ranked = sorted(children.values(), key=lambda c: c[0], reverse=True)
                for c in ranked[width:]:
                    Path(c[2]).unlink(missing_ok=True)
                frontier = ranked[:width]
                if not frontier:
                    return None
            return None
        finally:
            for _, _, node, _ in frontier:
                if node != snap and (not found or node != found[2]):
                    Path(node).unlink(missing_ok=True)


REJOIN = 12   # frames of alignment tried when falling back on the old input


def rejoin(s, old, marks, frames, snap, j, lives, past):
    """From a state near old frame j, the old run's own input (aligned within
    REJOIN frames) until Ryu is back on the old path at a checkpoint beyond
    old frame `past`, or the stage ends: (old frame or None, input, state,
    info), or None."""
    for off in sorted(range(-REJOIN, REJOIN + 1), key=abs):
        m = j + off                         # assume the state is old frame m
        if m < -1:
            continue
        s.load(snap)
        seq = []
        try:
            for k, buttons in enumerate(frames[m + 1:] + [frozenset()] * TAIL, start=m + 1):
                i = s.step(buttons)
                seq.append(buttons)
                if i['health'] == 0 or i['lives'] < lives:
                    break
                if s.done(i):
                    return None, seq, s.save(), i
                o = old[k] if k < len(frames) else None
                if (o and k > past and k in marks and o['area'] == i['area']
                        and abs(o['x'] - i['x']) + dy(o['y'], i['y']) <= 4):
                    return k, seq, s.save(), i
        except StepError:
            continue
    return None


def reroute(s, frames, snaps, trace, end):
    old, length = trace, len(frames)
    r = Rerouter(s, old, length)
    marks = waypoints(old, length)
    markset = set(marks)
    s.load(snaps[0])
    j, snap, info, new = -1, snaps[0], s.info(), []          # j: the old frame Ryu is at (-1: before frame 0)
    history = []                                               # (old frame, state, info, new length)
    try:
        while True:
            targets = [w for w in marks if w > j][:3] or [length - 1]
            found = (r.beam(snap, info, j, targets, smooth_moves) or r.beam(snap, info, j, targets, all_moves)
                     or r.beam(snap, info, j, targets, all_moves, *WIDE))
            if found:
                rank, inputs, snap2, info2 = found
                history.append((j, snap, info, len(new)))
                new += inputs
                snap, info = snap2, info2
                if rank == len(targets):                             # the stage finished
                    break
                j = targets[rank]
                s.log(f'reroute: old frame {j} reached at new frame {len(new)} '
                      f'(area {info["area"]} x {info["x"]} y {info["y"]}; old x {old[j]["x"]} y {old[j]["y"]})')
                continue
            # No plain way on: the old input, from here or from an earlier
            # checkpoint, past the hard part. The first checkpoint is the old
            # run's own start, so this always finds a way on.
            options = [(j, snap, info, len(new))] + list(reversed(history))
            for j0, snap0, info0, n0 in options:
                back = rejoin(s, old, markset, frames, snap0, j0, info0['lives'], targets[0])
                if back:
                    k, inputs, snap2, info2 = back
                    keep = [h for h in history if h[3] < n0 or h[0] == j0 and h[3] == n0]
                    for h in history:
                        if h not in keep and h[1] not in (snap0, snaps[0]):
                            Path(h[1]).unlink(missing_ok=True)
                    history = keep if (j0, snap0, info0, n0) in keep else keep + [(j0, snap0, info0, n0)]
                    new = new[:n0] + inputs
                    snap, info = snap2, info2
                    s.log(f'reroute: old input from old frame {j0} (new frame {n0}) '
                          + (f'back on the path at old frame {k}' if k is not None else 'to the end of the stage'))
                    break
            else:
                s.log(f'reroute: no way on from old frame {j} (area {info["area"]} x {info["x"]} y {info["y"]}, '
                      f'targets {targets}); keeping the run')
                return frames, snaps, trace
            if k is None:
                break
            j = k
    finally:
        for _, state, _, _ in history:
            if state != snaps[0]:
                Path(state).unlink(missing_ok=True)
    new_snaps = {}
    tail, _ = s.finishes(new, 0, snaps[0], new_snaps)
    if tail is None or tail[-1]['lives'] < end['lives']:
        s.log('reroute: the new route does not replay to the end; keeping the run')
        return frames, snaps, trace
    s.log(f'reroute: {length} -> {len(new)} frames, health at the end {tail[-1]["health"]} (was {end["health"]})')
    for path in set(snaps.values()) - {snaps[0]}:
        Path(path).unlink(missing_ok=True)
    new_snaps[0] = snaps[0]
    return new, new_snaps, tail


def smooth(game, rom, run, passes=('reroute', 'unhit', 'unturn'), log=print, checkpoint=None):
    """The smoothed segments; `checkpoint(pass, segments)` is called after each pass."""
    stage = run['stage']
    states = Path(tempfile.mkdtemp(prefix='comparison-smooth-'))
    try:
        start_point(game, rom, make_seed(game.binary, rom, states / 'seed.state'))
        start_stage(game, stage)
        s = Smoother(game, states, stage, log)
        frames = expand(run['segments'])
        snaps = {}
        first = s.save()
        trace = s.finishes(frames, 0, first, snaps)[0] or s.finishes(frames, 0, first, snaps)[0]
        if trace is None:
            raise ValueError('The run does not finish from the canonical start')
        end = trace[-1]
        steps = {'reroute': lambda: reroute(s, frames, snaps, trace, end),
                 'shortcut': lambda: s.shortcuts(frames, snaps, trace, end),
                 'calm': lambda: s.calm(frames, snaps, trace, end),
                 'unhit': lambda: s.unhit(frames, snaps, trace, end),
                 'unturn': lambda: s.unturn(frames, snaps, trace, end)}
        for name in steps:
            if name in passes:
                frames, snaps, trace = steps[name]()
                if name in ('reroute', 'unhit'):
                    end = trace[-1]
                if checkpoint:
                    checkpoint(name, compress(frames))
        return compress(frames)
    finally:
        shutil.rmtree(states, ignore_errors=True)


def reversals(segments):
    last, count = None, 0
    for _, buttons in segments:
        d = 'left' if 'left' in buttons else 'right' if 'right' in buttons else None
        if d and last and d != last:
            count += 1
        last = d or last
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True, help='Original ROM')
    parser.add_argument('run', type=Path)
    parser.add_argument('--out', type=Path, help='Default: overwrite the run file')
    parser.add_argument('--passes', default='reroute,unhit,unturn', help='Comma-separated, in this order: reroute, shortcut, calm, unhit, unturn')
    args = parser.parse_args()
    run = json.loads(args.run.read_text())
    out_path = args.out or args.run
    note = 'Smoothed with scripts/comparison_smooth.py (plain-input edits, each verified to finish).'

    def write(path, segments):
        out = dict(run, frames=sum(n for n, _ in segments), segments=segments,
                   notes=run.get('notes', '') + ('' if note in run.get('notes', '') else ' ' + note))
        path.write_text(json.dumps(out, separators=(',', ':')) + '\n')

    def checkpoint(name, segments):
        # Each pass's result, kept so that a long smoothing can resume from it.
        write(out_path.with_name(f'{out_path.stem}.after-{name}.json'), segments)
        print(f'{name}: {sum(n for n, _ in segments)} frames, direction changes {reversals(segments)}', flush=True)

    work = Path(tempfile.mkdtemp(prefix='comparison-smooth-log-'))
    try:
        with Game(args.emulator, work) as game:
            segments = smooth(game, args.rom.resolve(), run, tuple(args.passes.split(',')),
                              log=lambda m: print(m, flush=True), checkpoint=checkpoint)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f'{run["name"]}: {run["frames"]} -> {sum(n for n, _ in segments)} frames, '
          f'direction changes {reversals(run["segments"])} -> {reversals(segments)}')
    write(out_path, segments)


if __name__ == '__main__':
    main()
