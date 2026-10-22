# Reproducing and modifying v1.09

## Apply the release

Only Python 3.10+ and one of the original ROMs listed in the README
(headered or headerless) are needed:

```sh
python3 scripts/project.py apply --rom "/path/to/original.pce"
python3 scripts/project.py verify "dist/Ninja Ryukenden - Enhanced v1.09.pce"
```

The script identifies the original's format, picks the matching patch and
checks source SHA-256, source size, BPS checksums, patch SHA-256, output size
and output SHA-256. A different dump is rejected rather than silently
normalized. Never provide a previously patched ROM as input.

## Build the editable runtime

Install/build `pceas` from [pce-devel/huc](https://github.com/pce-devel/huc).
The version used for this release is pinned in `release/current.json`:
`54f5c73606c1e7142e8095c727cab2767e2b3cb3`. The assembler is an external
dependency; its source and binaries are not included in this repository.

```sh
python3 scripts/project.py build --rom "/path/to/original.pce" \
  --assembler "/path/to/pceas" --verify-release
```

This reproduces the 1.09 ROM hash in `release/current.json` exactly, from
either original format. After `VERSION` changes for new work the build is a
different ROM, so the check fails by design.
The default build filename remains `dist/Ninja Ryukenden - development.pce`;
`--verify-release` verifies its contents. `apply` writes the versioned release
filename. For intentional changes, omit `--verify-release` and use a separate
output as shown below. The build needs no release ROM,
emulator, captures, save states, network connection, or research workspace.

The build reads nothing from an earlier release. It starts from the original
ROM (any header removed, padded with `$FF` to 1 MiB) and writes the `src/`
modules over it:

1. Every module is assembled; only its declared ranges are written.
   Overlapping ranges and non-padding output outside reserved ranges are
   rejected. Outside the module ranges the ROM is the original game, byte
   for byte.
2. A module's data is either source in `src/` or generated at build time
   from the original ROM by the module's `prepare` step.

`src/modules.json` records each module's source, ROM ranges and prepare
step; no game graphics or memory dumps are distributed.

Backdrops are regenerated from the original ROM. Each parallax module names
a `prepare` step (`scripts/asset_transforms.py`) that runs
`scripts/native_backdrops.py` in the temporary build directory. It decodes
the original game's backdrop tiles, maps and palettes from the original ROM
(`scripts/native_gfx.py`, pinned by SHA-256 of what they decode to), builds
the loop of original columns listed in `native_gfx.LOOPS`, and writes that
module's map, phase-tile data, upload code or lists and `loop.inc` constants
in the renderer's own format. The castle and 6-1 share one horizon
(`scripts/castle_horizon.py`), which also regenerates the castle sky and star
images and checks the static castle tables committed in
`castle-generated.inc` against them; `scripts/rev5_texture.py` emits the
2-2/4-2 upload code, and 2-2 also gets the table of rows whose entries are
all equal (`uniform_rows`). `scripts/native_seams.py` is the development tool that
chose each loop; the build does not run it.

The splash is also generated: `src/notice/screen.json` supplies its text and
rows, `VERSION` the displayed version, and `scripts/notice_assets.py` the
tile map and font (glyph rows in the script). Its 32-glyph font allocation and
28-column safe area are checked at build time.

This is a **source rebuild from the original game**: no byte comes from a
release patch.

## Make a change

Edit the relevant `src/<module>/main.asm` or `.inc` file, then:

```sh
python3 scripts/project.py build --rom "/path/to/original.pce" \
  --assembler "/path/to/pceas" \
  --output "dist/Ninja Ryukenden - development.pce" \
  --bps-output "dist/ninja-ryukenden-enhanced-development.bps"
```

Omit `--verify-release` for intentional changes. A successful assembly is not
gameplay validation. Follow [VALIDATION.md](VALIDATION.md), record the exact
output hash, and never change the published patches or `release/current.json`.
Bump `VERSION` for new work; the displayed splash version follows it.

When changing a backdrop loop, edit `native_gfx.LOOPS` (and run
`scripts/native_seams.py` to compare seams); the build regenerates the data.

## ROM-free checks

```sh
python3 -m unittest discover -s tests -v
python3 scripts/audit_public.py
```

CI can run these without a ROM. Exact-ROM builds and gameplay checks are
local because the source game is not supplied to CI.

To check standalone distribution archives with a private ROM:

These checks use the current release in `release/current.json`. Packaging
writes versioned archives and `dist/SHA256SUMS-v<VERSION>.txt`; `package.py`
refuses to package while `VERSION` differs from the current release record.

```sh
python3 scripts/package.py
python3 scripts/check_export.py --rom "/path/to/original.pce" \
  --assembler "/path/to/pceas"
```

This extracts both archives into temporary directories, checks exact builds,
proves an isolated assembly edit changes the expected byte and produces a
working development BPS, and checks wrong-input/overwrite protection. Its
temporary modified ROM is discarded; published bytes remain unchanged.
