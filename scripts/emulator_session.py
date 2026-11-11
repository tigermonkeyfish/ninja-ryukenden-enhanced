#!/usr/bin/env python3
"""Headless Geargrafx client. Set BINARY before opening a session.

Backup RAM (BRAM, bank $F7) is controlled per session and never touches a
file (docs/pc-engine/EMULATOR.md, "Backup RAM"):

- `load_media` gives a machine WITHOUT backup RAM: the headless frontend
  never applies the desktop setting "Force Backup RAM", so a HuCard's bank
  $F7 is unmapped and reads $FF. `call` checks that after every load.
- `power_on(rom, bram=image)` gives a machine WITH backup RAM holding the
  2,048-byte `image`, from the first instruction after reset.
- A session whose machine has backup RAM is ended with SIGKILL, because a
  normal exit writes `<rom name>.sav` beside the emulator binary; `__exit__`
  also removes such a file if one appeared anyway and reports it.
"""
import json
import os
from pathlib import Path
import queue
import shutil
import signal
import struct
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('NG_EMULATOR') or shutil.which('geargrafx') or 'geargrafx').resolve()
BRAM_SIZE = 0x800
# What Geargrafx 78fc3d7 holds in its backup RAM after a reset, whether or
# not the machine has any (src/memory.cpp, Memory::Reset).
BRAM_RESET = b'HUBM\x00\xa0\x10\x80' + bytes(BRAM_SIZE - 8)


def state_bram_offset(state):
    """Where a Geargrafx 78fc3d7 save state keeps backup RAM (2,048 bytes,
    then one byte: the machine has backup RAM). Layout read in the source
    (GeargrafxCore::SaveState, Memory::SaveState): CD flag, u64 master clock,
    8 MPRs, 32 KiB work RAM, u32 size + CD RAM, u32 size + card RAM, the card
    RAM's first and last bank. Refuses a state that does not fit."""
    at = 1 + 8 + 8 + 0x8000
    for _ in range(2):
        at += 4 + struct.unpack_from('<I', state, at)[0]
    at += 2
    if at + BRAM_SIZE + 1 > len(state) or state[at + BRAM_SIZE] > 1:
        raise RuntimeError('Unrecognised save state layout: backup RAM not found')
    return at


