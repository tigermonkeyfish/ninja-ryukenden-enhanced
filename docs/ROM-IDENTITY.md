# ROM identity and header convention

Game: **Ninja Ryukenden (Japan)** for **PC Engine / TurboGrafx-16**.
If you found this project by searching for **Ninja Gaiden TurboGrafx-16 (Japan)**,
this is the Japanese PC Engine game covered by the patch. ROM listings may
also spell the title **Ninja Ryuuken Den**. Use the size and checksums below
to identify a compatible dump regardless of its filename.

## Supported originals

The same game data comes in two container formats. Each has its own patch;
both patches produce the same 1.09 ROM.

| Format | Size | CRC32 | SHA-256 | Patch |
| --- | --- | --- | --- | --- |
| Headered (512-byte copier header, included in the checksums) | 524,800 bytes | `A186DFD2` | `1b3f411dd7d11b1d26fdac199308f77b14144dd2291e417aeb478ad2b8061a89` | `patches/ninja-ryukenden-enhanced-v1.09.bps` |
| Headerless | 524,288 bytes | `67573BAC` | `3514f2e33257d6d4249aa0f0bee39c0fc7f395e1c8a37a6125b1e33601ace8e2` | `patches/ninja-ryukenden-enhanced-v1.09-headerless.bps` |

Some ROM tools and catalogs report only the headerless payload checksum. The
patches and the Python tool verify the source; they do not guess at header
contents, accept other revisions, or add or remove a header. Use the patch
that matches your file. `scripts/project.py apply` and `build` accept either
format and choose the matching patch.

Local comparison found `Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce` and
`gaiden.pce` byte-identical, and identical to the game payload in the
headered `Ninja Ryukenden (J).pce`. These are container variants, not
different game revisions. This comparison does not establish which filename
or format is most common.

## Expected 1.09 result

- File size: **1,048,576 bytes** (1 MiB)
- Header: **none**
- CRC32: **699381B7**
- SHA-256: `f84a31a86da01d1a3377a68a6ad3242af19065095915ed18dab487cb732ab912`

The patches themselves have their own SHA-256 values in
`release/current.json`, and the release archives get checksums in
`dist/SHA256SUMS-v1.09.txt`. Those identify different files and should not
be confused with the source or target ROM checksums.
