"""Job lines for runjobs.py: the dark-lift evidence on a build and on the
build before it (research reference, not a maintained tool).
usage: mkjobs.py SET WORK NEW.pce OLD.pce > jobs.txt
SET: starts   Level Select entries: SMS and HELL due for their tables
              (hell-1-1/stagestarts11.py), NES-A and NES-B hold their data
              (all-palettes/stagecheck.py); NEW only
     onscreen NES colours on screen in the 11 runs and every area of all 22
              entries (nes-palette/onscreen.py); NEW and OLD
     caps     the survey's captures in all six modes (cap.py); NEW only
     shots    the comparison pictures of 1-1, 2-2 and 5-3; NEW and OLD
     fades    fades.py on 4-1 and 6-2 in SMS and HELL (and Original); NEW and OLD
     trans    trans.py: every area exit of all 22 Level Select entries and
              the 11 stored runs in Original, GB DMG, HELL and SMS; NEW and OLD"""
import sys

kind, work, new, old = sys.argv[1:5]
T = 'research/tools'
D = f'{T}/dark-lift'
RUNS = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']
MODES = {'original': '0x00', 'nes-a': '0x08', 'nes-b': '0x28', 'gb-dmg': '0x10', 'hell': '0x18', 'sms': '0xb8'}
BUILDS = (('new', new), ('old', old))

if kind == 'starts':
    for mode in ('sms', 'hell'):
        for part, stages in (('a', '0,1,2,3,4,5,6,7,8,9,10'), ('b', '11,12,13,14,15,16,17,18,19,20,21')):
            print(f'starts-{mode}-{part}: {T}/hell-1-1/stagestarts11.py {new} {MODES[mode]} 120 {stages}')
    for mode in ('nes-a', 'nes-b'):
        for part, stages in (('a', '0,1,2,3,4,5,6,7,8,9,10'), ('b', '11,12,13,14,15,16,17,18,19,20,21')):
            print(f'stagecheck-{mode}-{part}: {T}/all-palettes/stagecheck.py {new} 150 {work}/starts/sc-{mode}-{part}.json '
                  f'{MODES[mode]} {stages}')
elif kind == 'onscreen':
    for tag, rom in BUILDS:
        for mode in ('nes-a', 'nes-b'):
            for part, runs in (('a', RUNS[:4]), ('b', RUNS[4:8]), ('c', RUNS[8:])):
                specs = ' '.join(f'run:{r}:900' for r in runs)
                print(f'onscreen-{tag}-{mode}-runs-{part}: {T}/nes-palette/onscreen.py {rom} {MODES[mode]} 30 '
                      f'{work}/onscreen/{tag}-{mode}-runs-{part}.json {specs}')
            for part, stages in (('a', range(0, 8)), ('b', range(8, 15)), ('c', range(15, 22))):
                specs = ' '.join(f'warp:{s}:180' for s in stages)
                print(f'onscreen-{tag}-{mode}-warp-{part}: {T}/nes-palette/onscreen.py {rom} {MODES[mode]} 30 '
                      f'{work}/onscreen/{tag}-{mode}-warp-{part}.json {specs}')
elif kind == 'caps':
    for mode in MODES:
        for name, args in (('4-1', 'run 4-1 250,700,1150,1450,1750'), ('5-1', 'warp 12'), ('6-2', 'warp 17'),
                           ('6-4A', 'boss 19 60,200,400,700'), ('6-4B', 'boss 20 60,200,400,700'),
                           ('6-4C', 'boss 21 60,200,400,700')):
            print(f'cap-{mode}-{name}: {D}/cap.py {new} {work}/cap {mode} {args}')
elif kind == 'shots':
    for tag, rom in BUILDS:
        for mode in ('sms', 'hell', 'nes-a', 'nes-b'):
            for name, frame in (('1-1', 600), ('2-2', 400), ('5-3', 3000)):
                print(f'shot-{tag}-{mode}-{name}: {D}/cap.py {rom} {work}/shots/{tag} {mode} run {name} {frame} scout')
elif kind == 'fades':
    for tag, rom in BUILDS:
        for mode in ('sms', 'hell') + (('original',) if tag == 'new' else ()):
            for case in ('load:8:60', 'run:4-1:2400:2547', 'load:17:60', 'warp:17:4:240'):
                print(f'fade-{tag}-{mode}-{case.replace(":", "-")}: {D}/fades.py {rom} {work}/fades {tag}-{mode} '
                      f'{MODES[mode]} {case}')
elif kind == 'trans':
    for tag, rom in BUILDS:
        for mode in ('original', 'gb-dmg', 'hell', 'sms'):
            for part, stages in (('a', range(0, 8)), ('b', range(8, 15)), ('c', range(15, 22))):
                cases = ' '.join(f'walk:{s}' for s in stages)
                print(f'trans-{tag}-{mode}-walk-{part}: {D}/trans.py {rom} {work}/trans {tag}-{mode} {MODES[mode]} {cases}')
            for part, runs in (('a', RUNS[:4]), ('b', RUNS[4:8]), ('c', RUNS[8:])):
                cases = ' '.join(f'run:{r}' for r in runs)
                print(f'trans-{tag}-{mode}-run-{part}: {D}/trans.py {rom} {work}/trans {tag}-{mode} {MODES[mode]} {cases}')
else:
    raise SystemExit(__doc__)
