"""Scenario runner (project harness: fresh session, shared start state,
Level Select entry, update 0 at the first gameplay update).

scen.py ROM FLAGS SCENARIO.json OUT.json
Scenario: {"stage": n, "updates": N, "run": optional stored run name (its
inputs), "hold": [buttons] default input, "events": [[update, action, arg], ...]}
actions: call <routine hex> (synthetic JSR from $8457), press [buttons]
(replaces the default from then on), poke [offset, [bytes]], timer2 (stage
timer to 002), screenshot <name>, mpr <rom offset> (count stops there and
record MPRs: breakpoint pass, not frame-exact afterwards).
Per-update samples include the effect slots, the wheel counter, art, freeze,
boss health and Ryu.
"""
import json
import sys
from fw import *

rom, flags, scen, out = sys.argv[1:5]
flags = None if flags == 'orig' else int(flags, 0)
sc = json.loads(Path(scen).read_text())
events = {}
for u, act, arg in sc.get('events', []):
    events.setdefault(u, []).append((act, arg))
inputs = frames_of(json.loads((RUNS / f"{sc['run']}.json").read_text())) if sc.get('run') else []
held = set(sc.get('hold', []))


def to_loop(game, u, mprs):
    """Continue to the gameplay loop head; record any other breakpoint stop."""
    while True:
        game.call('debug_continue')
        for _ in range(80000):
            st = game.call('debug_get_status')
            if st.get('paused'):
                break
        else:
            raise RuntimeError('not paused')
        if st['pc'] == '8457':
            return
        cpu = game.call('get_huc6280_status')
        mprs.append({'u': u, 'pc': st['pc'], 'mpr': [m['value'] for m in cpu['MPR']], 'S': cpu['S'], 'eda': game.read(0xeda, 1)[0]})


def run_once():
  """Steps by game update: run to the gameplay loop head ($8457) each time,
  so injections happen at exactly the same point in every build."""
  held = set(sc.get('hold', []))
  log, mprs = [], []
  with session('scen') as game:
    begin(game, rom, sc['stage'], flags)       # paused at $8457, update 0
    sp0 = int(game.call('get_huc6280_status')['S'], 16)
    game.write(0x104, bytes([0xA5]) * (0x100 + sp0 - 0x104 + 1))   # stack guard fill
    game.call('set_breakpoint', {'address': '2457', 'memory_area': 'rom', 'execute': True})
    for u in range(sc['updates']):
        for act, arg in events.get(u, []):
            if act == 'call':
                cpu = game.call('get_huc6280_status')
                saved = {k: int(cpu[k], 16) for k in ('A', 'X', 'Y', 'P', 'S')}
                sp = saved['S']
                game.write(0x100 + sp - 1, bytes([0x56, 0x84]))
                game.reg('S', sp - 2)
                game.reg('PC', int(arg, 16))
                to_loop(game, u, mprs)
                for k in ('A', 'X', 'Y', 'P'):
                    game.reg(k, saved[k])
            elif act == 'press':
                held = set(arg)
            elif act == 'poke':
                game.write(arg[0], bytes(arg[1]))
            elif act == 'timer2':
                game.write(0xedb, bytes([2, 0, 0]))
            elif act == 'mpr':
                for a in (arg if isinstance(arg, list) else [arg]):
                    game.call('set_breakpoint', {'address': a, 'memory_area': 'rom', 'execute': True})
        cur = inputs[u] if u < len(inputs) else held
        game.press(cur)
        to_loop(game, u, mprs)
        r = game.read(0, 0x2000)
        s = {'u': u, 'hp': r[0xead], 'lives': r[0xeaf], 'x': r[0xe9e] | r[0xe9f] << 8, 'y': r[0xea0],
             'state': r[0xeab], 'z36': r[0x36], 'z37': r[0x37], 'eff': r[0x110e:0x1113].hex(),
             'cnt': [r[0x1127 + i] | r[0x1136 + i] << 8 for i in range(5)], 'w317a': r[0x117a],
             'art': r[0x1158], 'freeze': r[0x1157], 'f3179': r[0x1179], 'boss': r[0x1035],
             'types': r[0xee0:0xef4].hex(), 'eflags': r[0xfbc:0xfd0].hex(), 'area': r[0xe60],
             'stage': r[0xe5f], 'master': r[0x240], 'score': r[0xed0:0xed6][::-1].hex(),
             'sprites': [], 'hit': r[0x1036:0x103a].hex(), 'tick': r[0xeda], 'timer': r[0xedb:0xede].hex(), 'items': r[0x10b7:0x10bf].hex(), 'ninpo': r[0x115a:0x115c].hex(), 'cont': r[0x1079:0x1089].hex()}
        for i in range(5):
            if r[0x110e + i] == 5:
                sp = r[0x1118 + i]
                s['sprites'].append([sp, r[0xd42 + sp], r[0xd82 + sp], r[0xb82 + sp]])
        s['ryu_frame'] = r[0xb82 + r[0xea3]]
        log.append(s)
        for act, arg in events.get(u, []):
            if act == 'screenshot':
                Path(OUT / f'{arg}.png').write_bytes(game.screenshot())
    page = game.read(0x104, 0x100 + sp0 - 0x104 + 1)
    low = min((0x2104 + i for i, b in enumerate(page) if b != 0xA5), default=None)
    log.append({'stack_low': None if low is None else f'${low:04x}'})
  return log, mprs


for attempt in range(4):
    try:
        log, mprs = run_once()
        break
    except StepError as exc:
        print('retry:', exc, flush=True)
else:
    raise SystemExit('injection kept mis-stepping')
Path(out).write_text(json.dumps({'log': log, 'mprs': mprs}))
print(Path(out).name, len(log), 'updates', len(mprs), 'breakpoint stops', 'attempts', attempt + 1)
