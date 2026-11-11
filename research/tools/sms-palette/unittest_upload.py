"""Unit-test the vblank palette upload in place, every mode, HELL and SMS
included (docs/pc-engine/EMULATOR.md, "Unit-test a small routine in place"),
against an independent Python model. The HELL probe of the same name with
the SMS build's layout: the mode is $2100 bits 3-5 (family bits 3-4, variant
bit 5: $38 SMS, stored with bit 7 as $B8, every entry and the border mapped
through the SMS table, as GB DMG; $30 uploads as GB DMG, $20 and $28 as
Original; $38 without bit 7 as HELL) and the module's state is $2104 bits
5-7; a case writes both and checks that $2100 comes
back unchanged and $2104 as the model says. HELL ($18): entries 0 to
HELL_MAPPED-1 mapped through the HELL table, the rest and the border
written unchanged, unmapped chunks charged n/4 + n/32 + RAW_SETUP budget
colours.

From the 1-1 main-loop hook ($83F3), each case writes a RAM palette ($2286),
a border colour, the queue ($2260-$2280), the lock, the options byte and
$2240, fills the VCE with a sentinel and the borrowed zero page $20-$26 with
known bytes, then calls the fixed-bank trampoline
by a synthetic JSR and runs back to the hook: the vblank entry ($FEC0) with
the I flag set, as in the interrupt, and palette_now ($FEBE, X = first
colour, Y = count) with I clear, as from a renderer. Checked: every VCE word,
the queue, the options byte, the lock, S, MPR2, MPR3 (as at the hook: the
debugger cannot write MPRs; the run prints it) and zero page $20-$26;
for the vblank entry also X and Y.
usage: unittest_upload.py ROM [CASES] [SEED]   (MODEL_RAW_SETUP=n or MODEL_SMS_TABLE=gb: negative controls)"""
import os
import random
import sys

from smstools import GB, HELL, HELL_MAPPED, SMS, Session, cv, mode_due, vce_words

CAP = int(os.environ.get('MODEL_CAP', 168))
ENTRY_COST = 6
LEFTOVER_CAP = 16
BUDGET_MIN = 16
RAW_SETUP = int(os.environ.get('MODEL_RAW_SETUP', 3))
RAW_ANY = 40
SMS_AS_GB = os.environ.get('MODEL_SMS_TABLE') == 'gb'     # negative control: the model expects GB colours in SMS
SENTINEL = 0x1ff ^ 0x0aa



def mode_of(case):
    return mode_due(case['opts']) if case['master'] == 0 else 0


def colour(mode, i, c):
    c &= 0x1ff
    if mode == 0x10:
        return GB[c]
    if mode == 0x38:
        return (GB if SMS_AS_GB else SMS)[c]
    if mode == 0x18 and i < HELL_MAPPED:
        return HELL[c]
    return c


