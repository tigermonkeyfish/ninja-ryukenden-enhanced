#!/usr/bin/env python3
"""Minimal HuC6280 disassembler. usage: dis.py ROM BANK:ADDR [count] [--base CPUBASE]
ROM headerless or headered; BANK hex, ADDR hex CPU address (bank mapped at ADDR&0xE000)."""
import sys

T = {}
def d(op, m, mode):
    T[op] = (m, mode)
# modes: imp, imm, zp, zpx, zpy, abs, absx, absy, izx, izy, izp, ind, indx, rel, zprel, blk, tstzp, tstabs, tstzpx, tstabsx, acc
rows = """
00 BRK imp|01 ORA izx|02 SXY imp|03 ST0 imm|04 TSB zp|05 ORA zp|06 ASL zp|08 PHP imp|09 ORA imm|0A ASL acc|0C TSB abs|0D ORA abs|0E ASL abs
10 BPL rel|11 ORA izy|12 ORA izp|13 ST1 imm|14 TRB zp|15 ORA zpx|16 ASL zpx|18 CLC imp|19 ORA absy|1A INC acc|1C TRB abs|1D ORA absx|1E ASL absx
20 JSR abs|21 AND izx|22 SAX imp|23 ST2 imm|24 BIT zp|25 AND zp|26 ROL zp|28 PLP imp|29 AND imm|2A ROL acc|2C BIT abs|2D AND abs|2E ROL abs
30 BMI rel|31 AND izy|32 AND izp|34 BIT zpx|35 AND zpx|36 ROL zpx|38 SEC imp|39 AND absy|3A DEC acc|3C BIT absx|3D AND absx|3E ROL absx
40 RTI imp|41 EOR izx|42 SAY imp|43 TMA imm|44 BSR rel|45 EOR zp|46 LSR zp|48 PHA imp|49 EOR imm|4A LSR acc|4C JMP abs|4D EOR abs|4E LSR abs
50 BVC rel|51 EOR izy|52 EOR izp|53 TAM imm|54 CSL imp|55 EOR zpx|56 LSR zpx|58 CLI imp|59 EOR absy|5A PHY imp|5D EOR absx|5E LSR absx
60 RTS imp|61 ADC izx|62 CLA imp|64 STZ zp|65 ADC zp|66 ROR zp|68 PLA imp|69 ADC imm|6A ROR acc|6C JMP ind|6D ADC abs|6E ROR abs
70 BVS rel|71 ADC izy|72 ADC izp|73 TII blk|74 STZ zpx|75 ADC zpx|76 ROR zpx|78 SEI imp|79 ADC absy|7A PLY imp|7C JMP indx|7D ADC absx|7E ROR absx
80 BRA rel|81 STA izx|82 CLX imp|83 TST tstzp|84 STY zp|85 STA zp|86 STX zp|88 DEY imp|89 BIT imm|8A TXA imp|8C STY abs|8D STA abs|8E STX abs
90 BCC rel|91 STA izy|92 STA izp|93 TST tstabs|94 STY zpx|95 STA zpx|96 STX zpy|98 TYA imp|99 STA absy|9A TXS imp|9C STZ abs|9D STA absx|9E STZ absx
A0 LDY imm|A1 LDA izx|A2 LDX imm|A3 TST tstzpx|A4 LDY zp|A5 LDA zp|A6 LDX zp|A8 TAY imp|A9 LDA imm|AA TAX imp|AC LDY abs|AD LDA abs|AE LDX abs
B0 BCS rel|B1 LDA izy|B2 LDA izp|B3 TST tstabsx|B4 LDY zpx|B5 LDA zpx|B6 LDX zpy|B8 CLV imp|B9 LDA absy|BA TSX imp|BC LDY absx|BD LDA absx|BE LDX absy
C0 CPY imm|C1 CMP izx|C2 CLY imp|C3 TDD blk|C4 CPY zp|C5 CMP zp|C6 DEC zp|C8 INY imp|C9 CMP imm|CA DEX imp|CC CPY abs|CD CMP abs|CE DEC abs
D0 BNE rel|D1 CMP izy|D2 CMP izp|D3 TIN blk|D4 CSH imp|D5 CMP zpx|D6 DEC zpx|D8 CLD imp|D9 CMP absy|DA PHX imp|DD CMP absx|DE DEC absx
E0 CPX imm|E1 SBC izx|E3 TIA blk|E4 CPX zp|E5 SBC zp|E6 INC zp|E8 INX imp|E9 SBC imm|EA NOP imp|EC CPX abs|ED SBC abs|EE INC abs
F0 BEQ rel|F1 SBC izy|F2 SBC izp|F3 TAI blk|F4 SET imp|F5 SBC zpx|F6 INC zpx|F8 SED imp|F9 SBC absy|FA PLX imp|FD SBC absx|FE INC absx
"""
for line in rows.strip().splitlines():
    for item in line.split('|'):
        op, m, mode = item.split()
        d(int(op, 16), m, mode)
