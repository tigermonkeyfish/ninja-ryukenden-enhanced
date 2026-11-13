"""Replay the pinned recording in the tracer core from an entered state, recording per
frame the counter and frame-end clock, and the master clock of watched PCs.
Usage: watchrun.py TAG ROM STATE LAST_FRAME"""
import sys, time, array, zlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
from tracer import T, inputs
KEYS = [(0, 0xE06C), (0, 0xE061), (0, 0xFCEC), (0, 0xFD1F), (0, 0xFCE9), (0x38, 0x4006), (0, 0xFD26), (0, 0xFCD7)]
NAMES = ['upd', 'wait', 'vbl', 'vbl_end', 'vbl_busy', 'music', 'rcr', 'irq1']
SAVE = set(range(5000, 6001, 50)) | set(range(13000, 13401, 25)) | set(range(51000, 52001, 50)) | \
       set(range(53100, 53401, 25)) | set(range(65500, 66001, 50)) | set(range(82700, 83101, 25)) | set(range(64300, 64501, 50)) | set(range(69900, 70101, 50)) | set(range(0, 126001, 5000))
tag, rom, state, last = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
rec = sys.argv[5] if len(sys.argv) > 5 else None
out = Path('/workspace/build/longplay-drift/watch'); out.mkdir(exist_ok=True)
sdir = Path('/workspace/build/longplay-drift/states'); sdir.mkdir(exist_ok=True)
inp = inputs(rec) if rec else inputs()
t = T(rom); t.load(state)
keys = np.array([(b << 16) | p for b, p in KEYS], dtype=np.uint32)
cnt = np.zeros(last + 1, np.uint8); fend = np.zeros(last + 1, np.uint64); ramcrc = np.zeros(last + 1, np.uint32)
cnt[0] = t.r(0x2000)[0]; fend[0] = t.clock()
allhits = []
t0 = time.time()
for f in range(1, last + 1):
    t.press(inp[f - 1])
    h = t.watch(1, keys, inp[f - 1:f], cap=4096)
    h['frame'] = f
    allhits.append(h)
    cnt[f] = t.r(0x2000)[0]; fend[f] = t.clock()
    ramcrc[f] = zlib.crc32(bytes(t.ram))
    if f in SAVE:
        (sdir / f'{tag}-{f}.state').write_bytes(t.save())
    if f % 10000 == 0:
        print(tag, f, round(time.time() - t0), flush=True)
hits = np.concatenate(allhits)
np.savez_compressed(out / f'{tag}.npz', cnt=cnt, fend=fend, ramcrc=ramcrc, hits=hits, names=np.array(NAMES))
print(tag, 'done', last, round(time.time() - t0), 'hits', len(hits))
