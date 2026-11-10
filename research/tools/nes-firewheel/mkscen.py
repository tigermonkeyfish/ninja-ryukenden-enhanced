import json
import os
from pathlib import Path

D = Path(os.environ.get('NFW_WORK', 'build/nes-firewheel')).resolve() / 'sc'
S = {
    'restart': {'stage': 0, 'updates': 800, 'events': [[30, 'call', 'a6a6'], [230, 'call', 'a6a6']]},
    'projectile': {'stage': 0, 'updates': 60, 'events': [[10, 'call', 'a6ae'], [12, 'call', 'a673'], [14, 'call', 'a673'],
                                                        [20, 'press', ['up', 'II']], [23, 'press', []], [26, 'call', 'a6a6']]},
    'freeze': {'stage': 0, 'updates': 120, 'events': [[20, 'call', 'a67d'], [40, 'call', 'a6a6']]},
    'artend': {'stage': 0, 'updates': 140, 'events': [[30, 'call', 'a6a6'], [100, 'call', 'a6b8']]},
    'freezeend': {'stage': 0, 'updates': 140, 'events': [[30, 'call', 'a6a6'], [100, 'call', 'a67d']]},
    'death': {'stage': 0, 'updates': 260, 'events': [[30, 'call', 'a6a6'], [40, 'timer2', None]]},
    'throw': {'stage': 0, 'updates': 130, 'events': [[10, 'call', 'a6ae'], [12, 'call', 'a673'], [30, 'call', 'a6a6'],
                                                   [100, 'press', ['up', 'II']], [103, 'press', []]]},
    'endwheel': {'stage': 19, 'updates': 700, 'hold': ['right'], 'events': [[30, 'call', 'a6a6']]},
    'boss12': {'stage': 1, 'updates': 500, 'hold': ['right'], 'events': [[30, 'call', 'a6a6']]},
    'dur11': {'stage': 0, 'updates': 760, 'events': [[30, 'call', 'a6a6']]},
    'walk11': {'stage': 0, 'updates': 700, 'hold': ['right'], 'events': [[5, 'call', 'a6a6']]},
    'mprs': {'stage': 1, 'updates': 260, 'hold': ['right'], 'events': [
        [0, 'mpr', ['2f70', '7c00', '4a8a', '4211', '4f2d', '46ab', '46b5', '46bf', '46c9', '46d3', '4682']],
        [10, 'call', 'a6ae'], [12, 'call', 'a673'], [14, 'call', 'a673'], [20, 'press', ['up', 'II']], [23, 'press', ['right']],
        [26, 'call', 'a67d'], [40, 'call', 'a6a6'], [150, 'call', 'a6a6'], [200, 'call', 'a6c2'], [210, 'call', 'a6a6'],
        [230, 'call', 'a67d']]},
}
for k, v in S.items():
    (D / f'{k}.json').write_text(json.dumps(v))
print(' '.join(S))
