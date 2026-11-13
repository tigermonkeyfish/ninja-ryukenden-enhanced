"""Small HuC6280 disassembler from Geargrafx's opcode table (pceas syntax)."""
import re
SRC = '/workspace/build/toolchain/geargrafx/src/huc6280_names.h'
LEN = {'Implied': 1, '1b': 2, '1b_1b': 3, '1b_2b': 4, '2b': 3, '2b_2b_2b': 7, '1b_Relative': 2,
       '1b_1b_Relative': 4, 'ST0': 2, 'BRK': 2, 'MPR': 2}
OPS = []
for line in open(SRC):
    m = re.match(r'\s*GG_OPCODE(_SYNTAX)?\((.*)\),?\s*$', line)
    if not m:
        continue
    args = re.findall(r'"([^"]*)"|(GG_OPCode_Type_\w+)', m.group(2))
    strs = [a for a, b in args if a]
    typ = [b for a, b in args if b][0].replace('GG_OPCode_Type_', '')
    fmt = strs[1] if m.group(1) else strs[0]
    fmt = re.sub(r'\{\w\}', '', fmt)
    OPS.append((fmt, typ))
assert len(OPS) == 256, len(OPS)


def dis(read, addr, n=20):
    """read(addr) -> byte at CPU address. Yields (addr, bytes, text)."""
    out = []
    for _ in range(n):
        op = read(addr)
        fmt, typ = OPS[op]
        L = LEN[typ]
        b = [read(addr + i) for i in range(L)]
        if typ in ('1b', 'ST0', 'MPR', 'BRK'):
            t = fmt % b[1] if '%' in fmt else fmt
        elif typ == '2b':
            t = fmt % (b[1] | b[2] << 8)
        elif typ == '1b_1b':
            t = fmt % (b[1], b[2])
        elif typ == '1b_2b':
            t = fmt % (b[1], b[2] | b[3] << 8)
        elif typ == '2b_2b_2b':
            t = fmt % (b[1] | b[2] << 8, b[3] | b[4] << 8, b[5] | b[6] << 8)
        elif typ == '1b_Relative':
            d = b[1] - 256 if b[1] > 127 else b[1]
            t = fmt % ((addr + 2 + d) & 0xffff) if '%' in fmt else fmt
        elif typ == '1b_1b_Relative':
            d = b[2] - 256 if b[2] > 127 else b[2]
            try:
                t = fmt % (b[1], (addr + 3 + d) & 0xffff)
            except TypeError:
                t = fmt % (b[1], b[2])
        else:
            t = fmt
        out.append((addr, b, t))
        addr += L
    return out


class Rom:
    def __init__(self, path):
        d = open(path, 'rb').read()
        if len(d) % 0x2000 == 512:
            d = d[512:]
        self.d = d

    def reader(self, mpr):
        """mpr: dict page(0-7) -> bank."""
        def rd(a):
            bank = mpr[(a >> 13) & 7]
            return self.d[bank * 0x2000 + (a & 0x1fff)]
        return rd

    def show(self, bank_for_page, addr, n=20):
        for a, b, t in dis(self.reader(bank_for_page), addr, n):
            print(f'{a:04X}  {" ".join(f"{x:02X}" for x in b):21s} {t}')


if __name__ == '__main__':
    import sys
    from roms import ROMS
    rom = Rom(ROMS[sys.argv[1]])
    mpr = {7: 0, 4: 1, 5: 2, 6: 3, 0: 0xff, 1: 0xf8, 2: 0x46, 3: 0x37}
    for kv in sys.argv[4:]:
        p, b = kv.split('=')
        mpr[int(p)] = int(b, 16)
    rom.show(mpr, int(sys.argv[2], 16), int(sys.argv[3]))
