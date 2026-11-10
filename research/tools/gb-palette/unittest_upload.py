"""Unit-test the vblank palette upload in place (docs/pc-engine/EMULATOR.md,
"Unit-test a small routine in place"), against an independent Python model.

From the 1-1 main-loop hook ($83F3), each case writes a RAM palette ($2286),
a border colour, the queue ($2260-$2280), the lock, the options byte and
$2240, fills the VCE with a sentinel and the borrowed zero page $20-$25 with
known bytes, then calls the fixed-bank trampoline by a synthetic JSR and runs
back to the hook: the vblank entry ($FEC0) with the I flag set, as in the
interrupt, and the stage modules' palette_now ($FEBE, X = first colour, Y =
count) with I clear, as from a renderer. Checked: every VCE word, the queue,
the lock, S, MPR2 and zero page $20-$26; for the vblank entry also X and Y.
usage: unittest_upload.py ROM [CASES] [SEED]"""
import os
import random
import sys

from gbtools import Session, cv, vce_words
sys.path.insert(0, str(cv.Path(__file__).resolve().parents[3] / 'scripts'))
from palette_tables import gb_dmg_table  # noqa: E402

GB = gb_dmg_table()
# MODEL_CAP set to a wrong value is the negative control: cases must fail.
CAP = int(os.environ.get('MODEL_CAP', 168))
ENTRY_COST = int(os.environ.get('MODEL_ENTRY_COST', 6))
LEFTOVER_CAP = 32
NATIVE_PLUS = 0
BUDGET_MIN = 16
SENTINEL = 0x1ff ^ 0x0aa


def model(case):
    """(VCE words, queue entries, options byte) the upload should leave."""
    vce = [SENTINEL] * 512
    pal, queue, opts = case['pal'], [list(e) for e in case['queue']], case['opts']
    mapped = (opts & 0x18) == 0x10 and case['master'] == 0
    if 'now' in case:
        first, count = case['now']
        for i in range(first, first + count):
            vce[i] = GB[pal[i] & 0x1ff] if mapped else pal[i]
        return vce, queue, opts
    if case['lock']:
        return vce, queue, opts
    # $2100 bit 7: the VCE holds mapped colours. A mismatch re-queues all.
    if bool(opts & 0x80) != mapped:
        opts ^= 0x80
        queue = [[0, 512]]
        if mapped:
            opts &= ~0x20
    if not queue:
        if mapped:
            opts &= ~0x20
        return vce, queue, opts
    full = mapped and len(queue) >= 8
    f = (lambda c: GB[c & 0x1ff]) if mapped else (lambda c: c & 0xffff)
    budget = CAP - ENTRY_COST * (min(len(queue), 8) - 1) if mapped else 1 << 30
    if mapped:
        # Bit 6: the main loop was busy (interrupted PC outside $FD67-$FD6F) at
        # the last vblank with work. Bit 5: a single left-over entry waits if it
        # is busy now or was then, else gets LEFTOVER_CAP colours.
        busy = not 0xfd67 <= case.get('pc', 0xfd69) <= 0xfd6f
        was_busy = bool(opts & 0x40)
        opts = (opts & ~0x40) | (0x40 if busy else 0)
        if len(queue) == 1 and opts & 0x20:
            if busy or was_busy:
                return vce, queue, opts
            budget = LEFTOVER_CAP
            opts &= ~0x20
        else:
            new = queue[1:] if opts & 0x20 else queue
            total = sum(2 * n for _, n in new)
            b = min((total >> 3) + (total >> 7) + NATIVE_PLUS, 255) if total < 2048 else 255
            b = min(b, CAP) - ENTRY_COST * (len(queue) - 1)
            budget = max(b, BUDGET_MIN)
            opts &= ~0x20
    kept = []
    for idx, n in queue:
        k = min(n, budget)
        for i in range(idx, idx + k):
            vce[i & 0x1ff] = f(pal[i & 0x1ff]) & 0x1ff if mapped else pal[i]
        budget -= k
        if n - k:
            kept.append([(idx + k) & 0x1ff, n - k])
    if kept:
        # One entry from where the upload stopped, running on (past 511 to 0)
        # far enough to cover the rest, at most 512 colours.
        s = kept[0][0]
        kept = [[s, max(min(512, ((a - s) & 0x1ff) + n) for a, n in kept)]]
    if full:
        kept = [[0, 512]]           # a full queue may have dropped an entry
    vce[256] = f(case['border'])
    if not mapped:
        kept = []
    elif kept:
        opts |= 0x20
    return vce, kept, opts


