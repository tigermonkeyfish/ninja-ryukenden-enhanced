#!/usr/bin/env python3
"""Picture check for the palette-lag fix (research probe): from the survey
traces (palette_lag.py records the whole VCE on frames where it changed),
per run and mapped mode, the frames whose VCE differs from the mode's
mode's colours of ORIGINAL's (mapped in gameplay, as they are in cinemas)'s VCE in the same frame (GB DMG / SMS: all 512 entries
through the table; APOCALYPSE (HELL): entries below HELL_MAPPED through the
table with the stage override, the rest as they are). NES-A/B and every mode
are also compared with a baseline trace folder by VCE hash.
usage: picture.py TRACES [BASELINE_TRACES]"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table, sms_table, hell_stage_table, load_hell  # noqa: E402

RUNS = ['1-1', '2-2', '3-1', '3-2', '4-1', '4-2', '5-2', '5-3', '5-4', '6-1', '6-3']
HELL_MAPPED = load_hell()['mapped_entries']
GB, SMS = gb_dmg_table(), sms_table()


def frames(trace):
    """The VCE words per frame, carried over frames without a change."""
    cur, out = None, []
    for t in trace:
        if 'vce_words' in t:
            b = bytes.fromhex(t['vce_words'])
            cur = [b[i] | b[i + 1] << 8 for i in range(0, 1024, 2)]
        out.append(cur)
    return out


def expected(mode, words, stage):
    if mode == 'apocalypse':
        table = hell_stage_table(stage)
        return [table[w & 0x1ff] if i < HELL_MAPPED else w for i, w in enumerate(words)]
    table = GB if mode == 'gbdmg' else SMS
    return [table[w & 0x1ff] for w in words]


def main():
    traces = Path(sys.argv[1])
    base = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    for run in RUNS:
        o = json.loads((traces / f'{run}.original.json').read_text())
        of = frames(o)
        for mode in ['apocalypse', 'sms', 'gbdmg']:
            p = traces / f'{run}.{mode}.json'
            if not p.exists():
                continue
            m = json.loads(p.read_text())
            mf = frames(m)
            bad = []
            for i, (ow, mw) in enumerate(zip(of, mf)):
                if ow is None or mw is None:
                    continue
                # cinemas, the title, the ending: original colours in every mode
                exp = ow if m[i]['master'] else expected(mode, ow, m[i]['stage'])
                n = sum(1 for a, b in zip(exp, mw) if (a & 0x1ff) != (b & 0x1ff))
                if n:
                    bad.append((i, n, o[i]['master']))
            line = f'{run} {mode:10s} frames {len(m)} not equal to ORIGINAL in the mode (mapped in gameplay, unmapped in cinemas): {len(bad)}'
            if bad:
                line += f' first {bad[:6]}'
            if base and (base / f'{run}.{mode}.json').exists():
                b = json.loads((base / f'{run}.{mode}.json').read_text())
                d = [i for i in range(min(len(b), len(m))) if b[i]['vce'] != m[i]['vce']]
                line += f' | VCE differs from baseline in {len(d)} frames'
            print(line)
        for mode in ['nes-a', 'nes-b', 'original']:
            p = traces / f'{run}.{mode}.json'
            if base and p.exists() and (base / p.name).exists():
                m = json.loads(p.read_text())
                b = json.loads((base / p.name).read_text())
                d = [i for i in range(min(len(b), len(m))) if b[i]['vce'] != m[i]['vce']]
                print(f'{run} {mode:10s} VCE differs from baseline in {len(d)} frames {d[:5]}')


if __name__ == '__main__':
    main()
