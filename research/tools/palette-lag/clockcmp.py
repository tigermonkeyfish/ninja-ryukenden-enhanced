#!/usr/bin/env python3
"""Clock comparison of instruction traces (palette_lag.py itrace output):
for two traces of the same window, whether every logged line (instruction
or interrupt) starts at the same master clock, and the first difference.
Bank $46 palette code may sit at other addresses in the two builds; only
the clocks and the line kinds (instruction mnemonic / interrupt) are
compared (the clocks; instructions that differ at equal clocks are
listed). usage: clockcmp.py A.gz B.gz [A2.gz B2.gz ...]"""
import gzip
import re
import sys

LINE = re.compile(r'^(\d+) @(\d+)\s.*?(?:[0-9A-F]{2}:[0-9A-F]{4}\s.*?S:\w\w\s+\S+\s+(\w+)|\[CPU\]\s+(IRQ)\s+(\S+))')


def lines(path):
    out = []
    with gzip.open(path, 'rt') as fh:
        for ln in fh:
            m = LINE.match(ln)
            if m:
                out.append((int(m[2]), m[3] or f'IRQ {m[5]}'))
    return out


args = sys.argv[1:]
for a, b in zip(args[::2], args[1::2]):
    la, lb = lines(a), lines(b)
    # Lines inside a run of differing instructions (a filler block reordered
    # at the same total length) are not compared; the line after it is.
    first = next((i for i, (x, y) in enumerate(zip(la, lb)) if x[0] != y[0]
                  and x[1] == y[1] and (i == 0 or la[i - 1][1] == lb[i - 1][1])), None)
    same = first is None and len(la) == len(lb)
    ops = sorted({(x[1], y[1]) for x, y in zip(la, lb) if x[1] != y[1]})
    irq_a = [c for c, k in la if k.startswith('IRQ')]
    irq_b = [c for c, k in lb if k.startswith('IRQ')]
    print(f'{a.split("/")[-1]:28s} lines {len(la)} / {len(lb)}: '
          + ('clock-identical' + (f' (other instructions at equal clocks: {ops})' if ops else '') if same else f'first difference at line {first}: {la[first] if first is not None and first < len(la) else None} vs {lb[first] if first is not None and first < len(lb) else None}')
          + f'; interrupts {len(irq_a)} / {len(irq_b)}, shifted {sum(x != y for x, y in zip(irq_a, irq_b))}, max {max([abs(x - y) for x, y in zip(irq_a, irq_b)] + [0])} clk')
