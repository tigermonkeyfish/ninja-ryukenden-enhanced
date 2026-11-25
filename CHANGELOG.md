# Changelog

## 1.11 — 2026-11-24

Game:

- Centered popup in-game menu (`Select`) over the playfield (`25×11`, hiding
  sprites while open and keeping the HUD unobstructed), with a top status
  line for backup memory, blank spacing above `RUN: OK  SELECT: CANCEL`, and
  paused music and sound effects while the menu is open.
- Console backup-RAM settings persistence (`NR ENHANCE`, 26 bytes, System
  Card compatible) across power cycles and resets, storing parallax, No
  Damage, NES Firewheel, palette, and language with safe fallback when
  backup RAM is absent, full, or unformatted.
- Five selectable **PALETTE** modes (**ORIGINAL**, **APOCALYPSE**, **NES**,
  **SMS**, **DMG**) plus a **RESET OPTIONS** row (`PRESS I`) and explicit
  **LANGUAGE** selection row in the menu. **DMG** keeps its 4-shade palette
  across gameplay, title, story scenes, and the ending (`ORIGINAL`,
  `APOCALYPSE`, `NES`, and `SMS` keep native colours outside gameplay).
- Optional **NES FIREWHEEL** rule: behaves like the NES Invincible Fire
  Wheel (invulnerability while spinning, NES hitbox, per-update boss damage,
  duration, and pickup behaviour); off by default.
- Exact vblank palette-upload timing, stage-load timing, start-position
  alignment, and cutscene-entry alignment across all 22 stages and area
  transitions (`ORIGINAL` and `NES` match the unmodified ROM update-for-update
  over the full playthrough recording).

Project:

- Editable source inputs expanded for popup menu layout
  (`src/options/menu.txt`), backup-RAM module (`src/bram/`), NES Firewheel
  (`src/nes-firewheel/`), mapped palette tables (`src/palette/*.json`),
  and 2C02G NES palette data (`src/nes-palette/`).
- Patches for both ROM formats; the 1.09 and 1.10 patches remain at tags
  `v1.09` and `v1.10`.

Evidence: the maintainer verified the exact 1.11 release ROM bytes on both
an NEC PC Engine Duo-RX and a TurboGrafx-16 with a Krikzz Turbo EverDrive PRO.

## 1.10 — 2026-10-30

Game:

- The splash screen is gone: power-on goes straight to the original
  publisher screen, and the boot is the original's frame for frame.
- New in-game menu layout (Select): `STAGE:`, `PARALLAX: ON/OFF`,
  `NO DMG: OFF/ON` and `RUN: ACCEPT` on the left; the version,
  `GITHUB.COM/` `TIGERMONKEYFISH` and `SELECT: CANCEL` on the right. It uses
  the status bar and the line under it. Run accepts and Select cancels (1.09
  used I and II). The selected value blinks instead of a dash marking it.
  The text leaves the item box clear, so a held item's icon no longer covers
  it (in 1.09 it covered "OFF" and "I"). The full status bar returns when
  the menu closes.
- Gameplay, backgrounds and cinemas are unchanged from 1.09.

Project:

- The menu text is editable source (`src/options/menu.txt`), checked and
  encoded at build time (`scripts/menu_text.py`).
- Patches for both ROM formats; the 1.09 patches remain at tag `v1.09`.

Evidence: the maintainer played 1.10 from both patches on an NEC PC Engine
Duo-RX with a Krikzz Turbo EverDrive PRO (1-1, 1-2, Level Select to 2-2 and
the final boss, into the ending cinema).

## 1.09 — 2026-10-21

The first public release. A patch for the Japanese PC Engine Ninja Ryukenden
(Ninja Gaiden), headered or headerless original.

Game:

- Smooth parallax in 11 stage entries (1-1, 2-2, 3-1, 3-2, 4-1, 4-2, 5-2,
  5-3, 5-4, 6-1, 6-3): the backgrounds scroll smoothly and slower than the
  playfield. Every Enhanced backdrop is generated at build time from the
  original ROM's own tiles, maps and palettes; no art is edited or added.
  Every round opens exactly like the original, and 6-1 has a stationary
  moon in a twinkling sky.
- Timing parity: all 11 enhanced stages play frame for frame like the original
  with matching button input (sprites, Ryu, enemies, timer, health, camera).
  Stage loads, respawns and area changes take the same number of frames as in
  the original, and no scrolling update takes longer than the original's.
- Level Select / options menu (Select during play): jump to any of 22 stage
  entries (Ryu starts with full health), switch between Enhanced and
  Original backgrounds, and turn No Damage on or off. Defaults: Enhanced, No
  Damage off.
- English by default, using the game's built-in translation; the original
  title-screen language switch (English, Chinese, Japanese) is kept.
- The cinema after every stage matches the original's after a full play of
  each enhanced stage.
- A splash screen with the version and the project address; Run leaves it
  without delay.

Project:

- Source build from the original ROM alone (`scripts/project.py build`), and
  release patches for both ROM formats.
- Player guide with screenshots ([docs/OPTIONS.md](docs/OPTIONS.md)).

Evidence: the release bytes were played on an NEC PC Engine Duo-RX with a
Krikzz Turbo EverDrive PRO.
