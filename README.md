# Ninja Ryukenden Enhanced — v1.11

A **Ninja Gaiden TurboGrafx-16 (Japan)** enhancement patch by **TIGERMONKEYFISH**,
for **PC Engine (PCE) / TurboGrafx-16 (TG16)**. It adds smoother parallax,
a centered popup Level Select/options menu, five colour palettes, optional
No Damage and NES Firewheel, backup-memory settings persistence, and English by default.

## Features

- **Parallax scrolling:** smoother, slower backgrounds in 11 stages, drawn
  from the game's own original artwork, with repaired scenery seams and a
  stationary moon in a twinkling sky in 6-1. Other stage entries keep their
  native backgrounds.
- **Timing parity:** `ORIGINAL` and `NES` match the unmodified ROM's update,
  stage-load, area-change, and cinema-entry timing across all 22 stages.
- **Popup Level Select & options menu:** opens cleanly over the playfield
  while keeping the status bar visible (`STAGE`, `SMOOTH PARALLAX`,
  `NO DAMAGE`, `NES FIREWHEEL`, `PALETTE`, `LANGUAGE`, `RESET OPTIONS`),
  pausing music/SFX cleanly until closed.
- **Five palette modes:** **ORIGINAL**, **APOCALYPSE**, **NES** (2C02G master
  palette), **SMS** (Sega Master System 64-colour palette), and **DMG**
  (4-shade green spanning gameplay, title, story scenes, and ending).
- **Optional gameplay toggles:** **No Damage** (pits and time-outs still cost
  a life) and **NES Firewheel** (NES Invincible Fire Wheel behaviour). Both
  default OFF.
- **Backup-memory settings:** automatically saves and restores menu choices
  to console backup RAM (`NR ENHANCE`) when available, with safe fallback
  when absent, full, or unformatted.
- **English by default:** uses the game's built-in English translation and
  keeps both the title-screen language switch and the menu selector.

## Choose your ROM and patch

Both **headered** and **headerless** original Japanese ROMs are supported.
They contain the same game data; the headered file has an extra 512-byte
copier header. Each format needs its matching BPS patch, and **both patches
produce the same Enhanced 1.11 game**.

Use your own **original, unpatched ROM**. Check its exact file size and
SHA-256 against one of the sections below. Filenames can vary; neither a
filename nor file size alone proves a match. No game ROM is included here.

### Headered ROM — 524,800 bytes

| Identify your original ROM | Expected value |
| --- | --- |
| File size | **524,800 bytes**, including a 512-byte copier header |
| CRC32 | `A186DFD2` |
| SHA-256 | `1b3f411dd7d11b1d26fdac199308f77b14144dd2291e417aeb478ad2b8061a89` |

**[Download the headered BPS patch](patches/ninja-ryukenden-enhanced-v1.11.bps)**
· **[Headered patching instructions](release/PLAYER-README.md)**

Example filename: `Ninja Ryukenden (J).pce`.

### Headerless ROM — 524,288 bytes

| Identify your original ROM | Expected value |
| --- | --- |
| File size | **524,288 bytes**, with no copier header |
| CRC32 | `67573BAC` |
| SHA-256 | `3514f2e33257d6d4249aa0f0bee39c0fc7f395e1c8a37a6125b1e33601ace8e2` |

**[Download the headerless BPS patch](patches/ninja-ryukenden-enhanced-v1.11-headerless.bps)**
· **[Headerless patching instructions](release/HEADERLESS-README.md)**

Example filenames: `Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce` or `gaiden.pce`.

## Apply the patch and play

