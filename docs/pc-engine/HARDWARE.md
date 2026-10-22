# PC Engine hardware and toolchain facts

The facts this project relied on while patching a 4 Mbit HuCard (Ninja
Ryukenden), written for the next patch or homebrew project. Each fact names
its basis and a confidence. The bases are kept apart on purpose:

- **source:** read in the Geargrafx source (commit `78fc3d7`). It shows the
  emulator's model, not the hardware.
- **emulated:** measured in that Geargrafx build (see [EMULATOR.md](EMULATOR.md)).
- **hardware:** reported on a real console. The only reports are of whole
  builds that looked right in play (NEC PC Engine Duo-RX with a Krikzz Turbo
  EverDrive PRO; a TurboGrafx-16 with a Turbo EverDrive). None measured a
  timing. A flash cart is not a mask-ROM HuCard.
- **game code:** read in Ninja Ryukenden's own code. It is that game's
  convention, which other Hudson-era games often share.
- **documented:** standard PC Engine documentation or common knowledge,
  not re-checked in this project.

Ninja addresses below are illustrations. [ARCHITECTURE.md](../ARCHITECTURE.md)
has the full Ninja map.

## Time

| Fact | Basis | Confidence |
| --- | --- | --- |
| The master clock is 21,477,273 Hz (`GG_MASTER_CLOCK_RATE`). The CPU runs at 7.16 MHz (3 master clocks per cycle) after `csh`, or 1.79 MHz (12 per cycle) after `csl`. | source; documented | high |
| A line is 1365 master clocks (455 CPU cycles at 7.16 MHz). A frame has 262 or 263 lines, chosen by VCE control register bit 2 (Geargrafx `k_huc6260_total_lines[m_blur]`). | source | high (emulator); the bit's meaning matches the documentation as recalled, not re-checked |
| Ninja runs 263 lines: one frame is 1365 × 263 = **358,995** master clocks (119,665 CPU cycles), about 59.83 Hz. A raw 10-frame measurement gave 3,589,953. | source; emulated | high |
| 21.477 MHz / 60 = 357,955 is **not** a frame. Early probes in this project used it; it is 0.3% short, which hid inside 1.5-frame thresholds but would break line-level work. | emulated | high |
| A raster position is (clock − clock at the vblank interrupt) / 1365, in "lines after vblank". The split-timing figures in [LESSONS](LESSONS.md) (69.9, 70.51, 70.9, 71.08) are in this unit. | method | high |

State the unit with every timing number. The Geargrafx save-state clock and
the trace log's cycle counts are both master clocks (see EMULATOR.md).

## CPU and memory map (HuC6280)

| Fact | Basis | Confidence |
| --- | --- | --- |
| Eight MPRs map 8 KiB banks into the 64 KiB address space; `tma`/`tam` read and write them. The opcode's operand is a bit mask of MPRs, but pceas takes the MPR number (`tam #2` assembles to `53 04`). MPR7 (`$E000-$FFFF`) holds bank 0 at reset and carries the vectors, so it is the fixed bank. | documented; game code | high |
| Work RAM is bank `$F8` at `$2000-$3FFF`. Zero page is `$2000-$20FF` and the stack page `$2100-$21FF`. In pceas, `<$11` means zero page `$2011`. | documented; game code | high |
| A 512 KiB card fills banks `$00-$3F`. Geargrafx maps banks `$40-$7F` of such a card to its banks `$20-$3F` (twice). | source | high (emulator); the hardware mirror pattern is documented, not checked here |
| Padding a 512 KiB image with `$FF` to a linear 1 MiB (8 Mbit) image gives 32 new banks (`$40-$7F`) with no mapper. Ninja Enhanced does this and runs on both flash-cart setups above. | hardware (flash carts); emulated | high for flash carts; untested on a real 8 Mbit card |
| Expansion replaces whatever the upper banks mirrored. Before using it on another game, check that the original never reads its own data through the mirror (for Ninja this was never checked; no symptom was seen). | reasoning | open question |
| Images above 1 MiB need the Street Fighter II mapper. | documented | not tested here |
| Bank switching from a hook: put a small trampoline in the fixed bank's unused `$FF` tail. It saves the MPRs it changes (`tma`), maps the code bank (`tam`), calls it and restores them. Ninja's hooks live at bank 0 `$FE00-$FFF5`. | game code; hardware | high |
| Changing MPR2/MPR3 in the main loop is safe only if every interrupt handler that uses those slots saves and restores them. Ninja's audio interrupt code (bank `$38`) does; this was read in its disassembly during the REV6 work (2026-09). Check each game's handlers. | game code | medium |
| Block transfers (`TII`, `TDD`, `TIN`, `TIA`, `TAI`) take only immediate operands. For a data-driven transfer, write the instruction into RAM and call it: Ninja's castle upload writes `$E3` (TIA), source, destination `$0002`, length 32 and `$60` (RTS) at `$2029-$2030`, then patches the source between calls. The RAM must be unused by every interrupt handler; Ninja's is borrowed scratch that the renderer entry saves and restores. | game code; hardware | high |
| A block transfer costs 17 + 6 cycles per byte (more when the target is the VDC and it inserts wait states). Interrupts are held off until it ends. | documented; source (Geargrafx services an IRQ only when no transfer is in progress) | high |
| Measured cost of a 32-byte TIA to the VDC during the active display: about 0.62 lines, against 0.46 lines (209 cycles) without wait states. | emulated | high (emulator) |
| Two back-to-back TIAs held the split interrupt across both blocks; with a NOP or any other instruction between them the latency fell to one block. Whether the interrupt arrived during the first block and was held across the second (a one-instruction sampling delay) was not established. Treat adjacent transfers as one uninterruptible stretch. | emulated | high for the measurement, unknown mechanism |
| Each `st1`/`st2` (immediate store to the VDC data port) is its own instruction, so a long run of them adds no interrupt latency beyond one instruction. | documented; emulated (did not delay the split at all) | high |

