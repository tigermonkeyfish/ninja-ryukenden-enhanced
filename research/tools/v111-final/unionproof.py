#!/usr/bin/env python3
"""Show that a merged ROM is the byte union of its two parents.

usage: unionproof.py BASE PARENT_A PARENT_B MERGED

BASE is the build both parents descend from. With A = bytes where PARENT_A
differs from BASE and B = bytes where PARENT_B differs from BASE, the merge
is a union when: A and B do not overlap; MERGED differs from PARENT_A
exactly on B and holds PARENT_B's bytes there; MERGED differs from PARENT_B
exactly on A and holds PARENT_A's bytes there; and elsewhere all four agree.
Prints the ranges (file offsets of the 1 MiB headerless image; bank and CPU
address for a bank mapped at $4000). Exit status 0 only if all of it holds.
"""
import json
import sys
from pathlib import Path

MODULES = json.loads((Path(__file__).resolve().parents[3] / 'src' / 'modules.json').read_text())
MODULES = MODULES['modules'] if isinstance(MODULES, dict) else MODULES


def owners(offsets):
    """Bytes per module (src/modules.json ranges); 'none' for bytes outside every range."""
    count = {}
    for i in offsets:
        name = next((m['name'] for m in MODULES for lo, hi in m.get('ranges', []) if lo <= i < hi), 'none')
        count[name] = count.get(name, 0) + 1
    return ', '.join(f'{k} {v}' for k, v in sorted(count.items()))


def diff(a, b):
    return {i for i in range(len(a)) if a[i] != b[i]}


def ranges(offsets, gap=1):
    out = []
    for i in sorted(offsets):
        if out and i - out[-1][1] <= gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def show(title, offsets):
    print(f'{title}: {len(offsets)} bytes in {len(ranges(offsets))} runs; by module: {owners(offsets)}')
    for lo, hi in ranges(offsets, gap=16):      # listed with gaps under 16 bytes joined
        n = sum(1 for i in offsets if lo <= i <= hi)
        print(f'  {lo:06x}-{hi:06x}  bank ${lo >> 13:02x} ${0x4000 + (lo & 0x1fff):04x}-${0x4000 + (hi & 0x1fff):04x}'
              f'  {n} of {hi - lo + 1} bytes differ')


def main():
    base, pa, pb, merged = (Path(p).read_bytes() for p in sys.argv[1:5])
    assert len(base) == len(pa) == len(pb) == len(merged), 'sizes differ'
    a, b = diff(base, pa), diff(base, pb)
    ma, mb = diff(merged, pa), diff(merged, pb)
    show('A = base vs parent A', a)
    show('B = base vs parent B', b)
    show('merged vs parent A', ma)
    show('merged vs parent B', mb)
    checks = {
        'A and B do not overlap': not a & b,
        'merged differs from parent A exactly on B': ma == b,
        'merged differs from parent B exactly on A': mb == a,
        'merged holds parent B bytes on B': all(merged[i] == pb[i] for i in b),
        'merged holds parent A bytes on A': all(merged[i] == pa[i] for i in a),
        'merged equals base everywhere else': diff(merged, base) == a | b,
    }
    for name, ok in checks.items():
        print(f'{"PASS" if ok else "FAIL"}  {name}')
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == '__main__':
    main()