def run_queue(mode, queue, budget, vce, pal):
    """Upload as the module does, chunk by chunk; returns the kept entries."""
    kept = []
    spent = False
    for idx, n in queue:
        if spent:
            kept.append([idx, n])
            continue
        while n:
            chunk = min(128, n)
            if idx >= 256:
                chunk = min(chunk, 512 - idx)
            if mode == 0x18 and idx >= HELL_MAPPED:
                if budget < RAW_ANY:
                    k = budget - RAW_SETUP
                    if k <= 0:
                        spent = True
                        break
                    chunk = min(chunk, 3 * k + k // 2)
                cost = chunk // 4 + chunk // 32 + RAW_SETUP
            else:
                if mode == 0x18:
                    chunk = min(chunk, HELL_MAPPED - idx)
                chunk = min(chunk, budget)
                cost = chunk
            for i in range(idx, idx + chunk):
                vce[i] = colour(mode, i, pal[i])
            idx = (idx + chunk) & 0x1ff
            n -= chunk
            budget -= cost
            if budget == 0:
                spent = True
                break
        if n:
            kept.append([idx, n])
    return kept


def model(case):
    """(VCE words, queue entries, state byte $2104) the upload should leave."""
    vce = [SENTINEL] * 512
    pal, queue, opts = case['pal'], [list(e) for e in case['queue']], case['st']
    mode = mode_of(case)
    mapped = mode != 0
    if 'now' in case:
        first, count = case['now']
        for i in range(first, first + count):
            vce[i] = colour(mode, i, pal[i])
        return vce, queue, opts
    if case['lock']:
        return vce, queue, opts
    if bool(opts & 0x80) != mapped:
        opts ^= 0x80
        queue = [[0, 512]]
        if mapped:
            opts &= ~0x20
    if not queue:
        if mapped:
            opts &= ~0x20
        return vce, queue, opts
    if not mapped:
        for idx, n in queue:
            for i in range(idx, idx + n):
                vce[i] = pal[i] & 0xffff
        vce[256] = case['border']
        return vce, [], opts
    full = len(queue) >= 8
    busy = not 0xfd67 <= case.get('pc', 0xfd69) <= 0xfd6f
    was_busy = bool(opts & 0x40)
    opts = (opts & ~0x40) | (0x40 if busy else 0)
    if len(queue) == 1 and opts & 0x20:
        if busy or was_busy:
            return vce, queue, opts
        budget = LEFTOVER_CAP
    else:
        new = queue[1:] if opts & 0x20 else queue
        total = sum(2 * n for _, n in new)
        b = min((total >> 3) + (total >> 7), 255) if total < 2048 else 255
        b = min(b, CAP) - ENTRY_COST * (len(queue) - 1)
        budget = max(b, BUDGET_MIN)
        if opts & 0x20 and total < 1024:
            queue = queue[1:] + queue[:1]
    opts &= ~0x20
    kept = run_queue(mode, queue, budget, vce, pal)
    if kept:
        s = kept[0][0]
        kept = [[s, max(min(512, ((a - s) & 0x1ff) + n) for a, n in kept)]]
    if full:
        kept = [[0, 512]]
    vce[256] = colour(mode, 0, case['border']) if mode in (0x10, 0x38) else case['border']
    if kept:
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
            'opts': rng.choice([0xb8, 0xb8, 0xb8, 0x18, 0x18, 0x10, 0x30, 0x00, 0x08, 0x20, 0x28, 0x38, 0x98])
            | rng.randrange(8),
            'st': rng.choice([0x80, 0x80, 0xa0, 0xe0, 0xc0, 0x00, 0x20, 0x40]),
            'master': rng.choice([0, 0, 0, 1]),
            'pc': rng.choice([0xfd69, 0xfd6b, 0xfd6d, 0xfd6f, 0xfd70, 0x4f52, 0xfd66])}


