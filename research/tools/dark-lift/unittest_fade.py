"""Unit-test the vblank palette upload in place with the fade rule (research
reference, not a maintained tool): hell-1-1/unittest_override.py's harness
and model (every mode, the visible stage written per case), each case also
writing the native fade's level $2A8A (restored after the case), and the
model giving a left-over entry FADE_CAP (136) colours instead of 16
when that byte's bit 7 is set (a fade-out has ended on black). Levels: 8
(after a fade-in), 0-7 (a fade under way) and $FF; edge cases run with 8 and
with $FF, in 1-1 and in 2-2.
usage: unittest_fade.py ROM [CASES] [SEED]
NO_FADE_MODEL=1: negative control (the model keeps 16 colours whatever the level)."""
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'hell-1-1'))
import unittest_override as uo  # noqa: E402

ut = uo.ut
FADE_CAP = 136
NO_FADE = bool(os.environ.get('NO_FADE_MODEL'))
stage_run_case = uo.run_case


def run_case(g, case):
    level = case['level']
    old = g.read(0xa8a, 1)
    g.write(0xa8a, bytes([level]))
    ut.LEFTOVER_CAP = FADE_CAP if level & 0x80 and not NO_FADE else 16
    try:
        return stage_run_case(g, case)
    finally:
        ut.LEFTOVER_CAP = 16
        g.write(0xa8a, old)


def main():
    rom = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    cases = []
    for stage in (0, 3):
        for level in (8, 0xff):
            for c in ut.edge_cases():
                pal = list(c['pal'])
                for i in (0x94, 18, 53, 181, 239, 240, 300):
                    pal[i] = 0x094
                cases.append(dict(c, pal=pal, stage=stage, level=level))
    for _ in range(count):
        c = uo.seeded(rng, ut.random_case(rng))
        if rng.random() < 0.5:          # more left-over entries than random_case makes
            idx = rng.randrange(512)
            c['queue'] = [(idx, rng.randint(1, 512))]
            c['st'] = rng.choice([0xa0, 0xa0, 0xa0, 0xe0])
            c['pc'] = rng.choice([0xfd69, 0xfd69, 0xfd6d, 0xfd6f, 0xfd70, 0x8457])
        cases.append(dict(c, level=rng.choice([8, 8, 0, 3, 7, 0xff, 0xff, 0xff])))
    failures = 0
    with ut.Session(rom, 0) as g:
        ut.cv.start_stage(g, 0)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.run_to('83F3', polls=20000)
        for i, case in enumerate(cases):
            errors = run_case(g, case)
            if errors:
                failures += 1
                print('case', i, 'stage', case['stage'], 'level', hex(case['level']), case['queue'], case.get('now'),
                      'opts', hex(case['opts']), 'st', hex(case['st']), 'master', case['master'],
                      'pc', hex(case.get('pc', 0xfd69)), errors, flush=True)
    boosted = sum(1 for c in cases if c['level'] & 0x80 and c['master'] == 0 and 'now' not in c and not c['lock']
                  and ut.mode_due(c['opts']) and len(c['queue']) == 1 and c['st'] & 0x20 and c['st'] & 0x80
                  and not c['st'] & 0x40 and 0xfd67 <= c.get('pc', 0xfd69) <= 0xfd6f)
    print(f'{len(cases)} cases ({boosted} with a left-over entry at the fade cap), {failures} failures'
          f'{" (negative control: model without the fade rule)" if NO_FADE else ""}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
