"""ctypes wrapper for libgxt.so, the longplay drift tracer (diagnostic, emulator evidence only).

libgxt.so is the in-process Geargrafx 78fc3d7 core of research/longplay/fast plus
shim_trace.cpp: the same run loop as the core's own RunToVBlank (GG_DISABLE_DISASSEMBLER
build), with passive recording of (master clock, PC, bank) per instruction (trace_frame),
master clocks of watched PCs (watch), and a RAM snapshot at the n-th hit of a PC (snap).
Recording reads state only; a 70,100-frame replay gave the same per-frame update counter
as the headless longplay_six runs in all four builds tested. Build: make (Makefile here).
States are the headless emulator's state files (entered.state of a longplay_six run).
"""
import ctypes, json, os, sys
from pathlib import Path
import numpy as np
LIB = Path(os.environ.get("GXT_LIB", "/workspace/build/longplay-drift/tracer/libgxt.so"))
from roms import ROMS
BITS = {'I': 1, 'II': 2, 'select': 4, 'run': 8, 'up': 16, 'right': 32, 'down': 64, 'left': 128}
REC = np.dtype([('clk', '<u8'), ('pc', '<u2'), ('bank', 'u1'), ('done', 'u1'), ('cyc', '<u4')])
HIT = np.dtype([('frame', '<u4'), ('which', '<u4'), ('clk', '<u8')])
FRAME = 358995
RECORDING = '/workspace/build/longplay-six/full/full-4bba5f4.json'


def inputs(path=RECORDING):
    run = json.loads(Path(path).read_text())
    out = []
    for n, buttons in run['segments']:
        m = 0
        for b in buttons:
            m |= BITS[b]
        out += [m] * n
    return np.array(out, dtype=np.uint8)


class T:
    def __init__(self, rom, load=True):
        L = self.lib = ctypes.CDLL(str(LIB))
        L.gx_init.argtypes = [ctypes.c_char_p]
        L.gx_load_state.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        L.gx_state_size.restype = ctypes.c_size_t
        L.gx_save_state.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        L.gx_save_state.restype = ctypes.c_size_t
        L.gx_run.argtypes = [ctypes.c_int, ctypes.c_int]
        L.gx_set_buttons.argtypes = [ctypes.c_int]
        L.gx_wram.restype = ctypes.POINTER(ctypes.c_ubyte)
        L.gx_clock.restype = ctypes.c_ulonglong
        L.gx_trace_frame.restype = ctypes.c_long
        L.gx_trace_frame.argtypes = [ctypes.c_void_p, ctypes.c_long]
        L.gx_run_watch.restype = ctypes.c_long
        L.gx_run_watch.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p]
        if load and not L.gx_init(str(ROMS.get(rom, rom)).encode()):
            raise RuntimeError('load failed')
        self.ram = (ctypes.c_ubyte * 0x2000).from_address(ctypes.addressof(L.gx_wram().contents))
        self.size = None
        self.buf = np.zeros(200000, dtype=REC)

    def load(self, state):
        if not isinstance(state, (bytes, bytearray)):
            state = Path(state).read_bytes()
        if not self.lib.gx_load_state(bytes(state), len(state)):
            raise RuntimeError('load_state failed')
        self.lib.gx_reset_held(); self.lib.gx_set_buttons(0xff); self.lib.gx_set_buttons(0)

    def save(self):
        if self.size is None:
            self.size = self.lib.gx_state_size() + 4096
        b = ctypes.create_string_buffer(self.size)
        n = self.lib.gx_save_state(b, self.size)
        return b.raw[:n]

    def press(self, m):
        self.lib.gx_set_buttons(int(m))

    def step(self, n=1):
        self.lib.gx_run(n, 0)

    def clock(self):
        return self.lib.gx_clock()

    def r(self, addr, n=1):
        o = addr - 0x2000
        return bytes(self.ram[o:o + n])

    def trace_frame(self):
        n = self.lib.gx_trace_frame(self.buf.ctypes.data, len(self.buf))
        assert 0 <= n <= len(self.buf), n
        return self.buf[:n].copy()

    def watch(self, frames, keys, buttons, cap=2000000):
        k = np.array(keys, dtype=np.uint32)
        h = np.zeros(cap, dtype=HIT)
        bt = np.ascontiguousarray(buttons, dtype=np.uint8)
        assert len(bt) >= frames
        n = self.lib.gx_run_watch(frames, k.ctypes.data, len(k), h.ctypes.data, cap, bt.ctypes.data)
        assert n <= cap, n
        return h[:n].copy()


def _until(self, bank, pc, max_instr=5000000):
    self.lib.gx_run_until.restype = ctypes.c_long
    self.lib.gx_run_until.argtypes = [ctypes.c_uint32, ctypes.c_long]
    return self.lib.gx_run_until((bank << 16) | pc, max_instr)


T.until = _until


def _snap(self, bank, pc):
    L = self.lib
    L.gx_frame_snap.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p]
    buf = np.zeros(0x2000, np.uint8); clk = ctypes.c_ulonglong(0)
    ok = L.gx_frame_snap((bank << 16) | pc, buf.ctypes.data, ctypes.byref(clk))
    return (buf, clk.value) if ok else (None, None)


T.snap = _snap
