"""Build-time steps that generate a module's data.

A module may name a prepare step in src/modules.json; the backdrop steps
regenerate its data from the original ROM (scripts/native_backdrops.py), so
no game data is stored here and nothing is read from an earlier release.
"""


def native(module):
    def step(work, original):
        from native_backdrops import prepare as regenerate
        regenerate(module, work, original)
    return step


# Backdrops regenerated from the original ROM (scripts/native_backdrops.py).
PREPARE = {'native-' + module: native(module) for module in (
    'stage11', 'stage22', 'stage31', 'stage32', 'stage41', 'stage42', 'stage52', 'stage63',
    'castle', 'stage61-mountains', 'stage61-sky')}


def prepare(name, work, original):
    if name not in PREPARE:
        raise ValueError(f'Unknown module prepare step: {name}')
    PREPARE[name](work, original)
