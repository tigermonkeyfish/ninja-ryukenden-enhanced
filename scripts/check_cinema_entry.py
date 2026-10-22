#!/usr/bin/env python3
"""Live-emulator reset check with private ROMs and a generated reference state."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from audit_cutscenes import crc_payload, unpack
import emulator_session as emulator


def inspect_entry(rom, seed, label, output):
    with emulator.Emulator() as session:
        def call(name, arguments=None):
            return unpack(session.call(name, arguments))

        def read(area, offset, size):
            return bytes.fromhex(call('read_memory', {
                'area': area, 'offset': f'{offset:04x}', 'size': size})['data'])

        call('load_media', {'file_path': str(rom.resolve())})
        call('debug_pause')
        state = bytearray(seed)
        struct.pack_into('<I', state, len(state) - 48, crc_payload(rom.read_bytes()))
        path = output.resolve() / f'contract-{label}.state'
        path.write_bytes(state)
        call('load_state_file', {'file_path': str(path)})
        dirty = bytes([0xa5]) * 512
        result = call('write_memory', {'area': 4, 'offset': '7200', 'bytes': dirty.hex(' ')})
        assert result['bytes_written'] == 512, result
        call('set_breakpoint', {'address': '8030', 'memory_area': 'rom', 'execute': True})
        try:
            call('debug_step_frame', {'frames': 1, 'mode': 'sync'})
        except RuntimeError as exc:
            if 'Synchronous frame step interrupted' not in str(exc):
                raise
        assert call('debug_get_status')['pc'] == '8030'
        return {'cpu': call('get_huc6280_status'), 'vdc': call('get_huc6270_registers'),
                'ram': read(0, 0, 8192), 'vram': read(4, 0, 65536)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['emulator', 'original', 'candidate', 'seed', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    emulator.BINARY = args.emulator.resolve()
    emulator.ROOT = args.output.resolve()
    seed = args.seed.read_bytes()
    metadata = json.loads(args.seed.with_suffix('.json').read_text())
    assert len(seed) == metadata['state_size']
    assert hashlib.sha256(seed).hexdigest() == metadata['state_sha256']
    assert struct.unpack_from('<I', seed, len(seed) - 48)[0] == metadata['cartridge_crc32']
    assert metadata['cartridge_crc32'] == crc_payload(args.original.read_bytes())
    original = inspect_entry(args.original, seed, 'original', args.output)
    candidate = inspect_entry(args.candidate, seed, 'candidate', args.output)
    for key in ['A', 'X', 'Y', 'P', 'PC', 'SP', 'MPR']:
        assert original['cpu'][key] == candidate['cpu'][key], key
    vram_changes = [i for i, (a, b) in enumerate(zip(original['vram'], candidate['vram'])) if a != b]
    assert vram_changes == list(range(0xe400, 0xe600)), vram_changes
    assert candidate['vram'][0xe400:0xe600] == bytes(512)
    ram_changes = [i for i, (a, b) in enumerate(zip(original['ram'], candidate['ram'])) if a != b]
    # Extra pushes may leave different bytes below the restored stack pointer.
    assert all(0x104 <= i <= 0x1ff for i in ram_changes), ram_changes
    assert original['ram'][0x100:0x140] == candidate['ram'][0x100:0x140]
    original_vdc = dict(original['vdc']['registers'])
    candidate_vdc = dict(candidate['vdc']['registers'])
    assert original_vdc['AR'] == candidate_vdc['AR']
    report = {
        'cpu_registers_preserved': True, 'vdc_selector_preserved': True,
        'vram_only_changed_bytes': [0xe400, 0xe600], 'ram_changed_offsets': ram_changes,
        'vdc_reference': original['vdc'], 'vdc_candidate': candidate['vdc'],
    }
    (args.output / 'hook-contract.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: registers, banks, stack margin and exact VRAM cleanup')


if __name__ == '__main__':
    main()