def random_case(rng):
    pal = [rng.randrange(0x200) for _ in range(512)]
    queue = []
    for _ in range(rng.choice([1, 1, 2, 3, 4, 8])):
        kind = rng.random()
        if kind < 0.2:
            idx, n = 0, 512
        elif kind < 0.5:
            idx = rng.randrange(32) * 16
            n = 16 * rng.randint(1, (512 - idx) // 16)
        else:
            idx = rng.randrange(512)
            n = rng.randint(1, 512 - idx)
        queue.append((idx, n))
    return {'pal': pal, 'queue': queue, 'border': rng.randrange(0x200), 'lock': 0,
            'opts': rng.choice([0x90, 0x90, 0x90, 0x10, 0x00, 0x80, 0xb0, 0xf0, 0xd0, 0x30]),
            'master': rng.choice([0, 0, 0, 1]), 'pc': rng.choice([0xfd69, 0xfd6b, 0xfd6d, 0xfd6f, 0xfd70, 0x4f52, 0xfd66])}


def edge_cases():
    pal = list(range(512))
    base = {'pal': pal, 'border': 0x123, 'lock': 0, 'opts': 0x90, 'master': 0}
    cases = []
    for q in ([(0, 512)], [(0, 192)], [(0, 191)], [(0, 193)], [(100, 128)], [(383, 129)],
              [(511, 1)], [(0, 128), (128, 64), (300, 10)], [(0, 256)] + [(241 + i, 1) for i in range(7)],
              [(256, 16), (272, 16), (288, 16)], [(500, 12), (0, 200), (16, 16)],
              [(368, 16), (384, 16), (320, 16), (400, 16), (304, 16), (352, 16), (416, 16), (432, 16)]):
        cases.append(dict(base, queue=q))
    cases.append(dict(base, queue=[], border=0x1ff))
    cases.append(dict(base, queue=[(0, 512)], lock=1))
    cases.append(dict(base, queue=[(0, 512)], lock=1, opts=0x10))
    cases.append(dict(base, queue=[(0, 512)], lock=1, opts=0x80))
    for opts in (0x00, 0x08, 0x18, 0x07, 0x67, 0x80, 0x88, 0x98, 0x10, 0x90):
        cases.append(dict(base, queue=[(0, 512), (16, 16)], opts=opts))
        cases.append(dict(base, queue=[], opts=opts))
    # Left-over entries: busy or idle main loop, first vblank or later.
    for opts in (0xb0, 0xf0, 0xd0, 0x90):
        for pc in (0xfd69, 0xfd6d, 0xfd6f, 0xfd70, 0xfd66, 0x8457):
            cases.append(dict(base, queue=[(176, 336)], opts=opts, pc=pc))
        cases.append(dict(base, queue=[(176, 336), (16, 16)], opts=opts, pc=0x8457))
        cases.append(dict(base, queue=[(480, 64)], opts=opts))              # wraps to colour 0
        cases.append(dict(base, queue=[(300, 512), (0, 512)], opts=opts))
        cases.append(dict(base, queue=[(480, 32), (96, 18)], opts=opts))
    for master in (1, 2):
        for opts in (0x10, 0x90):
            cases.append(dict(base, queue=[(0, 300), (400, 50)], master=master, opts=opts))
    rng = random.Random(7)
    for opts, master in ((0x90, 0), (0x00, 0), (0x08, 0), (0x18, 0), (0x10, 1)):
        for first, count in ((16, 16), (208, 32), (0, 1), (255, 1), (128, 127), (200, 56)):
            pal = [rng.randrange(0x200) for _ in range(512)]
            cases.append(dict(base, pal=pal, queue=[], opts=opts, master=master,
                              now=(first, count)))
    return cases


def run_case(g, case):
    ram = bytearray(g.read(0, 0x2000))
    for i, c in enumerate(case['pal']):
        ram[0x286 + 2 * i], ram[0x287 + 2 * i] = c & 0xff, c >> 8
    g.write(0x286, bytes(ram[0x286:0x686]))
    q = bytearray(33)
    q[0] = len(case['queue'])
    for k, (idx, n) in enumerate(case['queue']):
        q[1 + k], q[9 + k] = (2 * n) & 0xff, (2 * n) >> 8
        q[17 + k], q[25 + k] = idx & 0xff, idx >> 8
    g.write(0x260, bytes(q))
    g.write(0x281, bytes([case['border'] & 0xff, case['border'] >> 8, case['lock']]))
    g.write(0x100, bytes([case['opts']]))
    g.write(0x240, bytes([case['master']]))
    g.write(0x020, bytes([0x5a, 0xa5, 0x11, 0x22, 0x33, 0x44, 0x55]))
    g.call('write_memory', {'area': 8, 'offset': '0000',
                            'bytes': bytes([SENTINEL & 0xff, SENTINEL >> 8] * 512).hex(' ')})
    cpu = g.call('get_huc6280_status')
    assert cpu['PC'] == '83F3', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    mpr2 = cpu['MPR'][2]['value']
    sp = saved['S']
    g.write(0x100 + sp - 1, bytes([0xf2, 0x83]))
    g.reg('S', sp - 2)
    # The interrupt frame the vblank entry finds above the return address:
    # Y, X, A, P, then the interrupted PC (live main-loop stack, restored below).
    live = g.read(0x100 + sp + 1, 6)
    pc = case.get('pc', 0xfd69)
    g.write(0x100 + sp + 1, bytes([0, 0, 0, 0, pc & 0xff, pc >> 8]))
    if 'now' in case:
        g.reg('X', case['now'][0])
        g.reg('Y', case['now'][1])
        g.reg('P', saved['P'] & ~0x04)     # I clear, as from a renderer
        g.reg('PC', 0xfebe)
    else:
        g.reg('X', 0x37)
        g.reg('Y', 0x73)
        g.reg('P', saved['P'] | 0x04)      # I set, as in the interrupt
        g.reg('PC', 0xfec0)
    g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    g.run_to('83F3', polls=20000)
    after = g.call('get_huc6280_status')
    g.write(0x100 + sp + 1, live)
    regs = (after['X'], after['Y'], int(after['S'], 16), after['MPR'][2]['value'])
    g.reg('X', saved['X'])
    g.reg('Y', saved['Y'])
    g.reg('P', saved['P'])
    vce = vce_words(g.read(0, 1024, area=8))
    r = g.read(0, 0x300)
    errors = []
    n = r[0x260]
    queue = [[r[0x271 + k] | r[0x279 + k] << 8, (r[0x261 + k] | r[0x269 + k] << 8) // 2] for k in range(min(n, 8))]
    zp = r[0x20:0x27]
    want_vce, want_queue, want_opts = model(case)
    if r[0x100] != want_opts:
        errors.append(f'options {r[0x100]:#04x} want {want_opts:#04x}')
    bad = [i for i in range(512) if vce[i] != want_vce[i]]
    if bad:
        errors.append(f'VCE differs at {len(bad)} entries, first {bad[:5]} got {[hex(vce[i]) for i in bad[:5]]} want {[hex(want_vce[i]) for i in bad[:5]]}')
    if queue != want_queue:
        errors.append(f'queue {queue} want {want_queue}')
    if 'now' in case:
        regs = ('37', '73') + regs[2:]
    if regs != ('37', '73', sp, mpr2):
        errors.append(f'registers X Y S MPR2 {regs} want 37 73 {sp} {mpr2}')
    if r[0x283] != case['lock']:
        errors.append(f'lock {r[0x283]}')
    if zp != bytes([0x5a, 0xa5, 0x11, 0x22, 0x33, 0x44, 0x55]):
        errors.append(f'zero page $20-$26 {zp.hex()}')
    return errors


def main():
    rom = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    cases = edge_cases() + [random_case(rng) for _ in range(count)]
    failures = 0
    with Session(rom, 0) as g:
        cv.start_stage(g, 0)
        g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
        g.run_to('83F3', polls=20000)
        for i, case in enumerate(cases):
            errors = run_case(g, case)
            if errors:
                failures += 1
                print('case', i, case['queue'], 'opts', hex(case['opts']), 'master', case['master'],
                      'lock', case['lock'], errors, flush=True)
    print(f'{len(cases)} cases, {failures} failures')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
