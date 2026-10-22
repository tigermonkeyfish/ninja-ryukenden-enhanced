#!/usr/bin/env python3
"""Capture native English cinemas with Geargrafx's headless MCP debugger.

Run reference first, then candidate with the reference boot state. Gameplay
completion is accelerated; cinematic scripts run normally. See
docs/CUTSCENE-AUDIT.md for the scope and emulator requirements.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import struct
import time
import zlib

import emulator_session as emulator

# Fingerprint of the native English title screen, used only to leave the intro
# attract loop AFTER its cinematic has run. No copyrighted image is embedded.
TITLE_SHA256 = '0f7d3cca14687874168f17e547c076e42f30c41435646e0faf7aea9c90a0f9b9'
END_SHA256 = '16c6b883b9cdcfdf5c193737ce21f0ca4d8b78fe95429aa7a9866390696c50ac'


def unpack(result):
    texts = [item['text'] for item in result.get('content', []) if item['type'] == 'text']
    if len(texts) != 1:
        raise ValueError(f'Expected one JSON tool result, got {texts!r}')
    return json.loads(texts[0])


def crc_payload(rom):
    """Geargrafx states fingerprint cartridge bytes, excluding a copier header."""
    if len(rom) % 8192 == 512:
        rom = rom[512:]
    return zlib.crc32(rom)


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'frames.jsonl').exists():
        raise ValueError('Choose a new output directory; existing evidence is preserved')
    emulator.BINARY = args.emulator.resolve()
    emulator.ROOT = out
    rom = args.rom.resolve()
    events, movies = [], {}
    began = time.monotonic()
    with emulator.Emulator() as session:
        def call(name, arguments=None):
            return unpack(session.call(name, arguments))

        def step(frames=1):
            return call('debug_step_frame', {'frames': frames, 'mode': 'sync'})

        def read(offset, size):
            return bytes.fromhex(call('read_memory', {
                'area': 0, 'offset': f'{offset:04x}', 'size': size})['data'])

        def button(action):
            call('controller_button', {'player': 1, 'button': 'run', 'action': action})

        call('load_media', {'file_path': str(rom)})
        call('debug_pause')
        boot = out / 'boot.state'
        if args.seed:
            state = bytearray(args.seed.read_bytes())
            # Pinned Geargrafx format: do not silently transplant other versions.
            reference = json.loads(args.seed.with_suffix('.json').read_text())
            if (len(state) != reference['state_size'] or
                    hashlib.sha256(state).hexdigest() != reference['state_sha256'] or
                    struct.unpack_from('<I', state, len(state) - 48)[0] != reference['cartridge_crc32']):
                raise ValueError('Reference state fingerprint/trailer mismatch')
            struct.pack_into('<I', state, len(state) - 48, crc_payload(rom.read_bytes()))
            boot.write_bytes(state)
            call('load_state_file', {'file_path': str(boot)})
        else:
            call('set_breakpoint', {'address': '8022', 'memory_area': 'rom', 'execute': True})
            try:
                step(120)
            except RuntimeError as exc:
                if 'Synchronous frame step interrupted' not in str(exc):
                    raise
            status = call('debug_get_status')
            if not (status['paused'] and status['pc'] == '8022'):
                raise RuntimeError(f'Native cinema initialization not reached: {status}')
            call('remove_breakpoint', {'address': '8022', 'memory_area': 'rom'})
            result = call('write_memory', {'area': 0, 'offset': '1227', 'bytes': '01'})
            assert result['bytes_written'] == 1, result
            call('save_state_file', {'file_path': str(boot)})
            state = boot.read_bytes()
            reference = {
                'state_size': len(state), 'state_sha256': hashlib.sha256(state).hexdigest(),
                'cartridge_crc32': crc_payload(rom.read_bytes()),
            }
            if struct.unpack_from('<I', state, len(state) - 48)[0] != reference['cartridge_crc32']:
                raise ValueError('Unexpected Geargrafx state format')
            boot.with_suffix('.json').write_text(json.dumps(reference, indent=2) + '\n')

        prior, frame, release_at = None, 0, None
        terminal_frames = 0
        with (out / 'frames.jsonl').open('w') as log:
            for total in range(args.max_frames):
                state = read(0x240, 9)
                kind, scene = state[:2]
                key = (kind, scene)
                if key != prior:
                    event = {'kind': kind, 'id': scene, 'cursor': state[7],
                             'after_audit_frames': total}
                    events.append(event)
                    print(event, flush=True)
                    if kind == 2 or (14 in movies and key == (1, 0)):
                        break
                    frame, prior = 0, key
                if kind == 0:
                    step(120)
                    call('debug_run_to_cursor', {'address': '8457'})
                    status = call('debug_get_status')
                    if not (status['paused'] and status['pc'] == '8457'):
                        raise RuntimeError(f'Gameplay completion boundary not reached: {status}')
                    call('write_huc6280_register', {'name': 'PC', 'value': '8478'})
                    for _ in range(1200):
                        step()
                        if tuple(read(0x240, 2)) != key:
                            break
                    else:
                        raise RuntimeError(f'Native exit did not advance: {key}')
                    continue
                if kind != 1:
                    raise RuntimeError(f'Unknown native master kind: {state.hex()}')
                if release_at is not None and total >= release_at:
                    button('release')
                    release_at = None
                if scene == 1 and frame == 180:
                    button('press')
                    release_at = total + 2
                step()
                shot = session.call('get_screenshot')
                png = base64.b64decode(next(item['data'] for item in shot['content']
                                            if item['type'] == 'image'))
                digest = hashlib.sha256(png).hexdigest()
                if scene == 0 and frame > 2000 and digest == TITLE_SHA256 and release_at is None:
                    button('press')
                    release_at = total + 2
                path = out / f'{digest}.png'
                if not path.exists():
                    path.write_bytes(png)
                log.write(json.dumps({'scene': scene, 'frame': frame, 'png_sha256': digest}) + '\n')
                movies[scene] = movies.get(scene, 0) + 1
                frame += 1
                terminal_frames = terminal_frames + 1 if scene == 14 and digest == END_SHA256 else 0
                if terminal_frames >= 600:
                    # The final screen waits indefinitely; ten seconds of the
                    # verified terminal image completes the cinematic audit.
                    break
                if frame % 1000 == 0:
                    log.flush()
                    print(f'Scene {scene}, {frame} frames; {time.monotonic() - began:.0f}s', flush=True)
            else:
                raise RuntimeError('Frame budget exhausted before native end sequence')
        if set(movies) != set(range(15)):
            raise RuntimeError(f'Incomplete cinema coverage: {sorted(movies)}')
        report = {
            'rom_sha256': hashlib.sha256(rom.read_bytes()).hexdigest(),
            'movies': movies, 'events': events, 'elapsed_seconds': time.monotonic() - began,
            'terminal_end_frames': terminal_frames,
            'interventions': [
                'Native English selected at the first cinema initialization, before graphics load',
                'Candidate starts from reference CPU/RAM/VRAM state with only cartridge CRC retargeted'
                if args.seed else 'Reference boot state generated from original ROM',
                'Gameplay rendered for 120 frames, then PC moved from 8457 to native completion 8478',
                'Run used only to leave intro attract loop and title; story scripts play without input',
            ],
        }
        (out / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--emulator', type=Path, required=True)
    parser.add_argument('--rom', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=Path, help='Reference boot.state (and adjacent boot.json)')
    parser.add_argument('--max-frames', type=int, default=400000)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
