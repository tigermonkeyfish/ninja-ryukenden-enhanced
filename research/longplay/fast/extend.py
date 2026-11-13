#!/usr/bin/env python3
"""Extend research/longplay/full.json by one stage from a leg plan (fast core).

Emulator evidence only (in-process Geargrafx core, fastemu.py; the result is
checked with the headless emulator by scripts/longplay_check.py).
    extend.py PLAN.json [--dry]
PLAN: {"stage": "2-1", "legs": [leg, ...], "notes": "..."}; a leg is
  {"name": ..., "segments": [[n, [buttons]], ...]}            fixed input, or
  {"name": ..., "file": path, "frames": N}                     the first N frames of a run file, or
  {"name": ..., "beam": {"waypoints": [[x, y, r(, area, ry)], ...],
                         "goal": {"area": 2} | {"stage_change": true} | {"boss_dead": true} | {"x>=": .., "y<=": ..},
                         "width": 60, "chunk": 4, "max_frames": 2000, "seconds": 900, "ywt": 0.3, "actions": ...}}
Solved legs are cached in build/longplay/legs/STAGE.LEGNAME.json (keyed by the
input state's hash) so a plan can be re-run after changing a later leg. When
every leg is solved, the stage is played to its end, the game idles to the next
stage's first gameplay frame (stage byte changed, area 0, master 0) and
full.json gets the segments and a stage marker.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fastemu import Fast, BITS          # noqa: E402
import beam                              # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
FULL = ROOT / 'research/longplay/full.json'
ENTERED = Path('/workspace/build/longplay/states/entered.state')
LEGS = Path('/workspace/build/longplay/legs')
CACHE = Path('/workspace/build/longplay/states')


def goal_fn(g, i0, boss_seen):
    def goal(i, seen=False):
        if g.get('stage_change') and (i['stage'] != i0['stage'] or i['master'] != 0):
            return True
        if 'area' in g and i['area'] == g['area'] and i['stage'] == i0['stage']:
            return True
        if 'near' in g:
            x, y, r, ry = g['near']
            yy = i['y'] - 256 if i['y'] >= 224 else i['y']
            if abs(i['x'] - x) <= r and abs(yy - y) <= ry and i['area'] == g.get('in_area', i['area']) \
                    and i['state'] in (0, 1, 5):
                return True
        if g.get('boss_dead') and (boss_seen[0] or seen) and i['boss'] == 0:
            return True
        if 'x>=' in g or 'x<=' in g:
            ok = True
            for k, f in (('x>=', lambda v: i['x'] >= v), ('x<=', lambda v: i['x'] <= v),
                         ('y>=', lambda v: i['y'] >= v), ('y<=', lambda v: i['y'] <= v)):
                if k in g and not f(g[k]):
                    ok = False
            if g.get('ground') and i.get('state') not in (0, 1):
                ok = False
            return ok
        return False
    return goal


def replay_full(f, full):
    f.load(ENTERED)
    total = sum(n for n, _ in full['segments'])
    key = hashlib.sha1(json.dumps(full['segments']).encode()).hexdigest()[:16]
    cached = CACHE / f'full-{key}.state'
    if cached.exists():
        f.load(cached)
    else:
        f.play(full['segments'])
        f.press(0)
        for old in CACHE.glob('full-*.state'):
            old.unlink()
        cached.write_bytes(f.save())
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    ap.add_argument('--dry', action='store_true', help='solve legs, do not write full.json')
    ap.add_argument('--workers', type=int, default=7)
    ap.add_argument('--save-end', type=Path, help='save the state after the last leg here (diagnostics)')
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    stage = plan['stage']
    full = json.loads(FULL.read_text())
    if any(s['name'] == stage for s in full['stages']):
        sys.exit(f'{stage} is already in full.json')
    f = Fast()
    total0 = replay_full(f, full)
    LEGS.mkdir(parents=True, exist_ok=True)
    i0 = f.info()
    print('stage start', total0, i0, flush=True)
    segs, notes = [], []
    boss_seen = [False]
    for leg in plan['legs']:
        st = f.save()
        h = hashlib.sha1(st[:-188]).hexdigest()[:16]   # the state header (time stamp) excluded
        cfile = LEGS / f'{stage}.{leg["name"]}.json'
        legsegs = None
        if 'segments' in leg:
            legsegs = leg['segments']
        elif 'file' in leg:
            src = json.loads((ROOT / leg['file']).read_text())['segments']
            legsegs, t = [], 0
            for n, b in src:
                if t >= leg['frames']:
                    break
                n = min(n, leg['frames'] - t)
                legsegs.append([n, b]); t += n
        else:
            if cfile.exists():
                c = json.loads(cfile.read_text())
                budget = ('max_frames', 'seconds', 'width', 'stall_frames', 'ywt')
                same = lambda a, b: {k: v for k, v in a.items() if k not in budget} == \
                    {k: v for k, v in b.items() if k not in budget}
                if c['state'] == h and same(c['spec'], leg['beam']):
                    legsegs = c['segments']
            if legsegs is None:
                b = dict(leg['beam'])
                if 'follow' in b:
                    fl = b.pop('follow')
                    path = json.loads((ROOT / fl['path']).read_text())['path']
                    import stagemap
                    rects = {a: ar['rects'] for a, ar in enumerate(stagemap.decode(
                        stagemap.load(), stagemap.NAMES.index(stage)))}
                    lo, hi = fl.get('from_frame', 0), fl.get('to_frame', 10 ** 9)
                    pts, last, pfr = [], None, []
                    for fr, area, x, y, hp, stg, *mo in path:
                        if not lo <= fr <= hi or any(a <= fr <= b for a, b in fl.get('skip_frames', [])):
                            continue
                        if any(q[0] < fr <= q[0] + 8 or q[0] == fr for q in path if q[1] != area and q[0] < fr and fr - q[0] <= 8):
                            continue          # stale coordinates right after an area change
                        if mo and mo[0] in (3, 6, 8, 9) and fl.get('skip_air', True):
                            # air, slash and hurt positions make poor waypoints, except
                            # where the bot touched a platform top in a hop (it did not
                            # stand, but the beam must land there)
                            tops = [r for r in rects.get(area, []) if r[0] in (0, 1)
                                    and r[1] <= x <= r[3] and r[2] - 1 <= y <= r[2] + 2]
                            if not tops or (last and fr - last[0] < 16):
                                continue
                            pts.append([x, tops[0][2], fl.get('r', 16), area, 4, 1])
                            pfr.append(fr)
                            last = (fr, area)
                            continue
                        if last is None or fr - last[0] >= fl.get('every', 40) or area != last[1]:
                            if mo and mo[0] in (0, 1, 2) and fl.get('skip_air', True):
                                # standing points: Ryu must stand there (a jump apex
                                # 6 px under a ledge is not on it)
                                pts.append([x, y, fl.get('r', 16), area, fl.get('ry_ground', 8), 1])
                            else:
                                pts.append([x, y, fl.get('r', 16), area, fl.get('ry', 24)])
                            pfr.append(fr)
                            last = (fr, area)
                    # hand waypoints [frame, x, y, r, ry] slotted in by path frame
                    for fr_, x_, y_, r_, ry_, *g_ in fl.get('add_points', []):
                        k = sum(1 for q in pfr if q <= fr_)
                        pts.insert(k, [x_, y_, r_, pts[0][3] if pts else None, ry_] + g_)
                        pfr.insert(k, fr_)
                    span = [r for r in path if lo <= r[0] <= hi]
                    if span:      # the span's last point (the way out), even in the air
                        pts.append([span[-1][2], span[-1][3], 6, span[-1][1], 6])
                    b['waypoints'] = pts + b.get('waypoints', [])
                wps = [tuple(w) for w in b.pop('waypoints')]
                g = goal_fn(b.pop('goal'), f.info(), boss_seen)
                bw = b.pop('boss_weight', 0)
                chase = b.pop('chase', 0)     # pull toward the boss's x ($2F1C, 2-3)
                if bw:
                    b['prefer'] = lambda i, bw=bw, c=chase: (-bw * i['boss'] - c * abs(i['x'] - i['bx'])
                                                             if i['boss'] and i['bx'] else 0)
                acts = b.pop('actions', None)
                if acts:
                    b['actions'] = [sum(BITS[k] for k in x) if isinstance(x, list) else x for x in acts]
                print(f'leg {leg["name"]}: beam from {f.info()}', flush=True)
                t0 = time.time()
                with beam.Pool(a.workers) as pool:
                    node, why = beam.search(pool, st, wps, g, log=lambda s: print('  ', s, flush=True), **b)
                if why != 'goal':
                    out = LEGS / f'{stage}.{leg["name"]}.failed.json'
                    out.write_text(json.dumps({'segments': segs + node.segments(), 'best': node.info, 'why': why}))
                    print(f'leg {leg["name"]} NOT solved ({why}); best {node.info} wp {node.wp}; route so far in {out}',
                          flush=True)
                    return 1
                legsegs = node.segments()
                cfile.write_text(json.dumps({'state': h, 'spec': leg['beam'], 'segments': legsegs,
                                             'seconds': round(time.time() - t0)}))
        f.load(st)
        for n, bt in legsegs:
            for _ in range(n):
                f.step(1, bt)
                if f.info()['boss'] > 0:
                    boss_seen[0] = True
        segs.extend(legsegs)
        i = f.info()
        notes.append(f'{leg["name"]}: {sum(n for n, _ in legsegs)} frames -> area {i["area"]} x {i["x"]} y {i["y"]} hp {i["health"]}')
        print(notes[-1], flush=True)
    end = f.info()
    if a.save_end:
        a.save_end.write_bytes(f.save())
    if a.dry:
        print('dry run: not written', flush=True)
        return 0
    f.press(0)
    idle = 0
    while idle < 20000:
        f.step(1, 0)
        idle += 1
        i = f.info()
        if i['master'] == 0 and i['stage'] != i0['stage'] and i['area'] == 0:
            break
    else:
        sys.exit('next stage not reached while idling')
    print('idle', idle, f.info(), flush=True)
    stage_frames = sum(n for n, _ in segs)
    full['segments'] = full['segments'] + segs + [[idle, []]]
    full['frames'] = sum(n for n, _ in full['segments'])
    full['tail'] = {'stage': i['stage'], 'area': 0, 'master': 0}
    full['stages'].append({'name': stage, 'start_frame': total0, 'finished': True,
                           'end_frame': total0 + stage_frames, 'idle_after': idle,
                           'health_end': end['health'], 'lives_end': end['lives']})
    full.setdefault('notes', {})[stage] = plan.get('notes', '') + ' Legs: ' + '; '.join(notes)
    FULL.write_text(json.dumps(full, separators=(',', ':')) + '\n')
    print('wrote', FULL, full['frames'], flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
