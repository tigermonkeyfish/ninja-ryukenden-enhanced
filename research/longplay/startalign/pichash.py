"""start-pos: per-frame picture and VCE digests over a frame range of full-load.json (emulator only).

    pichash.py ROM MODE FIRST LAST OUT.npz     MODE: original, nes-a, nes-b, sms, gb dmg, apocalypse | unmod-en

Power-on as capture.py, replay to LAST; for frames FIRST..LAST store the frame buffer's and the VCE's
SHA-1 (first 8 bytes) and the RAM sample (camera, $2E4B-$2E4E, $2E63, stage, area, counter).
Two builds in one mode compare frame for frame (the RAM must be equal for the pictures to be).
"""
import hashlib, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'load'))
import lx                                                              # noqa: E402
from pe import W, inputs                                                # noqa: E402

rom, mode, first, last, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
inp = inputs(str(Path(__file__).resolve().parents[1] / 'full-load.json'))
t = W(rom, None if mode == 'unmod-en' else mode)
lx.boot(t, mode)
pic, vce, meta = [], [], []
h = lambda b: int.from_bytes(hashlib.sha1(b).digest()[:8], 'little')
for f in range(1, last + 1):
    t.press(inp[f - 1])
    t.lib.gx_run(1, 1 if f >= first else 0)
    if f >= first:
        pic.append(h(lx.frame_rgb(t).tobytes()))
        vce.append(h(lx.vce(t).tobytes()))
        r = bytes(t.ram)
        meta.append([f, r[0x20F] | r[0x210] << 8, r[0xE4B], r[0xE4C], r[0xE4D], r[0xE4E], r[0xE63], r[0xE5F],
                     r[0xE60], r[0]])
np.savez(out, pic=np.array(pic, np.uint64), vce=np.array(vce, np.uint64), meta=np.array(meta, np.int32))
print('done', out)
