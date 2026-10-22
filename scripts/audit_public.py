#!/usr/bin/env python3
"""Audit Git-visible publication files; never traverse ignored ROM/build data."""
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = {'README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'CHANGELOG.md', 'CREDITS.md',
       'LICENSE', 'VERSION', '.gitignore', '.gitattributes'}
DIRECTORIES = {'docs', 'src', 'scripts', 'tests', 'patches', 'release', 'research', '.github'}
FORBIDDEN = {'.pce', '.nes', '.sms', '.rom', '.bin', '.state', '.sav', '.vram', '.pal',
             '.png', '.jpg', '.zip', '.sym', '.lst', '.pyc'}
# The only images allowed: the how-to screenshots in docs/OPTIONS.md, made by
# scripts/guide_screenshots.py. Captures and frames stay out of the repository.
GUIDE_IMAGES = {f'docs/images/options/{name}.png' for name in
                ('title-languages', 'menu', 'menu-stage', 'menu-parallax', 'menu-no-damage')}
GUIDE_IMAGE_LIMIT = 100 * 1024


def public_paths():
    run = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                         cwd=ROOT, capture_output=True, check=True)
    return sorted(set(p for p in run.stdout.decode().split('\0') if p))


def audit():
    paths = public_paths()
    problems = []
    for name in paths:
        p = PurePosixPath(name)
        file = ROOT / name
        if (len(p.parts) == 1 and name not in TOP) or (len(p.parts) > 1 and p.parts[0] not in DIRECTORIES):
            problems.append(f'Unexpected publication path: {name}')
        if file.is_symlink() or not file.is_file():
            problems.append(f'Not a regular file: {name}')
            continue
        if name in GUIDE_IMAGES:
            if file.stat().st_size > GUIDE_IMAGE_LIMIT:
                problems.append(f'Guide screenshot too large: {name}')
            continue
        if p.suffix.lower() in FORBIDDEN or any(part in {'__pycache__', '.git', '.env'} for part in p.parts):
            problems.append(f'Excluded artifact: {name}')
        if file.stat().st_size > 2 * 1024 * 1024:
            problems.append(f'Unexpectedly large publication file: {name}')
        if p.suffix == '.bps' and p.parts[0] != 'patches':
            problems.append(f'Patch outside release patch directory: {name}')
        if p.suffix != '.bps':
            try:
                text = file.read_text()
                if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
                    problems.append(f'Private key marker: {name}')
            except UnicodeError:
                problems.append(f'Unexpected binary file: {name}')
    if problems:
        raise ValueError('\n'.join(problems))
    return paths


if __name__ == '__main__':
    paths = audit()
    print(f'Publication file audit passed: {len(paths)} files; no ROMs, states, captures or tool binaries.')
    print('This file audit does not replace license/provenance review.')