class Emulator:
    """Own one headless process; sequential requests with bounded waits."""

    def __enter__(self):
        self.started = time.time()
        logs = ROOT / 'local/logs'
        logs.mkdir(parents=True, exist_ok=True)
        self.log = (logs / 'emulator-stderr.log').open('w')
        self.counter = 0
        self.messages = queue.Queue()
        try:
            self.proc = subprocess.Popen(
                [str(BINARY), '--headless', '--mcp-stdio', '--portable'],
                cwd=BINARY.parent, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=self.log, text=True, bufsize=1,
                env=dict(os.environ, SDL_AUDIODRIVER='dummy', NG_DEBUGGER_FAST='1'))
            self.reader = threading.Thread(target=self._read, daemon=True)
            self.reader.start()
            self.server = self.rpc('initialize', {
                'protocolVersion': '2025-11-25', 'capabilities': {},
                'clientInfo': {'name': 'ninja-cutscene-audit', 'version': '0.1'}}).get('serverInfo', {})
            self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
            self.tools = self.rpc('tools/list', {})
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def _read(self):
        for line in self.proc.stdout:
            try:
                self.messages.put(json.loads(line))
            except json.JSONDecodeError:
                continue
        self.messages.put(None)

    def send(self, message):
        self.proc.stdin.write(json.dumps(message) + '\n')
        self.proc.stdin.flush()

    def rpc(self, method, params, timeout=30):
        self.counter += 1
        request_id = self.counter
        self.send({'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(method)
            try:
                message = self.messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError(method) from exc
            if message is None:
                raise RuntimeError('Emulator exited; inspect local/logs/emulator-stderr.log')
            if message.get('id') == request_id:
                if 'error' in message:
                    raise RuntimeError(message['error'])
                return message['result']

    def call(self, name, arguments=None):
        result = self.rpc('tools/call', {'name': name, 'arguments': arguments or {}})
        if result.get('isError'):
            raise RuntimeError(result)
        if name == 'load_media' and self.backup_ram_area() is not None:
            raise RuntimeError('load_media gave a machine with backup RAM; this harness expects '
                               'none (headless Geargrafx 78fc3d7). Use power_on(rom, bram=...)')
        return result

    def backup_ram_area(self):
        """The debugger's memory area for backup RAM; None when the machine
        has none (bank $F7 unmapped)."""
        areas = json.loads(self.call('list_memory_areas')['content'][0]['text'])['areas']
        return next((area['id'] for area in areas if area['name'] == 'BRAM'), None)

    def backup_ram(self):
        """The machine's backup RAM (2,048 bytes), or None when it has none."""
        area = self.backup_ram_area()
        if area is None:
            return None
        reply = self.call('read_memory', {'area': area, 'offset': '0', 'size': BRAM_SIZE})
        return bytes.fromhex(json.loads(reply['content'][0]['text'])['data'])

    def power_on(self, rom, bram=None):
        """Load `rom` and stop at its reset vector, before the first
        instruction. bram=None: no backup RAM (a console without CD hardware
        or save memory: bank $F7 reads $FF and ignores writes). Otherwise
        backup RAM is present and holds `bram` (2,048 bytes). It is always
        unlocked: this emulator build does not decode $1807/$1803 for a
        HuCard (the test-only build of research/tools/bram-save/
        locktest_patch.py does, when NG_BRAM_MODEL is set: there the memory
        starts locked). Nothing is read from or written to a save file."""
        self.call('load_media', {'file_path': str(Path(rom).resolve())})
        self.call('debug_pause')
        if bram is None:
            return
        if len(bram) != BRAM_SIZE:
            raise ValueError(f'A backup RAM image is {BRAM_SIZE} bytes, got {len(bram)}')
        # The only switch this build offers a headless session is the save
        # state, which carries backup RAM and whether the machine has it.
        with tempfile.TemporaryDirectory(prefix='bram-') as folder:
            path = Path(folder) / 'reset.state'
            self.call('save_state_file', {'file_path': str(path)})
            state = bytearray(path.read_bytes())
            at = state_bram_offset(state)
            if (state[1:9] != bytes(8) or state[at + BRAM_SIZE] != 0
                    or bytes(state[at:at + BRAM_SIZE]) != BRAM_RESET):
                raise RuntimeError('The machine is not at reset without backup RAM; refusing to patch its state')
            state[at:at + BRAM_SIZE] = bram
            state[at + BRAM_SIZE] = 1
            path.write_bytes(state)
            self.call('load_state_file', {'file_path': str(path)})
        if self.backup_ram() != bytes(bram):
            raise RuntimeError('Backup RAM was not installed')

    def __exit__(self, *_):
        if hasattr(self, 'proc'):
            if self.proc.poll() is None:
                # A machine with backup RAM (power_on with an image, or a
                # loaded state that carries it) would write a .sav on a normal
                # exit: kill it instead. SIGKILL also when it cannot be asked.
                try:
                    kill = self.backup_ram_area() is not None
                except Exception:
                    kill = True
                self.proc.send_signal(signal.SIGKILL if kill else signal.SIGTERM)
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
            if hasattr(self, 'reader'):
                self.reader.join(timeout=1)
            self.proc.stdin.close()
            self.proc.stdout.close()
            # Never leave a save file behind (the emulator writes it beside
            # its binary in portable mode).
            stray = [path for path in BINARY.parent.glob('*.sav') if path.stat().st_mtime >= self.started - 1]
            for path in stray:
                path.unlink()
            if stray:
                self.log.write(f'Removed save files written by this session: {[p.name for p in stray]}\n')
        self.log.close()
