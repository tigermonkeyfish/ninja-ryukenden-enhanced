#!/usr/bin/env python3
"""Test exported player/source archives with a private ROM and external pceas."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from bps import apply
from project import ROOT, checked, load_manifest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--rom', type=Path, required=True)
parser.add_argument('--assembler', type=Path, required=True)
args = parser.parse_args()
manifest = load_manifest()
source = checked(args.rom.read_bytes(), manifest['source'], 'Original ROM')

def run(root, *command, success=True):
    result = subprocess.run([sys.executable, *command], cwd=root, capture_output=True, text=True)
    if (result.returncode == 0) != success:
        raise RuntimeError(result.stdout + '\n' + result.stderr)
    return result

with tempfile.TemporaryDirectory(prefix='ng-enhanced-export-') as temp:
    temp = Path(temp)
    for kind in ['patch', 'source']:
        directory = temp / f'{kind} tree'
        with zipfile.ZipFile(ROOT / f'dist/ninja-ryukenden-enhanced-v{manifest["version"]}-{kind}.zip') as z:
            assert not any(Path(n).suffix in {'.pce', '.state', '.vram', '.bin'} for n in z.namelist())
            z.extractall(directory)
        run(directory, 'scripts/project.py', 'apply', '--rom', str(args.rom.resolve()))
        checked((directory / f'dist/Ninja Ryukenden - Enhanced v{manifest["version"]}.pce').read_bytes(), manifest['target'], kind)
    directory = temp / 'source tree'
    run(directory, '-m', 'unittest', 'discover', '-s', 'tests', '-v')
    run(directory, 'scripts/project.py', 'build', '--rom', str(args.rom.resolve()),
        '--assembler', str(args.assembler.resolve()), '--verify-release')
    checked((directory / 'dist/Ninja Ryukenden - development.pce').read_bytes(), manifest['target'], 'Clean export source build')

    # Prove that edits are assembled rather than silently ignored behind the BPS.
    english = directory / 'src/english/main.asm'
    text = english.read_text()
    assert text.count(' lda #1') == 1
    english.write_text(text.replace(' lda #1', ' lda #0'))
    changed_patch = directory / 'dist/modified.bps'
    run(directory, 'scripts/project.py', 'build', '--rom', str(args.rom.resolve()),
        '--assembler', str(args.assembler.resolve()), '--bps-output', str(changed_patch))
    altered = (directory / 'dist/Ninja Ryukenden - development.pce').read_bytes()
    pristine = (directory / f'dist/Ninja Ryukenden - Enhanced v{manifest["version"]}.pce').read_bytes()
    assert [i for i, (a,b) in enumerate(zip(pristine, altered)) if a != b] == [0x1fe7]
    assert altered[0x1fe7] == 0 and apply(source, changed_patch.read_bytes()) == altered
    run(directory, 'scripts/project.py', 'verify', str(directory / 'dist/Ninja Ryukenden - development.pce'), success=False)

    # The headerless original is a supported input with its own patch.
    headerless = temp / 'headerless.pce'
    headerless.write_bytes(source[512:])
    run(directory, 'scripts/project.py', 'apply', '--rom', str(headerless), '--output', str(temp / 'from-headerless.pce'))
    checked((temp / 'from-headerless.pce').read_bytes(), manifest['target'], 'Headerless apply')
    # Any other dump is rejected, not normalized.
    bad = temp / 'wrong.pce'
    bad.write_bytes(source[:0x1000] + bytes([source[0x1000] ^ 1]) + source[0x1001:])
    failure = run(directory, 'scripts/project.py', 'apply', '--rom', str(bad), success=False)
    assert 'Original ROM' in failure.stderr
    protected = temp / 'protected.pce'
    protected.write_bytes(source)
    run(directory, 'scripts/project.py', 'apply', '--rom', str(protected), '--output', str(protected), success=False)
    assert protected.read_bytes() == source

report = {
    'version': manifest['version'], 'rom_sha256': manifest['target']['sha256'],
    'patch_sha256': manifest['patch']['sha256'],
    'runtime_inputs_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted((ROOT / 'src').rglob('*')) if p.is_file()},
    'player_archive_apply_passed': True, 'source_archive_apply_passed': True,
    'clean_export_all_20_modules_reproduce_release': True,
    'edited_source_changes_expected_rom_byte': True,
    'development_patch_roundtrip_passed': True,
    'headerless_apply_passed': True, 'wrong_rom_rejected': True, 'source_overwrite_rejected': True,
    'rom_free_tests_passed': True,
    'emulator_rerun_needed_for_identical_rom': False,
    'physical_hardware_tested_this_revision': manifest.get('hardware_validation', {}).get('exact_release_bytes_tested', False),
    'hardware_validation': manifest.get('hardware_validation'),
}
(ROOT / f'dist/export-validation-v{manifest["version"]}.json').write_text(json.dumps(report, indent=2)+'\n')
print('Clean player/source exports, exact runtime rebuild, source edit, development BPS and input protections passed.')