def edge_cases():
    pal = list(range(512))
    base = {'pal': pal, 'border': 0x123, 'lock': 0, 'opts': 0xb8, 'st': 0x80, 'master': 0}
    cases = []
    queues = ([(0, 512)], [(0, 240)], [(0, 239)], [(0, 241)], [(239, 2)], [(240, 16)], [(224, 32)],
              [(100, 128)], [(200, 128)], [(383, 129)], [(511, 1)], [(256, 256)], [(240, 272)],
              [(0, 128), (128, 64), (300, 10)], [(0, 256)] + [(241 + i, 1) for i in range(7)],
              [(256, 16), (272, 16), (288, 16)], [(500, 12), (0, 200), (16, 16)],
              [(368, 16), (384, 16), (320, 16), (400, 16), (304, 16), (352, 16), (416, 16), (432, 16)],
              [(0, 512), (0, 512)], [(256, 128), (384, 128), (0, 240)], [(240, 128)], [(250, 6)])
    for opts in (0xb8, 0x18, 0x10):
        for q in queues:
            cases.append(dict(base, queue=q, opts=opts))
    cases.append(dict(base, queue=[], border=0x1ff))
    cases.append(dict(base, queue=[(0, 512)], lock=1))
    for opts in (0x00, 0x08, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0xb8, 0x98, 0x07, 0x1f, 0xbf, 0x3c):
        for st in (0x00, 0x80, 0xe0, 0x60):
            cases.append(dict(base, queue=[(0, 512), (16, 16)], opts=opts, st=st))
            cases.append(dict(base, queue=[], opts=opts, st=st))
    # Left-over entries: busy or idle main loop, first vblank or later.
    for opts in (0x18, 0xb8):
        for st in (0xa0, 0xe0, 0xc0, 0x80):
            for pc in (0xfd69, 0xfd6d, 0xfd6f, 0xfd70, 0xfd66, 0x8457):
                cases.append(dict(base, queue=[(176, 336)], opts=opts, st=st, pc=pc))
            cases.append(dict(base, queue=[(176, 336), (16, 16)], opts=opts, st=st, pc=0x8457))
            cases.append(dict(base, queue=[(480, 64)], opts=opts, st=st))         # wraps to colour 0
            cases.append(dict(base, queue=[(250, 300)], opts=opts, st=st))        # raw, wraps, mapped
            cases.append(dict(base, queue=[(300, 512), (0, 512)], opts=opts, st=st))
            cases.append(dict(base, queue=[(480, 32), (96, 18)], opts=opts, st=st))
            cases.append(dict(base, queue=[(260, 4)], opts=opts, st=st))          # tiny raw budget
    for master in (1, 2):
        for opts in (0x18, 0x10, 0xb8):
            for st in (0x00, 0x80):
                cases.append(dict(base, queue=[(0, 300), (400, 50)], master=master, opts=opts, st=st))
    rng = random.Random(7)
    for opts, master in ((0xb8, 0), (0x18, 0), (0x10, 0), (0x30, 0), (0x00, 0), (0x08, 0), (0x28, 0),
                         (0x38, 0), (0xb8, 1), (0x18, 1)):
        for first, count in ((16, 16), (208, 32), (0, 1), (255, 1), (128, 127), (200, 56),
                             (230, 20), (239, 2), (240, 16), (224, 127), (250, 100)):
            pal = [rng.randrange(0x200) for _ in range(512)]
            cases.append(dict(base, pal=pal, queue=[], opts=opts, master=master, now=(first, count)))
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
    g.write(0x104, bytes([case['st']]))
    g.write(0x240, bytes([case['master']]))
    g.write(0x020, bytes([0x5a, 0xa5, 0x11, 0x22, 0x33, 0x44, 0x55]))
    g.call('write_memory', {'area': 8, 'offset': '0000',
                            'bytes': bytes([SENTINEL & 0xff, SENTINEL >> 8] * 512).hex(' ')})
    cpu = g.call('get_huc6280_status')
    assert cpu['PC'] == '83F3', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    mpr2 = cpu['MPR'][2]['value']
    mpr3 = cpu['MPR'][3]['value']       # the debugger cannot write MPRs: must come back unchanged
    sp = saved['S']
    g.write(0x100 + sp - 1, bytes([0xf2, 0x83]))
    g.reg('S', sp - 2)
    live = g.read(0x100 + sp + 1, 6)
    pc = case.get('pc', 0xfd69)
    g.write(0x100 + sp + 1, bytes([0, 0, 0, 0, pc & 0xff, pc >> 8]))
    if 'now' in case:
        g.reg('X', case['now'][0])
        g.reg('Y', case['now'][1])
        g.reg('P', saved['P'] & ~0x04)
        g.reg('PC', 0xfebe)
    else:
        g.reg('X', 0x37)
        g.reg('Y', 0x73)
        g.reg('P', saved['P'] | 0x04)
        g.reg('PC', 0xfec0)
    g.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    g.run_to('83F3', polls=20000)
    after = g.call('get_huc6280_status')
    g.write(0x100 + sp + 1, live)
    regs = (after['X'], after['Y'], int(after['S'], 16), after['MPR'][2]['value'], after['MPR'][3]['value'])
    g.reg('X', saved['X'])
    g.reg('Y', saved['Y'])
    g.reg('P', saved['P'])
    vce = vce_words(g.read(0, 1024, area=8))
    r = g.read(0, 0x300)
    errors = []
    n = r[0x260]
    queue = [[r[0x271 + k] | r[0x279 + k] << 8, (r[0x261 + k] | r[0x269 + k] << 8) // 2] for k in range(min(n, 8))]
    zp = r[0x20:0x27]
    want_vce, want_queue, want_st = model(case)
    if r[0x100] != case['opts']:
        errors.append(f'options {r[0x100]:#04x} changed from {case["opts"]:#04x}')
    if r[0x104] != want_st:
        errors.append(f'state {r[0x104]:#04x} want {want_st:#04x}')
    bad = [i for i in range(512) if vce[i] != want_vce[i]]
    if bad:
        errors.append(f'VCE differs at {len(bad)} entries, first {bad[:5]} got {[hex(vce[i]) for i in bad[:5]]} '
                      f'want {[hex(want_vce[i]) for i in bad[:5]]}')
    if queue != want_queue:
        errors.append(f'queue {queue} want {want_queue}')
    if 'now' in case:
        regs = ('37', '73') + regs[2:]
    if regs != ('37', '73', sp, mpr2, mpr3):
        errors.append(f'registers X Y S MPR2 MPR3 {regs} want 37 73 {sp} {mpr2} {mpr3}')
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
        mpr3 = g.call('get_huc6280_status')['MPR'][3]['value']
        print('MPR3 at the hook', mpr3, '(HELL maps bank $43 there)', flush=True)
        for i, case in enumerate(cases):
            errors = run_case(g, case)
            if errors:
                failures += 1
                print('case', i, case['queue'], case.get('now'), 'opts', hex(case['opts']), 'st', hex(case['st']),
                      'master', case['master'],
                      'lock', case['lock'], 'pc', hex(case.get('pc', 0xfd69)), errors, flush=True)
    print(f'{len(cases)} cases, {failures} failures (RAW_SETUP model {RAW_SETUP})')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
