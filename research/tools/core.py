"""Shared helpers: headless Geargrafx session wrapper and stdlib PNG I/O."""
import base64
import json
import struct
import sys
import zlib
from pathlib import Path

import local
sys.path.insert(0, str(local.SCRIPTS))
import emulator_session as em  # noqa: E402

GEARGRAFX = local.EMULATOR
ORIGINAL = local.ORIGINAL
ENHANCED = local.ENHANCED

# Patch Level Select order (src/options/options-text.inc).
STAGE_NAMES = ['1-1', '1-2', '2-1', '2-2', '2-3', '3-1', '3-2', '3-3', '4-1', '4-2',
               '4-3', '4-4', '5-1', '5-2', '5-3', '5-4', '6-1', '6-2', '6-3',
               '6-4A', '6-4B', '6-4C']
NEXT_SEQUENCE = [4, 5, 7, 8, 9, 11, 12, 13, 15, 17, 18, 19, 21, 22, 23, 25, 27, 28,
                 29, 31, 33, 35]
PARALLAX = [0, 3, 5, 6, 8, 9, 13, 14, 15, 16, 18]


def unpack(result):
    texts = [item['text'] for item in result.get('content', []) if item['type'] == 'text']
    return json.loads(texts[0]) if texts else result


class Session:
    def __init__(self, logdir):
        em.BINARY = GEARGRAFX
        em.ROOT = Path(logdir)
        self.emu = em.Emulator()

    def __enter__(self):
        self.emu.__enter__()
        return self

    def __exit__(self, *a):
        self.emu.__exit__(*a)

    def call(self, name, arguments=None):
        return unpack(self.emu.call(name, arguments))

    def step(self, frames=1):
        try:
            return self.call('debug_step_frame', {'frames': frames, 'mode': 'sync'})
        except RuntimeError as exc:
            if 'interrupted' in str(exc):
                return None
            raise

    def status(self):
        return self.call('debug_get_status')

    def cpu(self):
        return self.call('get_huc6280_status')

    def read(self, offset, size, area=0):
        unit = 2 if area in (4, 6, 8) else 1
        out = b''
        while size > 0:
            n = min(size, 0x2000)
            out += bytes.fromhex(self.call('read_memory', {
                'area': area, 'offset': f'{offset:04x}', 'size': n})['data'])
            offset += n // unit
            size -= n
        return out

    def write(self, offset, data, area=0):
        r = self.call('write_memory', {'area': area, 'offset': f'{offset:04x}',
                                       'bytes': data.hex(' ')})
        assert r['bytes_written'] == len(data), r
        return r

    def reg(self, name, value):
        self.call('write_huc6280_register', {'name': name, 'value': f'{value:x}'})

    def button(self, button, action):
        self.call('controller_button', {'player': 1, 'button': button, 'action': action})

    def screenshot_png(self):
        shot = self.emu.call('get_screenshot')
        return base64.b64decode(next(item['data'] for item in shot['content']
                                     if item['type'] == 'image'))


# ---------------------------------------------------------------- PNG

