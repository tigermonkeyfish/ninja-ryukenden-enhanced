"""Beam search over button input toward waypoints (in-process core, fastemu).

Diagnostic route tool for the longplay: every node is a real emulator state
reached with button input only. A leg goes from a state through waypoints
(x, y, radius[, area]) to a goal predicate; nodes are scored by waypoint
progress, distance to the next waypoint and health, deduplicated by position
cell, and the beam is shared between waypoint levels so a doomed lead (a jump
into a pit) does not crowd out the slower ways. Worker processes each own an
in-process core and the states of their nodes (states never cross processes
except to rebalance). The result is [frames, [buttons]] segments that replay
the leg exactly from the start state.
"""
import multiprocessing as mp
import time
from fastemu import Fast, BITS

NAMES = {v: k for k, v in BITS.items()}
R, L, I, II, U, D = BITS['right'], BITS['left'], BITS['I'], BITS['II'], BITS['up'], BITS['down']
ACTIONS = [0, R, L, R | I, L | I, I, R | II, L | II, II, R | I | II, L | I | II]


def buttons(m):
    return sorted(NAMES[b] for b in NAMES if m & b)


def _worker(conn, key_bytes):
    f = Fast()
    store, nid = {}, 0
    while True:
        cmd = conn.recv()
        op = cmd[0]
        if op == 'put':
            nid += 1
            store[nid] = cmd[1]
            conn.send(nid)
        elif op == 'get':
            conn.send(store[cmd[1]])
        elif op == 'keep':
            keep = cmd[1]
            for k in list(store):
                if k not in keep:
                    del store[k]
            conn.send(len(store))
        elif op == 'expand':
            _, ids, actions, chunk = cmd
            out = []
            for pid in ids:
                st = store[pid]
                for a in actions:
                    f.load(st)
                    if isinstance(a, tuple):
                        for n, m in a:
                            f.step(n, m)
                    else:
                        f.step(chunk, a)
                    nid += 1
                    store[nid] = f.save()
                    out.append((pid, a, nid, f.info(), tuple(f.ram[b] for b in key_bytes)))
            conn.send(out)
        elif op == 'quit':
            conn.send(None)
            return


class Pool:
    def __init__(self, workers=4, key_bytes=(0xea7, 0xeaa)):
        ctx = mp.get_context('fork')
        self.conns, self.procs = [], []
        for _ in range(workers):
            a, b = ctx.Pipe()
            p = ctx.Process(target=_worker, args=(b, key_bytes), daemon=True)
            p.start()
            self.conns.append(a)
            self.procs.append(p)

    def close(self):
        for c in self.conns:
            c.send(('quit',))
            c.recv()
        for p in self.procs:
            p.join(timeout=5)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class Node:
    __slots__ = ('ref', 'parent', 'mask', 'frames', 'info', 'wp', 'score', 'depth', 'key')

    def __init__(self, ref, parent, mask, frames, info, wp, score, depth, key=()):
        self.ref, self.parent, self.mask, self.frames = ref, parent, mask, frames
        self.info, self.wp, self.score, self.depth, self.key = info, wp, score, depth, key

    def segments(self):
        out, n = [], self
        while n.parent is not None:
            if isinstance(n.mask, tuple):
                out.extend(reversed(n.mask))
            else:
                out.append((n.frames, n.mask))
            n = n.parent
        out.reverse()
        merged = []
        for fr, m in out:
            if merged and merged[-1][1] == m:
                merged[-1][0] += fr
            else:
                merged.append([fr, m])
        return [[fr, buttons(m)] for fr, m in merged]


def near(info, wp):
    x, y, r = wp[0], wp[1], wp[2]
    if len(wp) > 3 and wp[3] is not None and info['area'] != wp[3]:
        return False
    ry = wp[4] if len(wp) > 4 else r
    return abs(info['x'] - x) <= r and abs(info['y'] - y) <= ry


