"""Unit-test the vblank palette upload and palette_now in place with HELL's
per-stage override (research reference): research/tools/sms-palette/
unittest_upload.py's harness (every mode, the SMS build's layout) and model, each case also writing the visible
stage $2E5F (restored after the case) and the model taking
palette_tables.hell_stage_table(stage) in place of the global table. Random
palettes get colour $094 (the 1-1 key) and $194 (same low byte, high half:
not the key) at random entries so the compare is exercised (RAM colours with
bits above 8 are outside the model: its raw path writes the word, the VCE
keeps 9 bits); stages 0 (1-1, the override), 3 (2-2), 1 and
21. Edge cases run in 1-1 and in 2-2.
usage: unittest_override.py ROM [CASES] [SEED]
NO_OVERRIDE_MODEL=1: negative control (the model ignores the override)."""
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'sms-palette'))
import unittest_upload as ut  # noqa: E402
from palette_tables import hell_stage_table  # noqa: E402

TABLES = {s: hell_stage_table(s) for s in (0, 1, 3, 21)}
if os.environ.get('NO_OVERRIDE_MODEL'):
    TABLES[0] = TABLES[1]
base_run_case = ut.run_case


def run_case(g, case):
    stage = case['stage']
    old = g.read(0xe5f, 1)
    g.write(0xe5f, bytes([stage]))
    ut.HELL = TABLES[stage]
    try:
        return base_run_case(g, case)
    finally:
        g.write(0xe5f, old)


def seeded(rng, case):
    pal = list(case['pal'])
    for _ in range(rng.randint(0, 12)):
        pal[rng.randrange(512)] = rng.choice([0x094, 0x094, 0x194])
    return dict(case, pal=pal, stage=rng.choice([0, 0, 0, 3, 1, 21]))


def main():
    rom = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    cases = []
    for stage in (0, 3):
        for c in ut.edge_cases():
            pal = list(c['pal'])
            for i in (0x94, 18, 53, 181, 239, 240, 300):
                pal[i] = 0x094
            cases.append(dict(c, pal=pal, stage=stage))
    cases += [seeded(rng, ut.random_case(rng)) for _ in range(count)]
    ut.run_case = run_case
    failures = 0
    with ut.Session(rom, 0) as g:
        ut.cv.start_stage(g, 0)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.run_to('83F3', polls=20000)
        for i, case in enumerate(cases):
            errors = run_case(g, case)
            if errors:
                failures += 1
                print('case', i, 'stage', case['stage'], case['queue'], case.get('now'), 'opts', hex(case['opts']),
                      'master', case['master'], errors, flush=True)
    hits = sum(1 for c in cases if c['stage'] == 0 and c['master'] == 0 and ut.mode_due(c['opts']) == 0x18
               and 0x094 in [p & 0x1ff for p in c['pal'][:240]])
    print(f'{len(cases)} cases ({hits} HELL 1-1 cases with $094 below entry 240), {failures} failures'
          f'{" (negative control: model without the override)" if os.environ.get("NO_OVERRIDE_MODEL") else ""}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