1. **Download the matching BPS patch** from the section for your original ROM,
   or from the [itch.io page](https://tigermonkeyfish.itch.io/turbografx-16-pc-engine-ninja-ryukenden-ninja-gaiden-enhanced-parallax)
   (free; a tip is optional).
2. **Open a BPS patcher.** Select your original `.pce` file as the source and
   the matching `.bps` file as the patch. The instructions linked above also
   include a Python option using the tools in this repository.
3. **Save a new file** named `Ninja Ryukenden - Enhanced v1.11.pce`.
   Keep your original ROM. Apply only one patch, directly to the original;
   do not apply it over an older Enhanced version or another patched ROM.
4. **Load the new `.pce` file** in your emulator, or copy it to your
   Turbo EverDrive's SD card and launch it on your console. Start with a fresh
   boot/reset rather than an old save state.

If the patcher reports a source size or checksum mismatch, compare your
original against the two sections above and check that you chose its matching
patch. You do not need to add or remove a header.

### Check the patched game

Either patch produces this same output:

| Patched ROM | Expected value |
| --- | --- |
| File size | **1,048,576 bytes**, with no copier header |
| CRC32 | `6F28B771` |
| SHA-256 | `e62ce8591c2aa75229fddec4c4ade8d6e732b68a3b1fbefbc9d16839f75c47d2` |

See [ROM identification](docs/ROM-IDENTITY.md) for further details.

## Controls and defaults

**[How to change the options, with screenshots](docs/OPTIONS.md)**

During gameplay, press **Select** to open the Level Select / options popup
menu. **Up/Down** chooses a setting (its value blinks); **Left/Right** changes
it; **I** (or **II**) on **RESET OPTIONS** resets the draft options to defaults;
**Run** accepts (and saves settings to backup RAM when available) and restarts
the selected stage with full health; **Select** cancels and closes the menu
with nothing changed.

| Setting | Default | Choices |
| --- | --- | --- |
| Smooth parallax | ON (Enhanced) | ON / OFF (the original backgrounds) |
| No Damage | OFF | OFF / ON |
| NES Firewheel | OFF | OFF / ON |
| Palette | ORIGINAL | ORIGINAL / APOCALYPSE / NES / SMS / DMG |
| Language | ENGLISH | ENGLISH / CHINESE / JAPANESE (also title shortcut below) |

At the title screen, hold **I + II** and press **Select** to cycle
English → Chinese → Japanese → English. Some title and chapter artwork
retains its original Japanese lettering.

## Tested on

- **NEC PC Engine Duo-RX + Krikzz Turbo EverDrive PRO = TESTED** — exact
  `1.11` release bytes (`e62ce859…c47d2`) verified on hardware; `1.10` also
  played from both release patches.
- **TurboGrafx-16 + Krikzz Turbo EverDrive PRO = TESTED** — exact `1.11`
  release bytes (`e62ce859…c47d2`) verified on hardware (set **Default EXP
  Device** to `TNK2` or `CDROM` for backup-RAM saves on consoles without CD
  hardware).
- **Emulators:** Geargrafx.

## Known issues

- Start from a fresh boot/reset rather than loading save states created on
  older versions.
- Level Select warps hold the newly selected stage in the previous palette's
  colours for 13–17 frames before fading in.
- Fade-out and fade-in steps in **NES** palette mode dim colours by channel,
  producing intermediate steps outside the 2C02G palette during transitions.

## Building from source

Needs Python `3.10+` and `pceas`, the assembler from
[pce-devel/huc](https://github.com/pce-devel/huc) (pinned commit `54f5c73` in
[release/current.json](release/current.json)). No copyrighted game data is
hosted in this repository; every backdrop and palette table is generated at
build time from your own original Japanese ROM alone.

```sh
python3 scripts/project.py build --rom "/path/to/original.pce" --assembler "/path/to/pceas" --verify-release
```

Run the ROM-free verification checks:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/audit_public.py
```

See [build instructions](docs/BUILDING.md) for custom module builds and
standalone archive verification.

## Project information

- [itch.io page](https://tigermonkeyfish.itch.io/turbografx-16-pc-engine-ninja-ryukenden-ninja-gaiden-enhanced-parallax)
- [Changelog](CHANGELOG.md) and [credits](CREDITS.md): developed by
  TIGERMONKEYFISH with **OpenAI Codex Astra** (`1.00`/`1.01`), **Anthropic
  Claude Opus 5.5** (`1.09`/`1.10`), and the **Google Gemini** family (`1.11`)
- [Options & screenshots](docs/OPTIONS.md) and [ROM identity](docs/ROM-IDENTITY.md)
- [Contributor guide](CONTRIBUTING.md) and [build instructions](docs/BUILDING.md)

This is an unofficial community patch, not affiliated with or endorsed by
the original publisher. Original project code, tools and documentation use
the [MIT License](LICENSE); the original game's material is excluded.
See [license scope](docs/LICENSING.md).