## Video display controller (HuC6270)

| Fact | Basis | Confidence |
| --- | --- | --- |
| Ports: `$0000` selects a register (AR), `$0002`/`$0003` are its low and high data bytes. `st0`/`st1`/`st2` write those three ports with an immediate. A VRAM write (VWR) happens when its high byte (`$0003`) is written. | documented; source | high |
| Many games keep a RAM copy of AR, because the interrupt handler selects other registers. Ninja's is zero page `$11`: its scanline handler writes BYR (8) and BXR (7) and then does `lda <$11 / sta $0000`. A hook that does `st0` without updating the shadow first can have an interrupt restore the wrong register before its `st1`/`st2`. Write the shadow before every `st0` (`stz <$11 / st0 #0 / st1 / st2 / lda #2 / sta <$11 / st0 #2`) and restore both on exit. | game code | high for Ninja; find the shadow per game (look after the handler's own `st0` writes) |
| VRAM is 32K 16-bit words (64 KiB); the sprite table (SAT) is 256 words, copied from VRAM by DMA. | source; documented | high |
| MAWR (register 0, write address) and MARR (1, read address) are independent auto-incrementing pointers; VWR and VRR share register number 2. The step is 1, 32, 64 or 128 words (CR bits 11-12). | source; documented | high |
| Reads are prefetched: writing MARR's high byte queues a read into a buffer. Reading `$0002` returns the buffer's low byte and does not advance. Reading `$0003` (with AR = 2) returns the high byte, advances MARR and queues the next read. So reading only the high byte scans BAT palette nibbles (or any high bytes) at half the port cost. | source; game code (Ninja's foreground-preserving redraw relies on it and runs on hardware) | high (emulator), medium (hardware) |
| Writes to MAWR, MARR or VWR wait for a pending VRAM access to finish. | source | high (emulator) |
| A redraw that reads every cell but writes only some must re-seek MAWR before writing again in sequence after any skipped cell, including at every row end, map wrap and BAT wrap. A missing re-seek at a map-row end overwrote foreground in Ninja (LESSONS). | emulated | high |
| The CPU gets VRAM access slots only outside background and sprite fetches during the active display (Geargrafx `IsCpuVramSlotAvailable`; 4 dots per sprite), which is where VDC wait states come from. | source | high (emulator), hardware detail not measured |
| BYR writes are latched per line: Geargrafx latches BYR `k_huc6270_byr_latch_clocks` = 36 clock units before the line's display start, and a later write applies a line later. In Ninja (split at RCR `$6F`) the measured cut-off was between 70.84 (no shift) and 70.97 (one-line shift) lines after vblank. | source; emulated | high (emulator); the hardware latch point is not measured |
| A scanline (RCR) interrupt handler's writes are delayed by the longest uninterruptible stretch running when it fires. Code that runs during the active display beside a raster split must be measured against that split, not just against the frame. | emulated | high |

## Colour encoder (HuC6260 VCE)

| Fact | Basis | Confidence |
| --- | --- | --- |
| 512 palette entries of 9 bits (3 each of G, R, B); `$0402/$0403` set the entry index, `$0404/$0405` write the colour and advance. Entries 0-255 are background palettes (16 × 16), 256-511 sprite palettes. | documented; game code | high |
| Games that fade usually keep a RAM palette buffer and copy it to a fade source, then to the VCE. A colour written only to the VCE is lost at the next fade. Ninja's buffer is `$2286` (32 bytes a palette); Enhanced 2-2 writes its two added palettes to the buffer (`$2426`, `$2446`) and to the VCE. | game code | high for Ninja |

## Cartridge images and identity

| Fact | Basis | Confidence |
| --- | --- | --- |
| Some dumps carry a 512-byte copier header. Geargrafx strips it when the file size has bit 9 set (`size & 512`); the project's tools test `size % 8192 == 512`, which is equivalent for real ROM sizes. | source | high |
| Catalogues list either the headered or the headerless CRC32 (Ninja: `A186DFD2` headered, `67573BAC` headerless). Publish patches for both conventions with identical output. | project practice | high |
| Geargrafx identifies a state's cartridge by the CRC32 of the headerless ROM (see EMULATOR.md for where it sits in a state). | source | high |

## RAM and option design

- **Prove free RAM with a guard, not by inspection.** Fill the candidate range
  with a sentinel, set a read/write watchpoint over it, exercise every
  lifecycle path (boot, menus, every stage entry, combat, death, Continue,
  cinemas) and check that the watchpoint never fired and the sentinel
  survived. Ninja's options live at the bottom of the stack page (`$2100-$2103`)
  and the remaining margin `$2104-$213F` is watched; it is a reserved margin,
  not free RAM, and changes to call depth need the guard rerun. *Basis:
  emulated (REV8-era guards, 2026-09); a watchpoint covers only the paths you
  exercised.*
- **Make zero mean the default.** If the reset code clears RAM, encode options
  so all-zero is the shipped default (Ninja: bit 0 = Original, bit 1 = No
  Damage, so zero = Enhanced with damage). Where a native byte must start
  non-zero, hook the call that follows the RAM clear, set the byte and
  tail-call the original routine (Ninja's English default: `lda #1 / sta $3227
  / jmp $fcbe`, 8 bytes). *Basis: game code; emulated cold-boot and reset
  tests; high.*
- **Reserve a test-stub region.** A debugger test stub once sat at `$FFE6`,
  which production code later took for the English initialization. Write
  stubs to RAM or to a documented reserved range. *Basis: project history.*

## pceas (HuC, commit `54f5c73`)

| Fact | Basis | Confidence |
| --- | --- | --- |
| Indirect addressing uses square brackets: `jmp [table,x]`, `jmp [$2029]`, `lda [$20],y`. `jmp (abs,x)` is a syntax error unless `.opt i+` allows parentheses. | assembler source; observed | high |
| `<` forces zero page, `>` absolute. Zero-page auto-detection is off by default (`.opt a+`). | assembler source | high |
| Out-of-range branches are errors by default. `.opt b+` turns on automatic long branches (`bcc far` becomes `bcs +3 / jmp far`); this project never used it, and its 1.00-era builder rewrote branches by hand. | assembler source | high |
| Every file an `.incbin` or `.include` names must exist at assembly time, even when unused ("Unable to open file"). Generators should write every file their includes name, empty if need be. | observed | high |
| Overlapping `.org` blocks assemble silently. Guard every hand-placed region with `.if (label > limit)` / `.fail`. | observed | high |
| `pceas --raw --pad` emits a headerless image padded with `$FF` to whole banks. The build assembles each module into such an overlay, copies only its declared ranges and rejects any non-`$FF` byte outside them (a stray `$FF` is not detected). | project build (`scripts/project.py`) | high |

## Patching practice

- Hook by replacing a 3-byte absolute instruction with `jsr` to a fixed-bank
  wrapper that re-executes the displaced instruction first, and preserves
  registers, flags, MPRs and borrowed scratch.
- Make a build fail if the base ROM is not what the hook was designed against:
  check the original bytes at each hook site and that target space is still
  `$FF`. When replacing a repeated idiom, search for its exact bytes and
  require the expected count. (Ninja's current build checks the whole
  original by SHA-256 instead.)
- Put an added screen in front of a native sequence instead of editing the
  sequence. Ninja's community notice runs before an untouched publisher scene,
  so that region stays byte-identical to the original and easy to verify; an
  earlier build that shortened the publisher screen was reverted.
