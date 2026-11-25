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


def palette_tables(work, original):
    from palette_tables import generate
    generate(work)


# Palette-mode colour tables from editable parameters (scripts/palette_tables.py).
PREPARE['palette-tables'] = palette_tables


def nes_palette(work, original):
    from nes_palette import generate
    generate(work, original)


def nes_enhanced(module):
    def step(work, original):
        from nes_palette import enhanced
        enhanced(module, work, original)
    return step


# NES palette mode: the colour sets and their tables from src/nes-palette
# (scripts/nes_palette.py), and the NES versions of the 1-1 and 2-2 merged
# palettes, traced through the original backdrops.
PREPARE['nes-palette'] = nes_palette
PREPARE.update({'nes-enhanced-' + module: nes_enhanced(module) for module in ('stage11', 'stage22')})


def prepare(name, work, original):
    """Run a module's prepare step; `a+b` runs a, then b."""
    for part in name.split('+'):
        if part not in PREPARE:
            raise ValueError(f'Unknown module prepare step: {part}')
    for part in name.split('+'):
        PREPARE[part](work, original)
