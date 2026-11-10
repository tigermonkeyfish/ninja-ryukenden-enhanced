# Use NES Firewheel logic (1.11-dev)

Emulator evidence (headless Geargrafx `78fc3d7` with the headless-fast patch,
binary SHA-256 `2de50e51…85e9`), not a hardware report. Builds:

| Build | SHA-256 | Source |
| --- | --- | --- |
| 1.10 | `3d5c05df…bbf6` | `build --verify-release` |
| Protection only | `e85c03c1…438d` | commits `7da3181`-`4ad08fa` |
| Final 1.11-dev | `4b07211b…8707` | commit `8c2d557` (this record and the probes follow it; `f660e80a…8601` at `8ca201c` lacked the tally fix) |

Method ([EMULATOR.md](../pc-engine/EMULATOR.md)): one start state, a cold
boot of the original saved at the 1-1 main-loop hook in a session of its own;
every replay is a fresh session that loads it (cartridge CRC retargeted),
enters the stage as Level Select does (`start_stage`) and stops at the first
update. Declared interventions, applied identically to every build: `$2100`
written by the debugger (0 = option off, 4 = on); item pickups by a synthetic
JSR at the gameplay loop (`$8457`) to the native pickup handlers (`$A6A6`
Fire Wheel, `$A6AE`/`$A6B8`/`$A6C2` arts, `$A673` ninpo, `$A67D` time freeze;
the protection sweep called `$A919` directly); stage-timer digits set to 002
for a time-out; a sentinel fill of the stack page for the guard. Scenarios
are stepped by game update (run to `$8457` each time), so an injection lands
at the same point in every build: with frame stepping the update a pickup
lands in varied between sessions by one. Probes:
[`research/tools/nes-firewheel/`](../../research/tools/nes-firewheel).

## Free ROM

Bank 3 `$73FD-$7FFF` (CPU `$D3FD-$DFFF`) is `$FF` in the original. A
read/execute watch over that ROM range stopped 0 times during a cold boot
through the title into 1-1 (683 frames) and all 11 stored runs (35,084
updates) on the original; the same watch over the table read each update
(`$9CA1`) stopped at once (positive control). The module claims
`$DC00-$DFFF` (bank 3 `$7C00-$7FFF`) and uses `$DC00-$DD95` (406 bytes; 618
left), leaving the bytes next to the table at `$D3FC` alone. Every hook site
and the rule were checked for MPR6 = `$03` (and MPR5 = `$02`) at each stop
(451 stops in 1-2: gate 20, rule 20, `$A211` 115, `$AA8A` 109, `$AF2D` 180,
pickups 7). Fixed bank: no new bytes; `$FEBE-$FEDF` (34) and `$FFEE-$FFF5`
(8) remain free, and 2 bytes (`$FE3E-$FE3F`) inside the options range.

Stack low-water marks (sentinel fill below S at the first update): 2-2 with
the wheel, `$21D3` on 1.10, the protection build off and on; the final
build's scenarios `$21D2`-`$21DD` with the option on, `$21D5`-`$21DD` off and
on 1.10. The menu's own mark (`$215B`) is unchanged code.

## Behaviour, option on and off

