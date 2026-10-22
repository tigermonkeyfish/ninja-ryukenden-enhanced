# Publication checklist

The repository `tigermonkeyfish/ninja-ryukenden-enhanced` publishes release
1.09. Local preparation does not authorize a push or a release upload; the
maintainer decides both.

Suggested GitHub About description:

> Ninja Gaiden TurboGrafx-16 (Japan) / Ninja Ryukenden Enhanced for PC Engine (PCE) / TG16: smooth parallax, Level Select / Stage Select, No Damage and English by default. BPS patches.

Suggested repository topics: `ninja-gaiden`, `ninja-ryukenden`, `pc-engine`,
`pce`, `turbografx-16`, `tg16`, `parallax`, `level-select`, `stage-select`,
`no-damage`, `romhack`, `bps-patch`.

The current identity is `release/current.json`. Release files:

- Patches: `patches/ninja-ryukenden-enhanced-v1.09.bps` and
  `patches/ninja-ryukenden-enhanced-v1.09-headerless.bps` (also the two
  downloads on the itch.io page, where a tip is optional).
- `dist/ninja-ryukenden-enhanced-v1.09-patch.zip` (both patches, their
  instructions, the optional Python patcher), the optional source ZIP and
  `dist/SHA256SUMS-v1.09.txt`, made by `scripts/package.py`.
- The playable ROM stays local.

Before publishing a release:

- [ ] Tests, file audit and `build --verify-release` pass from a clean tree.
- [ ] Both patches reproduce the target from the two original formats.
- [ ] The release notes keep the scope of the hardware reports (Duo-RX /
      Turbo EverDrive PRO, stages and settings not specified) and do not
      claim that CI runs the original game; CI uses synthetic tooling tests.
- [ ] Credits and third-party/derived-material scope are reviewed
      ([LICENSING.md](LICENSING.md)).
- [ ] Tag `v<VERSION>` and push when the maintainer authorizes it; upload the
      patch package and checksums, never a playable ROM.

The optional source archive contains Git-visible source and documentation,
not ignored local artifacts. Inspect its file list before release. The file
audit is an accidental-artifact check, not a legal determination.

After changing the license or release notes, regenerate the archives:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/audit_public.py
python3 scripts/package.py
```

Generated archives and the checksum list are in `dist/` and remain untracked.
