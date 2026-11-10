import json
import os
from pathlib import Path

D = Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve() / 'sc'


def load(n, t):
    return [s for s in json.loads((D / f'{n}-{t}.json').read_text())['log'] if 'u' in s]


def wheels(s):
    return [i for i in range(5) if s['eff'][2 * i:2 * i + 2] == '05']


def types(s):
    return [s['eff'][2 * i:2 * i + 2] for i in range(5)]


for t in ('on', 'off'):
    print('=====', t)
    L = load('dur11', t)
    w = [s for s in L if wheels(s)]
    print('dur11: wheel sampled', len(w), 'updates', w[0]['u'], '-', w[-1]['u'], 'hidden', sum(1 for s in w if s['sprites'] and s['sprites'][0][2] == 1))
    L = load('boss12', t)
    ch = [(b['u'], b['boss']) for a, b in zip(L, L[1:]) if a['boss'] != b['boss']]
    print('boss12: boss hp changes', ch[:3], '...', ch[-1:], 'count', len(ch), 'ryu hp end', L[-1]['hp'])
    L = load('restart', t)
    print('restart: wheel slots u=229/231', wheels(L[229]), wheels(L[231]), 'cnt', [L[229]['cnt'][i] for i in wheels(L[229])], [L[231]['cnt'][i] for i in wheels(L[231])],
          'last wheel update', max(s['u'] for s in L if wheels(s)))
    L = load('projectile', t)
    print('projectile: types u=22..27', [types(s) for s in L[22:28:1]], 'art', L[25]['art'], L[27]['art'])
    L = load('freeze', t)
    print('freeze: u=39/41 freeze', L[39]['freeze'], L[41]['freeze'], 'types', types(L[39]), types(L[41]), 'end freeze', L[-1]['freeze'])
    L = load('artend', t)
    print('artend: u=99/101 wheels', wheels(L[99]), wheels(L[101]), 'art', L[99]['art'], L[101]['art'])
    L = load('freezeend', t)
    print('freezeend: u=99/101 wheels', wheels(L[99]), wheels(L[101]), 'freeze', L[101]['freeze'])
    L = load('death', t)
    d = next(s['u'] for s in L if s['hp'] == 0)
    gone = next(s['u'] for s in L if s['u'] > 30 and not wheels(s))
    print('death: hp 0 at', d, 'wheel gone at', gone, 'lives', L[0]['lives'], L[-1]['lives'])
    L = load('throw', t)
    print('throw: ryu frames u=99..106', [s['ryu_frame'] for s in L[99:107]], 'types', [types(s) for s in L[100:104]], 'art', L[99]['art'])
