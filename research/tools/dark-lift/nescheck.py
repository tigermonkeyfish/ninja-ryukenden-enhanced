"""4-1 in the NES modes, from cap.py captures of the stored 4-1 run
(research reference, not a maintained tool): in every capture the RAM
palette holds the variant's set-8 colour (src/nes-palette, NES-B re-lit)
in every entry of the set that Original mode holds at the original set's
value in the same frame (entries the game animates or rewrites are listed
apart), the VCE equals the RAM palette for those entries, and the back
trunks' entries (rows 0 and 3, entries 6 and 8-11) are lighter than the
fill's colour $040.
usage: nescheck.py CAP ORIGINAL.pce"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import nes_palette as NP  # noqa: E402

cap, original = Path(sys.argv[1]), Path(sys.argv[2]).read_bytes()
original = original[512:] if len(original) % 8192 == 512 else original
addr, count = struct.unpack_from('<HH', original, NP.SET_TABLE + 4 * 8)
base = NP.unpack(original[NP.SET_TABLE + addr - 0x6000:], count)
data = NP.load()
want = {'nes-a': NP.layout(data)['sets'][8], 'nes-b': NP.layout(NP.relit(data))['sets'][8]}
BACK = [row * 16 + entry for row in (0, 3) for entry in (6, 8, 9, 10, 11)]


def words(path, n=512, at=0):
    d = Path(path).read_bytes()[at:]
    return [(d[2 * i] | d[2 * i + 1] << 8) & 0x1ff for i in range(n)]


ok = True
for mode in ('nes-a', 'nes-b'):
    for f in (250, 700, 1150, 1450, 1750):
        ram_o = words(cap / f'4-1-f{f}-original.ram')
        ram, vce = words(cap / f'4-1-f{f}-{mode}.ram'), words(cap / f'4-1-f{f}-{mode}.vce')
        managed = [i for i in range(count) if i % 16 and ram_o[i] == base[i]]
        bad = [(i, f'{want[mode][i]:03X}', f'{ram[i]:03X}') for i in managed if ram[i] != want[mode][i]]
        raw = [i for i in managed if vce[i] != ram[i]]
        back = [f'{ram[i]:03X}' for i in BACK]
        lighter = all(NP.lightness(ram[i]) > NP.lightness(0x040) for i in BACK)
        nes = all(ram[i] in NP.NES_COLOURS for i in managed)
        ok = ok and not bad and not raw and lighter and nes and all(i in managed for i in BACK)
        print(f'{mode} 4-1 f{f}: {len(managed)} of {count} set entries checked ({count - len(managed)} game-written or '
              f'colour 0), {len(bad)} not the set-8 colour {bad[:6]}, {len(raw)} VCE != RAM; back trunks {back} '
              f'{"lighter than $040" if lighter else "NOT LIGHTER"}; NES colours only: {nes}')
print('nescheck', 'passed' if ok else 'FAILED')
