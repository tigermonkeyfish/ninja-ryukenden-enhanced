#!/usr/bin/env python3
"""Headless Geargrafx client. Set BINARY before opening a session."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get('NG_EMULATOR') or shutil.which('geargrafx') or 'geargrafx').resolve()


class Emulator:
    """Own one headless process; sequential requests with bounded waits."""

    def __enter__(self):
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
        return result

    def __exit__(self, *_):
        if hasattr(self, 'proc'):
            if self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait()
            if hasattr(self, 'reader'):
                self.reader.join(timeout=1)
            self.proc.stdin.close()
            self.proc.stdout.close()
        self.log.close()
