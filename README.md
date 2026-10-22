# Ninja Ryukenden Enhanced — v1.09

A **Ninja Gaiden TurboGrafx-16 (Japan)** enhancement patch by **TIGERMONKEYFISH**,
for **PC Engine (PCE) / TurboGrafx-16 (TG16)**. It adds smoother parallax,
Level Select, optional No Damage and English by default to Ninja Ryukenden.

## Features

- **Parallax scrolling:** smoother, slower backgrounds in 11 stages, drawn
  from the game's own original artwork, with repaired scenery seams and a
  stationary moon in a twinkling sky in 6-1.
- **Plays exactly like the original:** in emulator tests every enhanced stage
  plays frame for frame like the original game, with the same enemies,
  timing, load and respawn times. Only the backgrounds change.
- **Level Select / Stage Select:** jump to any stage from the in-game menu
  (Ryu starts it with full health) and switch between Original and Enhanced
  parallax at any time.
- **No Damage:** optional protection from ordinary damage and hit reactions.
  It defaults off; pits and time-outs still cost a life.
- **English by default:** uses the game's built-in English translation and
  keeps the original language switch.

## Choose your ROM and patch

Both **headered** and **headerless** original Japanese ROMs are supported.
They contain the same game data; the headered file has an extra 512-byte
copier header. Each format needs its matching BPS patch, and **both patches
produce the same Enhanced 1.09 game**.

Use your own **original, unpatched ROM**. Check its exact file size and
SHA-256 against one of the sections below. Filenames can vary; neither a
filename nor file size alone proves a match. No game ROM is included here.

### Headered ROM — 524,800 bytes

| Identify your original ROM | Expected value |
| --- | --- |
| File size | **524,800 bytes**, including a 512-byte copier header |
| CRC32 | `A186DFD2` |
| SHA-256 | `1b3f411dd7d11b1d26fdac199308f77b14144dd2291e417aeb478ad2b8061a89` |

**[Download the headered BPS patch](patches/ninja-ryukenden-enhanced-v1.09.bps)**
· **[Headered patching instructions](release/PLAYER-README.md)**

Example filename: `Ninja Ryukenden (J).pce`.

### Headerless ROM — 524,288 bytes

| Identify your original ROM | Expected value |
| --- | --- |
| File size | **524,288 bytes**, with no copier header |
| CRC32 | `67573BAC` |
| SHA-256 | `3514f2e33257d6d4249aa0f0bee39c0fc7f395e1c8a37a6125b1e33601ace8e2` |

**[Download the headerless BPS patch](patches/ninja-ryukenden-enhanced-v1.09-headerless.bps)**
· **[Headerless patching instructions](release/HEADERLESS-README.md)**

Example filenames: `Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce` or `gaiden.pce`.

## Apply the patch and play

1. **Download the matching BPS patch** from the section for your original ROM,
   or from the [itch.io page](https://tigermonkeyfish.itch.io/turbografx-16-pc-engine-ninja-ryukenden-ninja-gaiden-enhanced-parallax)
   (free; a tip is optional).
2. **Open a BPS patcher.** Select your original `.pce` file as the source and
   the matching `.bps` file as the patch. The instructions linked above also
   include a Python option using the tools in this repository.
3. **Save a new file** named `Ninja Ryukenden - Enhanced v1.09.pce`.
   Keep your original ROM. Apply only one patch, directly to the original;
   do not apply it over an older Enhanced version or another patched ROM.
4. **Load the new `.pce` file** in your emulator, or copy it to your
   Turbo EverDrive's SD card and launch it on your console. Start with a fresh
   boot/reset rather than an old save state. Press or hold **Run** to continue
   past the splash screen.

If the patcher reports a source size or checksum mismatch, compare your
original against the two sections above and check that you chose its matching
patch. You do not need to add or remove a header.

### Check the patched game

Either patch produces this same output:

| Patched ROM | Expected value |
| --- | --- |
| File size | **1,048,576 bytes**, with no copier header |
| CRC32 | `699381B7` |
| SHA-256 | `f84a31a86da01d1a3377a68a6ad3242af19065095915ed18dab487cb732ab912` |

See [ROM identification](docs/ROM-IDENTITY.md) for further details.

## Controls and defaults

**[How to change the options, with screenshots](docs/OPTIONS.md)**

During gameplay, press **Select** to open the Level Select / options menu.
**Up/Down** chooses a field; **Left/Right** changes it; **I** applies the
settings and restarts the selected stage with full health; **II** closes the
menu with nothing changed.

| Setting | Default | Choices |
| --- | --- | --- |
| Parallax | ENHANCED | ENHANCED / ORIGINAL |
| No Damage | OFF | OFF / ON |
| Language | English | Native title-screen shortcut below |

At the title screen, hold **I + II** and press **Select** to cycle
English → Chinese → Japanese → English. Some title and chapter artwork
retains its original Japanese lettering.

## Hardware testing and coverage

Player testing has been reported on:

- **NEC PC Engine Duo-RX** with **Krikzz Turbo EverDrive PRO** (version 1.09).
- **TurboGrafx-16** with **Krikzz Turbo EverDrive** and an **EDFX RGB adapter**.

Enhanced parallax covers **1-1, 2-2, 3-1, 3-2, 4-1, 4-2, 5-2, 5-3, 5-4,
6-1 and 6-3**. Other stage entries retain their native backgrounds.
See [validation and testing scope](docs/VALIDATION.md) for hardware reports
and emulator checks.

## Project information

- [itch.io page](https://tigermonkeyfish.itch.io/turbografx-16-pc-engine-ninja-ryukenden-ninja-gaiden-enhanced-parallax)
- [Original vs Enhanced videos](https://www.youtube.com/playlist?list=PLGlcjDjQV7V8):
  every enhanced stage, side by side
- [Changelog](CHANGELOG.md) and [credits](CREDITS.md): developed by
  TIGERMONKEYFISH with **OpenAI Codex Astra** (the first parallax, Level
  Select, No Damage and English work) and **Anthropic Claude Opus 5.5**
  (backgrounds rebuilt from the original art, timing parity with the
  original, and the validation and video tools)
- [Contributor guide](CONTRIBUTING.md) and [build instructions](docs/BUILDING.md)
- [Comparison videos](docs/COMPARISON-VIDEOS.md): how the side-by-side
  original-versus-Enhanced stage videos are recorded and verified
- [Architecture](docs/ARCHITECTURE.md), [development handoff](docs/HANDOFF.md),
  and [PC Engine research notes](docs/pc-engine/README.md)

This is an unofficial community patch, not affiliated with or endorsed by
the original publisher. Original project code, tools and documentation use
the [MIT License](LICENSE); the original game's material is excluded.
See [license scope](docs/LICENSING.md).