| NES behaviour | PC Engine (1.10, option off) | Option on | Verified how |
| --- | --- | --- | --- |
| No damage, knockback, hurt state while the wheel is active, from anything | Hurt by enemies it touches before they die, anything it cannot kill, bosses | No damage, no knockback (`$2EAB` never 9) | 2-2 (stored input, wheel at 1150): 1.10 hurt at 1263 by a bullet (type 40) Ryu falls onto at 5 px/update; on: no damage, the bullet still killed that update. Stored 4-1 run picks up a real wheel at 989; 1.10 hurt at 1051 (type 41); on: not. Sweep (protection build) of every contact in the 11 runs with the wheel granted 30/8/2 updates before (78 events, 205 replays): 15 still hurt on 1.10, none with the bit set (2-2 ×2, 4-1, 5-3 ×3, 5-4 boss type 4 ×5, unkillable type 11 ×3, 6-3) |
| Bosses and unkillable objects do not hurt | Hurt | No damage | 1-2 boss (type 0) walked into: 1.10 health 16 → 7, on 16. 6-4 A type 48 (the standing figure; no kill check): 1.10 hurt at 75, 122, 169; on: not hurt while the wheel lasts |
| No grace period at the end | — | Hurt on the first update after the wheel is gone | 6-4 A: wheel present to update 544, hurt at 545 (hurt state 546) |
| Pits and the timer still kill; death clears the wheel | Native; wheel ticks out 10 times after death | Pit and time-out death as 1.10; wheel removed the update health reaches 0 | Time-out with the wheel: health 0 at 193/194, lives 2 → 1 and respawn, traces identical to 1.10 (protection build); final: wheel gone at 194 (1.10: 200). Pit in 2-2 at 1277 with the wheel: death, wheel removed |
| Each frame an overlapping object loses 1 HP; bosses 1 per frame | Ordinary enemies die at once; bosses one point per contact (`$3036`) | Bosses one point every update the wheel touches | 1-2 boss: 16 → 0 in 16 consecutive updates (99-114), then the native defeat and cinema; 1.10: 6 points in 500 updates |
| Hitbox Ryu X-8..X+11 (inclusive), feet-24..feet, any facing | X±20, feet-35..feet+3 | X-9..X+12, feet-25..feet with the native strict tests (same set) | In place: the box routine with 8 positions (x 8/9 borrow, feet 0/24/25 clamp, x > 255): all NES, option off all native |
| 516 frames: 96, then 7 × 60, tick at each | 10 stage-timer ticks (617 updates in the test), tick each | 516 updates, the native tick sound at 96, 156, …, 516 | 1-1 idle: wheel 30-544 (counter 1-515, removed at 516); 1.10 30-647 |
| Timer stops in pause, transitions, intro, tally | Stage-timer driven | Counted only while the stage timer runs | Pause: counter 71 from frame 99 to 299, then on. Area change in 2-2: counter frozen for the 6-frame transition, wheel kept. 1-2 boss beaten at update 114: count held at 86 from 116 through the tally until the stage ends (the native wheel does not tick then either: `$2EDA` is `$FF`) |
| Last 180 frames on alternate frames | Faster spin in the last 3 ticks | Hidden on alternate updates from 337 | 90 hidden updates; screenshots at 400 (hidden) / 401 and 200 (shown) |
| Pickup replaces the art; none at the end | Art kept | Art 6 (none, as after a respawn), HUD icon blank | Shuriken → none at pickup; 1.10 keeps it |
| Pickup clears projectiles and a time freeze | Kept | Removed / ended as its own end does | Shuriken in flight removed at pickup; freeze `$3157` 1 → 0, effect removed |
| Another art or the time freeze ends the wheel; a second wheel restarts it | Wheel kept; two wheels | Removed at once; one wheel, counter reset | Art at 100: wheel gone at 100. Freeze: gone. Second pickup at 230: counter 200 → 2, wheel to 744 (1.10: two wheels) |
| Up+attack: throw pose, no projectile, no cost | Throws the art | Same pose (frame 5) as a throw, no projectile, ninpo unchanged | Ninpo 05 → 05 (1.10: 05 → 02 and a shuriken) |
| Persists across area changes | Persists | Persists | 2-2 area 0 → 1 with the wheel |

With the option off, all 12 scenarios (per-update samples of health, Ryu,
effects, counters, art, freeze, boss, enemies, items, timer, sprites) are
identical to 1.10.

## Regression with the option off

All 11 stored runs (35,084 frames), each recorded in a fresh session from
the one start state with `comparison_video.py`'s `record` method, storing a
SHA-1 of every screenshot instead of the image (probe `rec2.py`):

- **Option off against 1.10:** identical gameplay fields in all 11 runs and
  identical screenshots in every frame (0 of 35,084 differ). The whole-RAM
  hash (outside the comparison's owned bytes) differs in 13 single frames
  (1-1 2, 2-2 1, 4-2 1, 5-2 1, 5-3 2, 5-4 6); in 5-4 these are `$380C`,
  `$380D`, `$380E`, `$38BE` and `$38DF`, the music driver's workspace, one
  frame each (the hooks add a few cycles; the same class of difference as
  1.10 against the original).
- **Option off against the original:** identical gameplay in all 11, as 1.10.
- **Option on:** 10 runs never hold a wheel and are identical to 1.10
  (gameplay and screenshots). The stored 4-1 run picks up a real wheel at
  update 989: from 990 the effect-box scratch (`$2EB3/$2EB4`) differs, the
  hit at 1051 is ignored and the run diverges; its inputs no longer finish
  the stage (expected: they were found with knockback).

Option-off scenarios (12, stepped by update, per-update state) are identical
to 1.10, including the wheel's own life, pickups and boss fights.

`scripts/check_boot.py` on the final build: idle frames 1-899 identical to
the original, first 1-1 update at frame 163 when mashing Run, defaults
English, Enhanced, No Damage off (`$2100` = 0). `scripts/check_menu.py`
passed twice: all 22 Level Select entries and 121 menu openings across the
11 runs (a first pass opened only 8 instead of 21 in 5-3, all passing: the
script frame-steps after state loads, which can shift its replay; the exact
replays above show 5-3 playing as 1.10). The
menu shows `V1.11-DEV`; Run keeps `$2100` bit 2 (the draft copies bits 0-2).

## Not reproduced; open decisions

- **Unkillable types.** Enemy types without a kill check (the audit lists 7,
  8, 11 and 48; 11 appears with the 5-4 boss, 48 is the standing figure of
  6-4 A) stay unkillable; the NES spares nothing. How 48 is beaten was not
  traced, and making these die could break their stages. Recommendation:
  keep, or decide per type after tracing each.
- **Boss death frame.** A 16-point boss dies on the update it reaches 0
  (16 updates of contact); the NES needs a 17th touching frame.
  Recommendation: keep the native death.
- **HUD during the wheel.** The NES shows the wheel as the art; Enhanced
  shows no art (the PC Engine has no wheel art icon). Recommendation: keep.
- **Item containers.** The container check (`$A46C`) calls the same effect
  test (`$AA74`), so the NES box applies to containers, but no container was
  touched in the tests.
- **Sounds.** The NES tick is replaced by the native wheel tick (`$16`);
  whether the last boundary (516) should sound is not stated; it does.