def png_decode(data):
    """Return (width, height, rows) with rows as lists of (r, g, b) tuples."""
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, idat, plte = 8, b'', None
    while pos < len(data):
        length, kind = struct.unpack('>I4s', data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', body)
            assert depth == 8 and interlace == 0, (depth, interlace)
        elif kind == b'PLTE':
            plte = [tuple(body[i:i + 3]) for i in range(0, len(body), 3)]
        elif kind == b'IDAT':
            idat += body
        elif kind == b'IEND':
            break
    bpp = {2: 3, 6: 4, 3: 1, 0: 1}[ctype]
    raw = zlib.decompress(idat)
    stride = w * bpp
    rows, prev = [], bytearray(stride)
    i = 0
    for _ in range(h):
        f = raw[i]
        line = bytearray(raw[i + 1:i + 1 + stride])
        i += 1 + stride
        if f == 1:
            for x in range(bpp, stride):
                line[x] = (line[x] + line[x - bpp]) & 255
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 255
        elif f == 3:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                line[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
        elif f == 4:
            for x in range(stride):
                a = line[x - bpp] if x >= bpp else 0
                b = prev[x]
                c = prev[x - bpp] if x >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        prev = line
        if ctype == 3:
            rows.append([plte[v] for v in line])
        elif ctype == 0:
            rows.append([(v, v, v) for v in line])
        else:
            rows.append([tuple(line[x:x + 3]) for x in range(0, stride, bpp)])
    return w, h, rows


def png_encode(rows):
    h, w = len(rows), len(rows[0])
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for px in row:
            raw.extend(px)

    def chunk(kind, body):
        return (struct.pack('>I', len(body)) + kind + body +
                struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 6)) + chunk(b'IEND', b''))


# ---------------------------------------------------------------- game control

def boot_to_gameplay(s, rom, log=print):
    """Cold boot, leave attract/title with Run, stop at the first gameplay-loop hook."""
    s.call('load_media', {'file_path': str(rom)})
    s.call('debug_pause')
    s.call('set_breakpoint', {'address': '23f3', 'memory_area': 'rom', 'execute': True})
    prev, since, presses, title_pressed = None, 0, [200], False
    for frame in range(1, 20000):
        s.step(1)
        since += 1
        st = s.status()
        if st.get('at_breakpoint') and st['pc'] == '83F3':
            log(f'gameplay hook at boot frame {frame}')
            return frame
        master = s.read(0x240, 2)
        if master != prev:
            log(f'frame {frame}: master {master.hex()}')
            prev, since = master, 0
        if master == b'\x01\x01' and since == 180 and not title_pressed:
            presses.append(frame)
            title_pressed = True
        # The Enhanced splash precedes the native master script; Run leaves it.
        if master in (b'\x00\x00', b'\x01\x00') and since % 300 == 150:
            presses.append(frame)
        for p in presses:
            if frame == p:
                s.button('run', 'press')
            elif frame == p + 2:
                s.button('run', 'release')
    raise RuntimeError('gameplay not reached')


def run_to_hook(s, max_polls=4000):
    """Continue until the gameplay-loop breakpoint ($83F3, bank 1) is hit."""
    s.call('debug_continue')
    for _ in range(max_polls):
        st = s.status()
        if st.get('paused'):
            if st['pc'] == '83F3':
                return st
            raise RuntimeError(f'Unexpected stop {st}')
    raise TimeoutError('gameplay hook not reached')


def jump_to_stage(s, stage):
    """Reproduce the patch Level Select's state change with debugger writes.

    At $83F3 (native `lda $2E63`), write the same progression bytes the patch
    selector writes, then call native stage initialization $8244 (A = stage)
    with a synthetic return to $83F3. X/Y/P are restored afterwards, as the
    patch hook's php/phx/phy ... plp do. Applied identically to both ROMs.
    """
    cpu = s.cpu()
    assert cpu['PC'] == '83F3' and cpu['MPR'][4]['value'] == '01', cpu
    saved = {k: int(cpu[k], 16) for k in ('X', 'Y', 'P', 'S')}
    s.write(0x241, bytes([stage]))
    s.write(0x247, bytes([NEXT_SEQUENCE[stage], 0]))
    s.write(0xe65, bytes(22))
    sp = saved['S']
    s.write(0x100 + sp - 1, bytes([0xf2, 0x83]))  # RTS pulls low then high, +1
    s.reg('S', sp - 2)
    s.reg('A', stage)
    s.reg('PC', 0x8244)
    st = run_to_hook(s, max_polls=20000)
    cpu = s.cpu()
    assert int(cpu['S'], 16) == sp, (cpu, sp)
    for k in ('X', 'Y', 'P'):
        s.reg(k, saved[k])
    return cpu
