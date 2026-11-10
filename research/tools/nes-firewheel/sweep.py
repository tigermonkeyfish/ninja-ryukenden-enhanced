"""For each contact-damage event of the catalogue, grant the Fire Wheel OFFSET
updates earlier and replay on (a) 1.10 bit clear and (b) dev with $2100 bit 2.
Records: damage/knockback in the window, the first contact hit (ident) with
the wheel active, and whether the touching enemy was killed.
sweep.py V110 DEV CATALOG.json OUT.json [offsets...]"""
import json
import subprocess
import sys
from fw import *

v110, dev, cat, out = sys.argv[1:5]
offsets = [int(x) for x in sys.argv[5:]] or [30, 8, 2]
here = Path(__file__).parent
catalog = json.loads(Path(cat).read_text())
results = []


def trace(rom, name, flags, grant, n):
    path = OUT / f'sweep-tmp-{name}.json'
    p = subprocess.run([sys.executable, str(here / 'survey.py'), 'trace', rom, name, flags, str(grant), str(n), str(path)],
                       capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-800:])
    return json.loads(path.read_text())


def ident(rom, name, flags, grant, frame):
    p = subprocess.run([sys.executable, str(here / 'survey.py'), 'ident', rom, name, flags, str(grant), str(frame)],
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        return p.stderr[-300:]


only = __import__('os').environ.get('ONLY')
for name, evs in catalog.items():
    if only and name != only:
        continue
    for e in evs:
        d = e['f']
        if e['lives'][0] != e['lives'][1] or e['health'][1] == 0:
            continue
        for off in offsets:
            g = d - off
            n = d + 12
            row = {'run': name, 'event': d, 'grant': g, 'orig_hit': e.get('hit')}
            try:
                a = trace(v110, name, '0', g, n)
                b = trace(dev, name, '4', g, n)
            except RuntimeError as exc:
                row['error'] = str(exc)
                results.append(row)
                print(json.dumps(row), flush=True)
                continue
            win = range(g + 1, n)
            def dmg(log):
                return [s['f'] for p, s in zip(log, log[1:]) if s['f'] in win and s['health'] < p['health']]
            def hurt(log):
                return [s['f'] for s in log if s['f'] in win and s['kb'][-2:] == '09']
            row['v110_damage'] = dmg(a)
            row['v110_hurt_state'] = hurt(a)[:3]
            row['dev_damage'] = dmg(b)
            row['dev_hurt_state'] = hurt(b)[:3]
            row['same_until'] = next((x['f'] for x, y in zip(a, b) if x != y), None)
            if row['v110_damage']:
                f = row['v110_damage'][0]
                row['v110_hit'] = ident(v110, name, '0', g, f)
                row['dev_hit'] = ident(dev, name, '4', g, f)
                # the touching enemy: was it killed in the same update on dev?
                if isinstance(row['dev_hit'], list) and row['dev_hit']:
                    slot = row['dev_hit'][0]['slot']
                    after = next((s for s in b if s['f'] == f), None)
                    if after:
                        row['dev_slot_after'] = {'type': after['types'][2 * slot:2 * slot + 2],
                                                 'flags': after['enemy_t'][2 * slot:2 * slot + 2]}
            results.append(row)
            print(json.dumps(row), flush=True)
            if row.get('v110_damage'):
                break        # the shortest useful offset not needed once reproduced
Path(out).write_text(json.dumps(results, indent=1))
