# Ninja Ryukenden Enhanced 1.09 — headerless ROM patch

For **Ninja Gaiden TurboGrafx-16 (Japan)**, the PC Engine game titled
**Ninja Ryukenden**, also spelled **Ninja Ryuuken Den** in ROM filenames.

This patch accepts the original Japanese game **without a copier header**.
It produces exactly the same Enhanced 1.09 ROM as the headered patch.

## Choose the correct input

Use your original, unpatched ROM matching all of these values:

- Size: **524,288 bytes**
- CRC32: **67573BAC**
- SHA-256: `3514f2e33257d6d4249aa0f0bee39c0fc7f395e1c8a37a6125b1e33601ace8e2`

Known filenames include `Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce` and
`gaiden.pce`. Filenames alone do not establish compatibility.

If your original is **524,800 bytes**, CRC32 **A186DFD2**, use
`ninja-ryukenden-enhanced-v1.09.bps` instead (see `README.md`). That file
includes a 512-byte copier header; the game data itself is identical. Do not
add or remove header bytes, and do not apply either patch over an
already-patched ROM.

## Apply

In a BPS patcher:

1. Select `patches/ninja-ryukenden-enhanced-v1.09-headerless.bps` as the patch.
2. Select your matching 524,288-byte original ROM as the source.
3. Save the output as `Ninja Ryukenden - Enhanced v1.09.pce`.

Alternatively, from the extracted package, use the included Python tool:

```sh
python3 scripts/project.py apply --rom "/path/to/original.pce"
```

Expected output:

- Size: **1,048,576 bytes**, no copier header
- CRC32: **699381B7**
- SHA-256: `f84a31a86da01d1a3377a68a6ad3242af19065095915ed18dab487cb732ab912`

Start with a fresh boot/reset. Press or hold Run to leave the splash;
press Select during gameplay for the options menu.

This package contains no game ROM. Original project code, tools and docs use
MIT; the original game's material is excluded. See LICENSE, CREDITS.md and
docs/LICENSING.md. Updates: https://github.com/tigermonkeyfish/ninja-ryukenden-enhanced
