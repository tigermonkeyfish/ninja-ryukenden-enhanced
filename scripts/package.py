#!/usr/bin/env python3
"""Create local, patch-only player and source archives. Does not publish."""
import hashlib
import json
from pathlib import Path
import zipfile
from audit_public import ROOT, audit
from project import load_manifest


def archive(path, files, replacements=None):
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):
            # Fixed timestamps keep packaging deterministic.
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 21, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            z.writestr(entry, (ROOT / (replacements or {}).get(name, name)).read_bytes())


paths = audit()
manifest = load_manifest()
if (ROOT / 'VERSION').read_text().strip() != manifest['version']:
    raise SystemExit('Development version: freeze new release metadata before packaging. '
                     'Existing release archives were not changed.')
dist = ROOT / 'dist'
dist.mkdir(exist_ok=True)
# The player package: both patches (headered and headerless original), their
# instructions, the optional Python patcher and the release record.
players = ['README.md', 'release/HEADERLESS-README.md', 'CHANGELOG.md', 'CREDITS.md', 'LICENSE',
           'docs/LICENSING.md', 'release/current.json', manifest['patch']['path'],
           manifest['headerless']['patch']['path'], 'scripts/project.py', 'scripts/bps.py', 'VERSION']
version = manifest['version']
archives = [dist / f'ninja-ryukenden-enhanced-v{version}-patch.zip',
            dist / f'ninja-ryukenden-enhanced-v{version}-source.zip']
archive(archives[0], set(players), {'README.md':'release/PLAYER-README.md'})
archive(archives[1], paths)
hashes = []
for path in archives:
    hashes.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}')
(dist / f'SHA256SUMS-v{version}.txt').write_text('\n'.join(hashes) + '\n')
print('\n'.join(str(p) for p in archives))
print('Local packages only. Complete docs/PUBLISHING.md before making a public release.')
