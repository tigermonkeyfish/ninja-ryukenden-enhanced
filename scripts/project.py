#!/usr/bin/env python3
"""Portable release application and runtime-source build (Python stdlib only)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from bps import apply, create

ROOT = Path(__file__).resolve().parents[1]
# Enhanced ROM size: the original's 512 KiB plus banks $40-$7F for the modules.
ROM_SIZE = 0x100000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_manifest():
    return json.loads((ROOT / 'release/current.json').read_text())


def checked(data, spec, label):
    if len(data) != spec['size'] or digest(data) != spec['sha256']:
        raise ValueError(f'{label} mismatch: expected {spec["size"]} bytes, SHA256 '
                         f'{spec["sha256"]}; got {len(data)} bytes, {digest(data)}')
    return data


def identify(source, manifest):
    """(game data without a copier header, header length, matching patch spec)
    for an original ROM in either format: headered (512-byte copier header)
    or headerless."""
    formats = [(manifest['source'], manifest['patch'])]
    if 'headerless' in manifest:
        formats.append((manifest['headerless']['source'], manifest['headerless']['patch']))
    for spec, patch in formats:
        if len(source) == spec['size'] and digest(source) == spec['sha256']:
            header = spec.get('header_bytes', 0)
            return source[header:], header, patch
    expected = '; or '.join(f'{s["size"]} bytes, SHA256 {s["sha256"]}' for s, _ in formats)
    raise ValueError(f'Original ROM mismatch: expected {expected}; got {len(source)} bytes, {digest(source)}')


def original_image(source, manifest):
    """The original game without its header, padded with $FF to ROM_SIZE."""
    game = identify(source, manifest)[0]
    return game + b'\xff' * (ROM_SIZE - len(game))


def baseline(source, manifest):
    """The current release, from the original ROM and its matching patch."""
    patch_spec = identify(source, manifest)[2]
    patch = (ROOT / patch_spec['path']).read_bytes()
    if digest(patch) != patch_spec['sha256']:
        raise ValueError('Release patch SHA256 mismatch')
    return checked(apply(source, patch), manifest['target'], 'Patched ROM')


def write_output(path, data, protected=()):
    path = path.resolve()
    if path in {p.resolve() for p in protected}:
        raise ValueError('Output must not overwrite an input or a release patch')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f'{path}\n  {len(data)} bytes; SHA256 {digest(data)}')


def build_runtime(base, assembler, directory, original):
    """Assemble each runtime module over `base` (the padded original game).
    A module's prepare step generates its data from the original ROM
    (headerless image `original`)."""
    modules = json.loads((ROOT / 'src/modules.json').read_text())
    result = bytearray(base)
    occupied = set()
    for module in modules:
        work = directory / module['name']
        shutil.copytree((ROOT / module['source']).parent, work)
        if 'prepare' in module:
            from asset_transforms import prepare
            prepare(module['prepare'], work, original)
        overlay = work / 'overlay.pce'
        if module['name'] == 'notice':
            from notice_assets import generate
            generate(work, (ROOT / 'VERSION').read_text().strip())
        command = [assembler, '--raw', '--pad', '-I', str(work), '-o', str(overlay), str(work / 'main.asm')]
        run = subprocess.run(command, cwd=work, capture_output=True, text=True)
        if run.returncode:
            raise RuntimeError(f'Assembly failed: {module["name"]}\n{run.stdout}\n{run.stderr}')
        raw = overlay.read_bytes()
        allowed = set()
        for lo, hi in module['ranges']:
            allowed.update(range(lo, hi))
        outside = next((i for i, b in enumerate(raw) if b != 0xff and i not in allowed), None)
        if outside is not None:
            raise ValueError(f'Module {module["name"]} emits bytes outside its reserved ranges at {outside:06x}')
        for lo, hi in module['ranges']:
            if not 0 <= lo < hi <= len(base) or len(raw) < hi:
                raise ValueError(f'Invalid or undersized module range: {module["name"]}: {lo:x}..{hi:x}')
            region = set(range(lo, hi))
            if region & occupied:
                raise ValueError(f'Overlapping module ranges: {module["name"]}')
            occupied.update(region)
            result[lo:hi] = raw[lo:hi]
        print(f'Assembled {module["name"]}')
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['apply', 'build']:
        p = sub.add_parser(name)
        p.add_argument('--rom', type=Path, required=True, help='Original Japanese ROM, headered or headerless')
        p.add_argument('--output', type=Path)
        if name == 'build':
            p.add_argument('--assembler', default=shutil.which('pceas'), help='Path to pceas')
            p.add_argument('--verify-release', action='store_true', help='Require exact current release bytes')
            p.add_argument('--bps-output', type=Path, help='Also write a cumulative development patch')
    p = sub.add_parser('verify')
    p.add_argument('rom', type=Path, help='Already patched current-release ROM')
    args = parser.parse_args()
    manifest = load_manifest()
    if args.command == 'verify':
        checked(args.rom.read_bytes(), manifest['target'], 'Release ROM')
        print(f'Exact v{manifest["version"]} game bytes verified.')
        return
    source = args.rom.read_bytes()
    # A source build starts from the original game alone; apply uses the
    # current release patch.
    rom = original_image(source, manifest) if args.command == 'build' else baseline(source, manifest)
    protected = [args.rom, *ROOT.glob('patches/*.bps')]
    if args.command == 'build':
        if not args.assembler:
            raise ValueError('pceas is required for source builds; use --assembler PATH or the apply command')
        assembler = str(Path(args.assembler).resolve())
        (ROOT / 'build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='runtime-', dir=ROOT / 'build') as temp:
            rom = build_runtime(rom, assembler, Path(temp), identify(source, manifest)[0])
        if args.verify_release:
            checked(rom, manifest['target'], 'Reassembled release ROM')
        if args.bps_output:
            patch = create(source, rom, header=identify(source, manifest)[1],
                           metadata=b'Ninja Ryukenden Enhanced development build; see associated source revision.')
            if apply(source, patch) != rom:
                raise ValueError('Development BPS round-trip failed')
            write_output(args.bps_output, patch, protected + ([args.output] if args.output else []))
    default = f'Ninja Ryukenden - Enhanced v{manifest["version"]}.pce' if args.command == 'apply' else 'Ninja Ryukenden - development.pce'
    output = args.output or ROOT / 'dist' / default
    write_output(output, rom, protected + ([args.bps_output] if args.command == 'build' and args.bps_output else []))
    if digest(rom) == manifest['target']['sha256']:
        print(f'Matches v{manifest["version"]} exactly.')
    else:
        print('Modified development build: emulator/hardware validation required before release.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, RuntimeError) as error:
        print(f'Error: {error}', file=sys.stderr)
        sys.exit(1)
