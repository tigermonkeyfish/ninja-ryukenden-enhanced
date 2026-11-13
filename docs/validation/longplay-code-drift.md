# Full-playthrough code drift: causes (work in progress)

WORK IN PROGRESS (checkpoint). Emulator evidence only (Geargrafx 78fc3d7 core, in-process
tracer `research/longplay/drift/`), no real-hardware claim. Verified = measured here;
inferred = read or reasoned, not measured.

Established so far:

- 5,668 (1.11-dev only): the native object-list walker (bank 2 `$A598`/`$A5B3`), on entering
  1-2 area 1, walks 139 four-byte "entries" from bank 0 `$F1FF` to `$F42E`, i.e. fixed-bank
  code read as data (original behaviour). 1.11-dev's NES palette hook changed `$F235-$F236`
  (`jsr $F2BE` -> `jsr $7FE0`, `src/nes-palette`), so the phantom entry at `$F233` gets
  different coordinates and the object is discarded instead of kept. Not a RAM overlap;
  no timing effect (same update frames). Verified by RAM bisection and instruction traces.
- 13,258: the 2-2 stage load runs 283-296k master clocks longer in 1.10 and 1.11-dev (the
  Enhanced load-time backdrop draw, `init_background` -> stage22 banks `$56-$65`); the
  original load ends 210k clocks before a vblank, so the patched load ends one vblank later.
- 51,763 (1.11-dev only): an act 3 scene update ends 465 clocks before a vblank in 1.10 and
  the original; 1.11-dev's vblank palette trampoline (+76 CPU cycles a vblank,
  `src/palette` `$FD13` -> `$FEC0`) adds 228 clocks to the waking and the inner vblank
  and it misses by about 40 clocks.
- 65,934: native. The unmodified ROM in Japanese loses the same update in the 4-4 end scene
  (Japanese text update 488k vs 286k clocks) as 1.11-dev Japanese.
- 5-4 (coordinator's fifth point): the 5-4 load runs ~240k clocks longer in 1.10 and
  1.11-dev (castle load-time draw) and ends one vblank later; same family as 13,258.