def search(pool, state, waypoints, goal, width=60, chunk=4, max_frames=3000, actions=ACTIONS,
           lost=None, hp_weight=40, log=print, seconds=600, ywt=0.3, levels=3, prefer=None, stall_frames=600):
    """Return (node, reason). goal(info) -> True ends the leg. `prefer(info)` adds to the score."""
    W = len(pool.conns)
    pool.conns[0].send(('put', state))
    ref = (0, pool.conns[0].recv())
    f = Fast()
    f.load(state)
    i0 = f.info()
    if lost is None:
        def lost(i):
            return (i['health'] == 0 or i['lives'] < i0['lives']
                    or (i['stage'] == i0['stage'] and i['area'] < i0['area']))

    def score(info, wp):
        s = 100000 * wp + hp_weight * info['health']
        if wp < len(waypoints):
            w = waypoints[wp]
            s -= abs(info['x'] - w[0]) + ywt * abs(info['y'] - w[1])
        if prefer:
            s += prefer(info)
        return s

    root = Node(ref, None, 0, 0, i0, 0, score(i0, 0), 0)
    beam = [root]
    t0 = time.time()
    best = root
    frames = 0
    best_frames = 0
    depth = 0
    while frames < max_frames:
        depth += 1
        by_w = [[] for _ in range(W)]
        for n in beam:
            by_w[n.ref[0]].append(n)
        # rebalance: move states from loaded workers to light ones
        avg = (len(beam) + W - 1) // W
        spare = [n for w in range(W) for n in by_w[w][avg:]]
        for w in range(W):
            del by_w[w][avg:]
        for n in spare:
            w = min(range(W), key=lambda k: len(by_w[k]))
            pool.conns[n.ref[0]].send(('get', n.ref[1]))
            st = pool.conns[n.ref[0]].recv()
            pool.conns[w].send(('put', st))
            n.ref = (w, pool.conns[w].recv())
            by_w[w].append(n)
        for w in range(W):
            pool.conns[w].send(('expand', [n.ref[1] for n in by_w[w]], actions, chunk))
        cand = {}
        nodes = {n.ref: n for n in beam}
        goal_node = None
        for w in range(W):
            for pid, a, nid, i, kb in pool.conns[w].recv():
                parent = nodes[(w, pid)]
                if lost(i):
                    continue
                wp = parent.wp
                while wp < len(waypoints) and near(i, waypoints[wp]):
                    wp += 1
                fr = sum(n for n, _ in a) if isinstance(a, tuple) else chunk
                node = Node((w, nid), parent, a, fr, i, wp, score(i, wp), depth)
                if goal(i) and goal_node is None:
                    goal_node = node
                k = (wp, i['area'], i['x'] // 3, i['y'] // 3) + kb
                if k not in cand or cand[k].score < node.score:
                    cand[k] = node
        frames += chunk
        if goal_node is not None:
            log(f'goal at depth {depth} {goal_node.info} t={time.time() - t0:.0f}s')
            return goal_node, 'goal'
        if not cand:
            return best, 'dead end'
        ranked = sorted(cand.values(), key=lambda n: -n.score)
        # share the beam between the top waypoint levels
        top = ranked[0].wp
        keep, used = [], set()
        for lvl in range(levels):
            quota = width // (2 ** (lvl + 1)) if lvl < levels - 1 else width
            for n in ranked:
                if len(keep) >= width or quota <= 0:
                    break
                if n.wp == top - lvl and id(n) not in used:
                    keep.append(n); used.add(id(n)); quota -= 1
        for n in ranked:
            if len(keep) >= width:
                break
            if id(n) not in used:
                keep.append(n); used.add(id(n))
        beam = keep
        for w in range(W):
            pool.conns[w].send(('keep', {n.ref[1] for n in beam if n.ref[0] == w}))
        for w in range(W):
            pool.conns[w].recv()
        if beam[0].score > best.score:
            best = beam[0]
            best_frames = frames
        elif frames - best_frames > stall_frames:
            return best, 'stall'
        if depth % 25 == 0:
            b = beam[0]
            log(f'depth {depth} wp {b.wp} area {b.info["area"]} x {b.info["x"]} y {b.info["y"]} hp {b.info["health"]} '
                f'cands {len(cand)} t={time.time() - t0:.0f}s')
        if time.time() - t0 > seconds:
            return best, 'time'
    return best, 'frames'
