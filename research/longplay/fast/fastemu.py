"""In-process Geargrafx core (ctypes) for fast route search. Diagnostic tool.

Build the library with research/longplay/fast/Makefile (shim.cpp, against the
same Geargrafx 78fc3d7 core sources as the headless emulator). States are the
headless emulator's state files (same native format), so a search can start
from a state the headless emulator saved and its result is replayed there.
Buttons change only between frames, as with MCP controller_button.
"""
import ctypes
from pathlib import Path

LIB = Path('/workspace/build/longplay/fastemu/libgx.so')
ROM = Path('/workspace/roms/Ninja Ryukenden - Enhanced v1.11-dev (apocalypse, reset 2, palette timing 2).pce')
BITS = {'I': 1, 'II': 2, 'select': 4, 'run': 8, 'up': 16, 'right': 32, 'down': 64, 'left': 128}
HEALTH, LIVES, X, Y, AREA, STAGE = 0xead, 0xeaf, 0xe9e, 0xea0, 0xe60, 0xe5f


def airborne(i):
    """Ryu's motion state $2EAA: 0 stand, 1 walk, 2 crouch, 3 air, 5 clinging to a
    wall, 6 slash (ground or air), 8 crouch slash, 9 hurt (knocked back)."""
    return i['state'] in (3, 9) or (i['state'] == 6 and i['vy'] != 0)


def mask(buttons):
    m = 0
    for b in buttons:
        m |= BITS[b]
    return m


class Fast:
    def __init__(self, rom=ROM):
        self.lib = ctypes.CDLL(str(LIB))
        L = self.lib
        L.gx_init.argtypes = [ctypes.c_char_p]
        L.gx_load_state.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        L.gx_state_size.restype = ctypes.c_size_t
        L.gx_save_state.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        L.gx_save_state.restype = ctypes.c_size_t
        L.gx_run.argtypes = [ctypes.c_int, ctypes.c_int]
        L.gx_set_buttons.argtypes = [ctypes.c_int]
        L.gx_wram.restype = ctypes.POINTER(ctypes.c_ubyte)
        L.gx_fb.restype = ctypes.POINTER(ctypes.c_ubyte)
        if not L.gx_init(str(rom).encode()):
            raise RuntimeError('load failed')
        self.ram = (ctypes.c_ubyte * 0x2000).from_address(ctypes.addressof(L.gx_wram().contents))
        self.held = 0
        self.size = None

    def load(self, state):
        """state: bytes or a path."""
        if not isinstance(state, (bytes, bytearray)):
            state = Path(state).read_bytes()
        if not self.lib.gx_load_state(bytes(state), len(state)):
            raise RuntimeError('load_state failed')
        # A state carries the controller state; force a known release.
        self.lib.gx_reset_held()
        self.lib.gx_set_buttons(0xff)
        self.lib.gx_set_buttons(0)
        self.held = 0

    def save(self):
        if self.size is None:
            self.size = self.lib.gx_state_size() + 4096
        buf = ctypes.create_string_buffer(self.size)
        n = self.lib.gx_save_state(buf, self.size)
        if not n:
            raise RuntimeError('save_state failed')
        return buf.raw[:n]

    def press(self, buttons):
        m = buttons if isinstance(buttons, int) else mask(buttons)
        self.lib.gx_set_buttons(m)
        self.held = m

    def step(self, frames, buttons=None, render=False):
        if buttons is not None:
            self.press(buttons)
        self.lib.gx_run(frames, 1 if render else 0)

    def play(self, segments):
        for n, b in segments:
            self.step(n, b)

    def rd(self, off, n=1):
        return bytes(self.ram[off:off + n])

    def info(self):
        r = self.ram
        return {'x': r[X] | r[X + 1] << 8, 'y': r[Y], 'area': r[AREA], 'stage': r[STAGE],
                'lives': r[LIVES], 'health': r[HEALTH], 'cam': r[0x20f] | r[0x210] << 8,
                'pages': r[0x237], 'master': r[0x240], 'm2': r[0x241], 'boss': r[0x1035],
                'state': r[0xeaa], 'bx': r[0xf1c],
                'vy': r[0xea7] - 256 if r[0xea7] >= 128 else r[0xea7]}

    def screenshot(self, path):
        """Render the next frame's picture: call step(1, render=True) first."""
        w, h = ctypes.c_int(), ctypes.c_int()
        self.lib.gx_fb_size(ctypes.byref(w), ctypes.byref(h))
        W, H = w.value, h.value
        data = bytes(self.lib.gx_fb()[:W * H * 4])
        from PIL import Image
        Image.frombytes('RGBA', (W, H), data).convert('RGB').save(path)
