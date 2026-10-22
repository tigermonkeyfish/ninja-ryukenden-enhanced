# Ninja Ryukenden Enhanced — v1.09

Brought to you by **TIGERMONKEYFISH**. An unofficial community fan patch,
not affiliated with or endorsed by the original publisher.

An enhancement patch for **Ninja Gaiden TurboGrafx-16 (Japan)**, titled
**Ninja Ryukenden** on PC Engine: smoother, slower parallax backgrounds drawn
from the game's own art, a Level Select, optional No Damage, and English by
default. Match your original ROM to the checksums below; listings and
filenames may use either name or **Ninja Ryuuken Den**.

This package contains two BPS patches and an optional Python patching tool.
It does not contain a game ROM.

## Choose the patch for your ROM

Both patches produce exactly the same game. They differ only in the original
file they accept:

| Your original ROM | Use |
| --- | --- |
| **524,800 bytes**, CRC32 **A186DFD2** (with a 512-byte copier header), e.g. `Ninja Ryukenden (J).pce` | `patches/ninja-ryukenden-enhanced-v1.09.bps` (instructions below) |
| **524,288 bytes**, CRC32 **67573BAC** (no header), e.g. `Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce` | `patches/ninja-ryukenden-enhanced-v1.09-headerless.bps` (see `release/HEADERLESS-README.md`) |

Full SHA-256 values of both originals are in `release/current.json`. A
matching filename alone is not sufficient.

## Apply (headered ROM)

Headered original: SHA-256
`1b3f411dd7d11b1d26fdac199308f77b14144dd2291e417aeb478ad2b8061a89`.

Apply `patches/ninja-ryukenden-enhanced-v1.09.bps` with a BPS patcher:

1. Select that `.bps` file as the patch.
2. Select your original, unpatched Japanese ROM as the source.
3. Save the result as a new `.pce` file, keeping your original.

Apply it directly to the original ROM, never over an already-patched ROM.
Alternatively, use Python 3.10+ (it accepts either original format):

```sh
python3 scripts/project.py apply --rom "/path/to/original.pce"
```

The output is `dist/Ninja Ryukenden - Enhanced v1.09.pce`:

- Size: **1,048,576 bytes**, no copier header
- CRC32: **699381B7**
- SHA-256: `f84a31a86da01d1a3377a68a6ad3242af19065095915ed18dab487cb732ab912`

Verify the output with:

```sh
python3 scripts/project.py verify "dist/Ninja Ryukenden - Enhanced v1.09.pce"
```

Start from a fresh boot/reset, not an older save state. A source-checksum
error means the ROM and patch do not match; check the table above.

## Controls

Press or hold **Run** at the splash. During gameplay, press **Select** for
the stage/options menu. **Up/Down** chooses a field, **Left/Right** changes
it, **I** applies and restarts the selected stage with full health, **II**
closes the menu with nothing changed.

- **ENHANCED** parallax is the default; **ORIGINAL** shows the game's own
  backgrounds.
- **No Damage** defaults OFF. When ON, pits and time-outs still cost a life.
- **English** is selected at reset. At the title screen, hold **I + II** and
  press **Select** to cycle English → Chinese → Japanese → English. Some logo
  and chapter lettering remains Japanese, as in the game's own English mode.

A guide with screenshots:
https://github.com/tigermonkeyfish/ninja-ryukenden-enhanced/blob/main/docs/OPTIONS.md

## Release scope

In emulator tests, each of the 11 enhanced stages plays frame for frame like
the original game, with the same load and respawn times; only the
backgrounds change. Version 1.09 was played on an NEC PC Engine Duo-RX with
a Krikzz Turbo EverDrive PRO. When reporting a bug, include the version or
ROM hash, stage, options, hardware or emulator, and how to reproduce it.

Updates: https://github.com/tigermonkeyfish/ninja-ryukenden-enhanced

Original patch code, tools and docs use MIT; the original game's material is
excluded. See `LICENSE`, `docs/LICENSING.md`, `CREDITS.md` and `CHANGELOG.md`.
