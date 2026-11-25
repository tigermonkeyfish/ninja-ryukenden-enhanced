# Ninja Ryukenden Enhanced — v1.11

Brought to you by **TIGERMONKEYFISH**. An unofficial community fan patch,
not affiliated with or endorsed by the original publisher.

An enhancement patch for **Ninja Gaiden TurboGrafx-16 (Japan)**, titled
**Ninja Ryukenden** on PC Engine: smoother, slower parallax backgrounds drawn
from the game's own art, a Level Select, optional No Damage, optional NES
Firewheel logic, five selectable palette modes (**ORIGINAL**,
**APOCALYPSE**, **NES**, **SMS**, **DMG**), backup-memory settings persistence,
and English by default. Match your original ROM to the checksums below;
listings and filenames may use either name or **Ninja Ryuuken Den**.

This package contains two BPS patches and an optional Python patching tool.
It does not contain a game ROM.

## Choose the patch for your ROM

Both patches produce exactly the same game. They differ only in the original
file they accept:

| Your original ROM | Use |
| --- | --- |
| **524,800 bytes**, CRC32 **A186DFD2** (with a 512-byte copier header), e.g. `Ninja Ryukenden (J).pce` | `patches/ninja-ryukenden-enhanced-v1.11.bps` (instructions below) |
| **524,288 bytes**, CRC32 **67573BAC** (no header), e.g. `Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce` | `patches/ninja-ryukenden-enhanced-v1.11-headerless.bps` (see `release/HEADERLESS-README.md`) |

Full SHA-256 values of both originals are in `release/current.json`. A
matching filename alone is not sufficient.

## Apply (headered ROM)

Headered original: SHA-256
`1b3f411dd7d11b1d26fdac199308f77b14144dd2291e417aeb478ad2b8061a89`.

Apply `patches/ninja-ryukenden-enhanced-v1.11.bps` with a BPS patcher:

1. Select that `.bps` file as the patch.
2. Select your original, unpatched Japanese ROM as the source.
3. Save the result as a new `.pce` file, keeping your original.

Apply it directly to the original ROM, never over an already-patched ROM.
Alternatively, use Python 3.10+ (it accepts either original format):

```sh
python3 scripts/project.py apply --rom "/path/to/original.pce"
```

The output is `dist/Ninja Ryukenden - Enhanced v1.11.pce`:

- Size: **1,048,576 bytes**, no copier header
- CRC32: **6F28B771**
- SHA-256: `e62ce8591c2aa75229fddec4c4ade8d6e732b68a3b1fbefbc9d16839f75c47d2`

Verify the output with:

```sh
python3 scripts/project.py verify "dist/Ninja Ryukenden - Enhanced v1.11.pce"
```

Start from a fresh boot/reset, not an older save state. A source-checksum
error means the ROM and patch do not match; check the table above.

## Controls

During gameplay, press **Select** for the stage/options popup menu (`STAGE`,
`SMOOTH PARALLAX`, `NO DAMAGE`, `NES FIREWHEEL`, `PALETTE`, `LANGUAGE`,
`RESET OPTIONS`). **Up/Down** chooses a setting (its value blinks),
**Left/Right** changes it, **I** (or **II**) on **RESET OPTIONS** resets the
draft options to defaults, **Run** accepts (and saves to backup memory when
available) and restarts the selected stage with full health, and **Select**
cancels and closes the menu with nothing changed.

- **SMOOTH PARALLAX: ON** (Enhanced) is the default; **OFF** shows the game's
  own backgrounds.
- **NO DAMAGE** defaults **OFF**. When **ON**, pits and time-outs still cost a
  life.
- **NES FIREWHEEL** defaults **OFF**. When **ON**, the Fire Wheel art follows
  the NES Invincible Fire Wheel rules.
- **PALETTE** steps **ORIGINAL**, **APOCALYPSE**, **NES**, **SMS**, **DMG**.
  **DMG** also keeps its 4-shade palette on the title, story scenes, and ending.
- **LANGUAGE** defaults to **ENGLISH** (when no backup-memory file overrides it).
  On the title screen you can also hold **I + II** and press **Select** to
  cycle English → Chinese → Japanese → English. Some logo and chapter
  lettering remains Japanese, as in the game's own English mode.
- **Backup memory:** pressing **Run** saves settings to console backup RAM (`NR ENHANCE`) so future power-ons and resets restore them automatically when backup RAM is available.

A guide with screenshots:
https://github.com/tigermonkeyfish/ninja-ryukenden-enhanced/blob/main/docs/OPTIONS.md

## Release scope

In emulator tests, all 22 stage entries and the full recorded playthrough
match the original game's stage timing when running in **ORIGINAL** or **NES**
mode. The exact 1.11 release bytes were tested on both an NEC PC Engine
Duo-RX and a TurboGrafx-16 with a Krikzz Turbo EverDrive PRO. When reporting
a bug, include the version or ROM hash, stage, options, hardware or emulator,
and how to reproduce it.

Updates: https://github.com/tigermonkeyfish/ninja-ryukenden-enhanced

Original patch code, tools and docs use MIT; the original game's material is
excluded. See `LICENSE`, `docs/LICENSING.md`, `CREDITS.md` and `CHANGELOG.md`.
