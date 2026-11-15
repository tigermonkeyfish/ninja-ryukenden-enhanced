# Timing cleanup (`timing-cleanup`): D2, D3, D4/D5 fixes and anomaly investigations

Emulator evidence only (Geargrafx `78fc3d7` / `libgxar.so`); no real hardware.

Branch `timing-cleanup`, code commit `846e0b9` (`846e0b9760a0c69a84f1a2b2bf1d4153d9c2ff73`), built on `align-combined` (`dbc2034`).

## Build and BPS patches (verified)

Built from source with `scripts/project.py build` and `pceas` from both the headered (`Ninja Ryukenden (J).pce`) and headerless (`Ninja Ryuuken Den (Japan) (En,Ja,Zh).pce`) originals, and verified by applying both `.bps` patches back with `scripts/bps.py apply`:

- ROM (`timing1.pce` and delivered `.pce`): `1,048,576` bytes, SHA-256 `ea1762973dbd04e1497a74b65ba093a260fc92ccd38c8698798b839c6d63ace1`
- Headered BPS: `445,474` bytes, SHA-256 `c7ae94da6e303ef4ddd7c9ae7d284f46ea18368691f3a0772ab42d7b69f98833`
- Headerless BPS: `445,473` bytes, SHA-256 `25b4b92edccfc2775b7a94b51353f9128a70ac54a361606cdc7733280d4eb635`

Byte diffs against `align-combined/rom.pce` (`2f134a80`):

- Bank `$00`, `$FF41..$FF6C` (`0x001F41..0x001F6C`, 44 B span, 38 B changed)
- Bank `$46`, `$5DF9..$5FFD` (`0x08DDF9..0x08DFFD`, 517 B span, 512 B changed)
- Bank `$56`, `$4CF0..$4E6F` (`0x0ACCF0..0x0ACE6F`: `$4CF0..$4E18`, `$4E2F..$4E58`, `$4E6D..$4E6F`)

## Fixes in `846e0b9`

1. **D4 + D5 (`src/dispatch/main.asm`, `deferred_draw` at `$00:FF42-$FF68`, 39 B):**
   Replaced the 17-cycle `$FF` check with `lda $2258 / inc a / bpl draw_done / cmp #$ff / bcc draw / sta $2258` (11 cycles for `$00..$08`, `$03`, and `$FF -> $00`; 15 cycles for `$FC/$FD -> $FD/$FE`; 18 cycles for `$FE -> $FF`). Eliminates the +6-cycle per-update overhead in stages without an Enhanced backdrop and resolves D5 (4-1 frame `1,664` with `SMOOTH PARALLAX OFF`).
   - `init_hook_end = $00:FF69` (**7 bytes free** at `$FF69-$FF6F`, up from 3).

2. **D3 (`src/stage22/main.asm`, Option 2A-1 in `draw_all` at `$56:4CF8`):**
   Mapped modes (`$2100 & $10`) now run `jsr cache` (`$40BB`) before `ldx #208 / ldy #32 / jmp $febe`, eliminating the 1-line dash in 2-2 area 2's last black transition frame (`14,672`). Palettes 13-14 are still written to VCE mid-frame after `cache` in mapped modes (HUD and sprites untouched).
   - `main_end = $56:41D4` (**300 bytes free** before `$4300`), `helpers_end = $56:4E70` (**400 bytes free** before `$5000`).