for i in range(8):
    d(0x07 + 16 * i, f'RMB{i}', 'zp')
    d(0x87 + 16 * i, f'SMB{i}', 'zp')
    d(0x0F + 16 * i, f'BBR{i}', 'zprel')
    d(0x8F + 16 * i, f'BBS{i}', 'zprel')
SIZE = dict(imp=1, acc=1, imm=2, zp=2, zpx=2, zpy=2, izx=2, izy=2, izp=2, rel=2,
            abs=3, absx=3, absy=3, ind=3, indx=3, zprel=3, blk=7, tstzp=3, tstzpx=3, tstabs=4, tstabsx=4)


def dis(mem, pc, base):
    """mem: bytes for CPU window starting at base."""
    o = pc - base
    op = mem[o]
    if op not in T:
        return 1, f'.db ${op:02X}'
    m, mode = T[op]
    n = SIZE[mode]
    b = mem[o:o + n]
    w = lambda i: b[i] | (b[i + 1] << 8)
    if mode in ('imp',):
        s = m
    elif mode == 'acc':
        s = m + ' A'
    elif mode == 'imm':
        s = f'{m} #${b[1]:02X}'
    elif mode == 'zp':
        s = f'{m} <${b[1]:02X}'
    elif mode == 'zpx':
        s = f'{m} <${b[1]:02X},X'
    elif mode == 'zpy':
        s = f'{m} <${b[1]:02X},Y'
    elif mode == 'izx':
        s = f'{m} [${b[1]:02X},X]'
    elif mode == 'izy':
        s = f'{m} [${b[1]:02X}],Y'
    elif mode == 'izp':
        s = f'{m} [${b[1]:02X}]'
    elif mode == 'rel':
        t = (pc + 2 + (b[1] - 256 if b[1] > 127 else b[1])) & 0xffff
        s = f'{m} ${t:04X}'
    elif mode == 'abs':
        s = f'{m} ${w(1):04X}'
    elif mode == 'absx':
        s = f'{m} ${w(1):04X},X'
    elif mode == 'absy':
        s = f'{m} ${w(1):04X},Y'
    elif mode == 'ind':
        s = f'{m} [${w(1):04X}]'
    elif mode == 'indx':
        s = f'{m} [${w(1):04X},X]'
    elif mode == 'zprel':
        t = (pc + 3 + (b[2] - 256 if b[2] > 127 else b[2])) & 0xffff
        s = f'{m} <${b[1]:02X},${t:04X}'
    elif mode == 'blk':
        s = f'{m} ${w(1):04X},${w(3):04X},${w(5):04X}'
    elif mode == 'tstzp':
        s = f'TST #${b[1]:02X},<${b[2]:02X}'
    elif mode == 'tstzpx':
        s = f'TST #${b[1]:02X},<${b[2]:02X},X'
    elif mode == 'tstabs':
        s = f'TST #${b[1]:02X},${w(2):04X}'
    elif mode == 'tstabsx':
        s = f'TST #${b[1]:02X},${w(2):04X},X'
    return n, s


def main():
    rom = open(sys.argv[1], 'rb').read()
    if len(rom) % 8192 == 512:
        rom = rom[512:]
    bank, addr = sys.argv[2].split(':')
    bank, addr = int(bank, 16), int(addr, 16)
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    base = addr & 0xE000
    mem = rom[bank * 0x2000:(bank + 1) * 0x2000] + b'\0' * 8
    pc = addr
    for _ in range(count):
        if pc - base >= 0x2000:
            break
        n, s = dis(mem, pc, base)
        raw = mem[pc - base:pc - base + n].hex(' ')
        print(f'{bank:02X}:{pc:04X}  {raw:21s} {s}')
        pc += n


if __name__ == '__main__':
    main()
