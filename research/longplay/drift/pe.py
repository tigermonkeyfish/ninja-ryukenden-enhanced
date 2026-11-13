"""palette-exact probes on libgxw.so (the tracer core plus a RAM access watch and power-on
with forced backup RAM; Makefile target watch). Diagnostic, emulator evidence only.

    W(rom, mode)        power on with MODE's settings entry in backup RAM (None: no backup RAM)
    w.boot()            the title left with Run as longplay_lib.boot_to_first_update does, stop at
                        the first frame whose update counter runs in gameplay (frame-step granularity)
    w.run_w(n, buttons) n frames, returning the watched RAM accesses (WREC records)
"""
import ctypes, os, sys
from pathlib import Path
import numpy as np
os.environ.setdefault('GXT_LIB', '/workspace/build/palette-exact/tracer/libgxw.so')
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
from tracer import T, inputs, BITS, FRAME, HIT     # noqa: E402,F401
import bram_image as bi                             # noqa: E402
MODE_BITS = {'original': 0x00, 'apocalypse': 0x18, 'nes-a': 0x08, 'nes-b': 0x28, 'sms': 0xb8, 'gb dmg': 0x10}
WREC = np.dtype([('frame', '<u4'), ('off', '<u2'), ('val', 'u1'), ('w', 'u1'), ('pc', '<u2'), ('bank', 'u1'),
                 ('pad', 'u1'), ('clk', '<u8')], align=True)   # the C struct's layout (24 bytes)


class W(T):
    def __init__(self, rom, mode='original', language=1):
        L = ctypes.CDLL(os.environ['GXT_LIB'])
        L.gx_init_bram.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        if mode is None:
            ok = L.gx_init_bram(str(rom).encode(), None, 0)
        else:
            img = bi.image([bi.settings_entry(options=MODE_BITS[mode], language=language)])
            ok = L.gx_init_bram(str(rom).encode(), bytes(img), len(img))
        if not ok:
            raise RuntimeError('power-on failed')
        super().__init__(rom, load=False)
        L = self.lib             # argtypes belong to this CDLL object
        L.gx_run_w.restype = ctypes.c_long
        L.gx_run_w.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long, ctypes.c_uint32,
                               ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
        L.gx_watch_range.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.frame = 0

    def watch_range(self, lo, hi, writes_only=True):
        """RAM offsets (CPU address - $2000) [lo, hi) to watch."""
        self.lib.gx_watch_range(lo, hi, 1 if writes_only else 0)

    def run_w(self, n, buttons=None, keys=(), cap=1 << 20, hcap=1 << 16):
        """n frames; returns (RAM accesses in the watched range, hits on keys)."""
        rec = np.zeros(cap, dtype=WREC)
        k = np.array(list(keys), dtype=np.uint32)
        h = np.zeros(hcap, dtype=HIT)
        nh = ctypes.c_long(0)
        b = None if buttons is None else np.ascontiguousarray(buttons, dtype=np.uint8)
        n_acc = self.lib.gx_run_w(n, None if b is None else b.ctypes.data, rec.ctypes.data, cap, self.frame,
                                  k.ctypes.data if len(k) else None, len(k), h.ctypes.data, hcap, ctypes.byref(nh))
        self.frame += n
        assert n_acc <= cap and nh.value <= hcap, (n_acc, nh.value)
        return rec[:n_acc].copy(), h[:nh.value].copy()

    def boot(self, limit=20000):
        """longplay_lib.boot_to_first_update's title handling (Run at the title after 180
        frames, and every 300 frames before it), frame by frame; stops after the frame in
        which gameplay (master 0) begins after the title. Returns boot frames. The headless
        tool then runs to 1-1's first update and saves a state; here the core simply goes on."""
        previous, since, presses, pressed, title = None, 0, [200], False, False
        for frame in range(1, limit):
            held = 0
            for p in presses:
                if p <= frame - 1 < p + 2:
                    held = BITS['run']
            self.press(held)
            self.step(1)
            since += 1
            master = self.r(0x2240, 2)
            if master != previous:
                previous, since = master, 0
            if master == b'\x01\x01':
                title = True
            if master == b'\x01\x01' and since == 180 and not pressed:
                presses.append(frame)
                pressed = True
            if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150 and not title:
                presses.append(frame)
            if title and master[0] == 0 and frame > presses[-1] + 2:
                self.press(0)
                # as the headless tool: on to 1-1's first update ($8457, bank 1), then save
                # and reload there so frame 1 of a recording is the step that follows
                if self.until(1, 0x8457) < 0:
                    raise RuntimeError('first update not reached')
                self.entered = self.save()
                self.load(self.entered)
                return frame
        raise RuntimeError('gameplay not reached')