3. **D2 (`src/palette/main.asm`, Option A in `worker_convert` at `$46:5DE1..$5FFE`):**
   Zero new RAM/ZP (`W_SRC_HI = $24`, `W_ENTRY = $26`, `W_OVR` bit 7 = HELL, bit 0 = override stage). `convert_table` and `convert_hell_mapped` index with `Y = (256 - chunk)..0` and `W_SRC_HI` (58/60 cycles/colour, ~91,926 clocks for 512 colours, clearing 5-3 a4's 95,115-clock budget while keeping 1-colour `<$12` abort latency). `worker_chunk` hoists the `2 * HELL_MAPPED` (`$01E0`) boundary check, `convert_hell_ovr` runs only when `W_OVR` bit 0 = 1, and `worker_do_raw` is inlined (42 cycles/colour).
   - Bounds: `palette_upload_end = $00:FECF` (**17 bytes free**), `palette_code_end = $46:53F4` (SMS mirror `$3B:53F4`, **12 bytes free**), `palette_far_end = $46:5AA3` (SMS mirror `$3B:5AA3`, **93 bytes free**), `timing_end = $46:5FFE` (**2 bytes free** at `$5FFE-$5FFF`), `hell_code_end = $43:7BED` (**19 bytes free** before `HELL_TABLE = $7C00`).

## Anomaly investigations on `align-combined` (`2f134a80`)

- **D11 (4-3, frames `60,700..60,715`) — resolved on `align-combined`:** `0` CORE diffs across `original`, `apocalypse`, `sms`, `gbdmg`. Ryu's y byte (`$2EA0`) is `20` at frame `60,707` end and `190` at frames `60,708` and `60,709` end in all 4 modes. In earlier builds (palette timing 2 APOCALYPSE / palette timing 3 SMS), `$01:85E5` (`sta $2EA0`) ran only `480` clocks (160 CPU cycles) before vblank `$FCEC`, so any `>= 480`-clock delay pushed the write across the frame-end sample boundary.
- **D7 (6-3 -> 6-4 cinema entry, frame `97,646`):** On `full-load.json`, `$2000 = 56` in `apocalypse`, `sms`, `gbdmg` vs `57` in `original` at frame `97,646` end (`97,647` is `57 = 57`). `RENT` MN uploads all 512 colours (`$FD13..$FD16 = 22,179` clocks vs `717` in `original`), so the `tia` stub is still running at frame `97,646` end (`35,255,821,980`). `$00:E06C` (`inc <$00`) executes in frame `97,647` at `+17,229` clocks, leaving `322,809` clocks before frame `97,647` vblank. Zero updates lost.
- **D13 (5-4 post-boss, `original` vs `unmod-en`, frames `82,800..84,499`):** `88` differing frames (`83,621..84,289`, every 4th frame during the post-boss timer-to-score countdown; `0` diffs in `82,800..83,620`), differing by `1-27` px in screenshot rows `19..25`, cols `72..102`. `$01:8457`'s `jsr $FE40` (early wrapper + castle star animation in bank `$7C`, plus `$01:8472` `jsr $FF00`) delays `$01:845D..$00:E061` by `~20.8k` clocks (`~15.2` scanlines), shifting the HUD digit VRAM writes (`$01:96E9 -> $00:FC8A`) across rasterized HUD lines `33..39` (`+45,045..+54,600` clocks).
- **D6 (2-2 frame `788`, `check_menu` sweep):** `menu` vs `ref` enter `$FCD7` on an RCR IRQ and spin in `WAITR` (`30` clocks/iter) until `IRQ1`, ending frame 0 at `end0_vdc = (3,0)` vs `(0,0)` (`3` VDC dots = `12` master clocks relative to `y=0`, inside the `30`-clock polling jitter). That `12`-clock offset straddles the `42`-clock write of VCE word `0xae` (`+8,103..+8,145` clocks post-`IRQ1`).
- **Outside `2-2/5-2/5-3/5-4` transition survey (`APOCALYPSE`, `SMS`, `GB DMG` on `full-load.json`):** `62` windows captured (`2,702` frames: `60` outside `2-2/5-2/5-3/5-4` plus `2` boss/cinema exits out of `5-3`/`5-4`), `0` frame drift, `0` D2 / 1-frame black-foreground anomalies across all `60` outside windows (`1-1` start, `17` stage loads, `15` mid-stage area changes, `9` black-gap entries, `18` fade-outs).

## Verification on `timing1.pce` (`ea176297`)

Logs under `/workspace/build/timing-cleanup/verify/`:

| Check | Result | Notes |
| --- | --- | --- |
| `python3 -m unittest tests.test_tools` | PASS | 54 tests |
| `python3 scripts/audit_public.py` | PASS | 497 files |
| `check_boot.py` (`boot.log`) | PASS | Idle frames `1-899` identical to original (`136` distinct screens), mash first update `163` |
| `check_menu.py --only options --only reset` (`menu_opt_reset.log`) | PASS | `68/68` ok (`0` timer-phase-only) |
| `check_menu.py --only select` (`menu_select.log`) | PASS | `21/21` entries + language check (`0` timer-phase-only) |
| `check_menu.py --only runs` (`menu_runs.log`) | PASS | `140/140` across 11 runs (`0` timer-phase-only) |
| `check_menu.py --only runs --parallax-off` (`menu_runs_px.log`) | PASS | `140/140` across 11 runs including `4-1` frame `1,664` (`0` timer-phase-only; D5 resolved) |
| `check_menu.py --only runs --preview` (`menu_runs_preview.log`) | PASS | `140/140` across 11 runs (`0` timer-phase-only) |
| `check_bram.py --only cycle` (`bram.log`) | PASS | `17/17` |
| `check_bram_fallback.py` (`bram_fallback.log`) | FAIL (`rc=1`) | Pre-existing sound-timer phase shift matching `align-combined` (`bram_fallback_align.log`, `rc=1`): `control`, `write-error`, `control-old`, `write-error-old` PASS and all 18 negative controls bite; `no-memory` / `no-memory-bus` differ in `66/2843` frames (`14` in a row, `['0x84', '0x18bb']`) vs `align-combined` `59/2843` (`7` in a row); `full-memory` differs at frame `774` in `['screen']` and `121/2843` RAM frames (`['0x85', '0x88', '0x18bb']`) vs `align-combined` `115/2843` + frame `774` `['screen']` |
| `palette_lag.py pairs` (`pairs.log`) | PASS | `36/36`: first update `+0` clk, `0` sound RAM/counter/Ryu/stage/irq clock diffs, `0` lag frames |
| `palette_lag.py fastok --lengths 195..215` (`fastok.log`) | PASS | All 21 lengths `FASTOK 00`, no `FASTOK 1` |
| `palette_lag.py loadtime` (`loadtime.log`) | PASS | `132/132` `+0` clk |
| `palette_lag.py e2e` (`e2e.log`) | PASS | All 6 modes: first update `+0` clk, `0` differing frames in `2,903`, `96` sound commands, min margin `146,208` |
| D3 (`d3.log`, `verify_d3.py`) | PASS | All 6 modes: frame `14,672` `extra_px=0` (`align-combined` had `24` in `APOCALYPSE`, `32` in `SMS`); `14,033` and `14,673` byte-identical to `align-combined` |
| D2 (`d2.log`, `verify_d2.py`) | Partial log | `stage 1-1 (f=10)` and `2-1 (f=10,200)` VCE byte-identical to `align-combined` in `APOCALYPSE` (`VCE[$094]=80`, matching `align=80`); `d2.log` stopped at `verify_d2.py:137` (`AssertionError: apocalypse 1-1 VCE[$094]=80 != 210`). D2 first-visible-frame fixes on 5-3 are confirmed in `pics_vs_align.log` below |
| `full-load.json` 6-mode replay (`lx-*.log`, `runs/timing1-*.npz`) | PASS | 126,002 samples (frames `0..126,001`) vs `unmod-L.npz`: `ORIGINAL`, `NES-A`, `NES-B` `0` diffs (`cnt`, `mas`, `m2`, `stg`, `are`); `APOCALYPSE`, `SMS`, `GB DMG` `cnt` differs in `1` frame (`97,646`), `0` diffs in `mas`/`m2`/`stg`/`are` |
| Sampled picture check (`pics_vs_align.log`, `verify_pics_vs_align.py`) | PASS | `843` frames/mode across 48 start-window events + ending + every 500th frame: `0` unexpected diffs in all 6 modes; `expected_fixed_diffs`: `APOCALYPSE` `[14672, 77976, 78672, 79291, 80300, 80632, 80890]`, `SMS` `[14672, 80300, 80890]`, `GB DMG` `[14672, 80300, 80890]`, `ORIGINAL`/`NES-A`/`NES-B` `[]` |
