; Palette modes: $2100 bits 3-5 (1.11-dev). Bits 3-4 are the upload family,
; bit 5 the variant within it:
;   $00 Original (the shipped colours; zero is the default)
;   $08 NES-A, $28 NES-B: other palette data loaded into the RAM palette
;       (the nes-palette branch; uploaded here as Original)
;   $10 GB DMG
;   $18 HELL
;   $38 SMS (stored with bit 7 set: $B8, below)
;   $20, $30: unassigned (uploaded as Original and as GB DMG)
; $2100 bit 7 is set exactly when bits 3-5 are SMS ($38): a copy that lets
; the upload tell SMS from HELL at no cost. The dispatch masks $2100 with
; DISPATCH_BITS ($98: bits 3, 4 and 7) and compares with $10 as before:
; equal is GB DMG; below (carry clear) the native upload (bits 3-4 = 00 or
; 01, whatever bit 5); above (carry set) family 11, HELL ($18 - $10: N clear)
; or SMS ($98 - $10: N set). Whoever writes bits 3-5 writes bit 7 with them
; (the menu does); a stray bit 7 without bits 3-5 = 111 shows SMS colours
; for HELL and HELL's for $20/$28 (no other harm). The menu's PALETTE row
; offers the modes (src/options/menu.txt).
;
; The native game keeps its live palette in RAM ($2286, 512 words) and queues
; ranges to upload ($F350; up to 8 entries at $2260-$2280). The vblank
; interrupt uploads the queue with a TIA ($F3B5, called from $FD13), then
; writes the border colour $2281/$2282 to entry $100; a lock ($2283) holds
; it off. In GB DMG mode during gameplay this module uploads the same queue
; with every colour looked up in the mode's table, so the RAM palette always
; holds the original colours and fades map every step. HELL does the same
; for VCE entries 0 to HELL_MAPPED-1 (background palettes 0-14) only: the HUD
; palette, the sprite palettes and the border (entry $100) keep their
; colours, written by a TIA at the native rate. SMS is GB DMG with the SMS
; table: the very same code runs from a copy of this bank's $5000-$57FF in
; bank SMS_BANK, whose $5400-$57FF holds the SMS table instead of the GB DMG
; one (see "SMS" at the end). Cinemas, the title and the ending ($2240 = 1
; or 2) keep the native upload in every mode.
;
; PALETTE_STATE ($2104, bits 5-7; in $2100 bits 5-7 before SMS) is this
; module's state, not an option. Bit 7 is set while the VCE holds mapped
; colours (GB DMG, HELL or SMS). Whenever the colours due (mapped in a mapped
; mode's gameplay, original otherwise) differ from that state, the vblank
; upload queues all 512 colours ($F394) and flips the bit, so a change
; between Original (or NES) and a mapped mode, or a cinema starting or
; ending, re-uploads everything by itself. The bit does not say which table
; the VCE holds: whoever changes bits 3-5 while a mapped mode is live must
; also queue all 512 colours ($F394; the menu's preview and cancel do).
; Clearing bit 7 costs at most one needless full re-upload. $2104 is the
; byte above $2100-$2103 at the bottom of the stack page (the watched stack
; margin is $2105-$213F since 1.11-dev; docs/validation/sms-palette.md).
;
; The Original and GB DMG paths take exactly the cycles they took before HELL
; existed (the HELL and SMS tests ride on branches those paths already took;
; PALETTE_STATE is read and written with the same absolute instructions as
; $2100 was), so their timing, and that of every interrupt after them, is
; unchanged. HELL's paths take exactly the cycles they took before SMS (see
; vblank_hell, hell_cinema, now_hell_far and now_hell).
;
; The mapped upload costs about 3.5 times the native TIA per colour, so it
; uploads at most PALETTE_CAP colours per vblank, less ENTRY_COST for each
; queue entry after the first (it must end before the display starts), and
; leaves the rest queued: what is left of the entry it stopped in and the
; entries it did not reach become one entry that starts there and runs on,
; past colour 511 to 0 if need be, so the producers keep seven free entries. A
; queue found full (8 entries) may have lost an entry ($F350 drops when full),
; so it is replaced by all 512 colours. In HELL an unmapped colour costs
; about a quarter of a mapped one (RAW_* below), so those entries take about
; the native upload's time.
;
; Fades. The native fade ($F49A, a main-loop tick) recomputes its range of
; the RAM palette from the backup at a brightness FADE_LEVEL ($2A8A) and
; queues the range, every 7 ticks: a fade-in from level 0 up to 7 (then the
; byte is 8), a fade-out from 7 down to 0, all black (then the byte is $FF:
; $F4B6 adds $2A8F = $FF to it after the last step). The stage-end fade-out
; (bank 1 $8510, the only one in gameplay) is followed 8 ticks after its
; last step by the next stage's load, which holds the lock and, starting
; its fade-in ($F436), empties the queue ($F345). With LEFTOVER_CAP colours
; a vblank the last step's 512 colours were still on their way then: the
; load dropped the left-over entry, and the VCE kept the step before black
; in those entries (a hundred of them in 6-2's exit) while the new stage's
; tiles were drawn, until the fade-in's first step reached them. Since the
; dark lift SMS shows that step's greens and greys (6-3's floor, grey on
; the black screen for 7 frames); before, the modes' tables happened to
; show them as their black. So while FADE_LEVEL is $FF (bit 7: a fade-out
; has ended on black and no fade has begun since) a left-over entry gets
; FADE_CAP colours a vblank, still only with the main loop idle at this
; vblank and the last one with work. FADE_CAP is what a fade step's 512
; colours get in their first vblank (0.266 x 512), so in GB DMG and SMS
; those vblanks are no longer than every fade step's first already is (in
; HELL, where the budget also buys unmapped colours, up to 0.4 line longer:
; 19.75 lines after the interrupt at the worst); with that first vblank
; (130 or 136 colours) three more complete the black, at the fourth vblank
; after the step, four ticks before the load (BUDGET_MIN + 4 x FADE_CAP is
; more than 512: the fifth at the latest; docs/validation/dark-lift.md).
; The main loop does nothing but count those ticks. The colours still come
; from the RAM palette through the table: the fade's state changes the
; pace only.

OPTIONS = $2100
DISPATCH_BITS = $98         ; the upload family (bits 3-4) and the SMS copy (bit 7)
PALETTE_GB = $10
PALETTE_HELL = $18          ; family 11: HELL, or SMS with SMS_FLAG
SMS_FLAG = $80              ; $2100 bit 7: bits 3-5 are SMS ($38)
PALETTE_STATE = $2104       ; bits 5-7: this module's state (below)
MASTER_STATE = $2240        ; 0 gameplay, 1 cinema or title, 2 ending
VISIBLE_STAGE = $2e5f       ; Level Select numbering: 0 is 1-1 (HELL's override)
QUEUE_COUNT = $2260
QUEUE_BYTES_LO = $2261      ; bytes to upload (2 per colour)
QUEUE_BYTES_HI = $2269
QUEUE_INDEX_LO = $2271      ; first colour (0-511)
QUEUE_INDEX_HI = $2279
BORDER = $2281              ; written to colour $100 after each upload
FADE_LEVEL = $2a8a          ; the native fade's brightness (below, "Fades")
PALETTE_LOCK = $2283
NATIVE_UPLOAD = $f3b5
QUEUE_ALL = $f394           ; native: queue colours 0-511, under the lock
MAPPED_STATE = $80          ; PALETTE_STATE bit 7: the VCE holds mapped colours
LEFTOVER = $20              ; bit 5: the queue's one entry was left over
WAS_BUSY = $40              ; bit 6: the main loop was busy at the last vblank with work
PALETTE_BANK = $46
PALETTE_FAR = $5a00         ; bank $46 $5A00-$5AFF: fold_queue and the SMS stubs
SMS_BANK = $3b              ; the SMS copy of $5000-$57FF and PALETTE_FAR
HELL_BANK = $43            ; HELL's code and table, mapped in MPR3 ($6000)
HELL_CODE = $7800           ; while they run: bank $43 $7800-$7BFF ...
HELL_TABLE = $7c00          ; ... and $7C00-$7FFF

PALETTE_CAP = 168           ; colours per vblank (measured: docs/validation/gb-palette.md)
ENTRY_COST = 6              ; colours' worth of time per further queue entry
LEFTOVER_CAP = 16           ; colours a vblank for a left-over entry alone
FADE_CAP = 136              ; ... once a fade-out has ended on black ("Fades")
NATIVE_PLUS = 0             ; colours beyond the native upload's time
BUDGET_MIN = 16
; HELL: an unmapped chunk of n colours (a TIA from the RAM palette, at the
; native 42 master clocks a colour) is charged n/4 + n/32 + RAW_SETUP mapped
; colours' worth of the budget (measured: docs/validation/hell-palette.md).
RAW_SETUP = 3
RAW_ANY = 40                ; a budget this large fits any chunk (128: 39)

; Zero page borrowed by the mapped upload; saved and restored around it.
PTR = $20                   ; and $21: source pointer
BUDGET = $22                ; colours left this vblank
CHUNK = $23                 ; colours in this chunk (1-128)
ENTRY = $24                 ; queue entry being read
FULL = $25                  ; nonzero: the queue was full (8 entries)
TMP = $26

; Palette timing (1.11-dev, branch palette-lag; "Palette timing" below).
WAITR = $37c0               ; RAM: the main loop's vblank wait ($37C0-$37DD)
LIVE = $37e0                ; RAM: $10 = mapped gameplay seen by the worker, else 0
FASTOK = $37e1              ; RAM: 1 = every queued colour is in SHADOW
BORDER_MAP = $37e2          ; RAM, 2 bytes: the border colour as the mode shows it
W_LEFT = $37e4              ; RAM, 2 bytes: the worker's bytes left in an entry
W_OVR = $37e6               ; RAM: nonzero = HELL's override applies (stage)
W_INDEX = $37e7             ; RAM, 2 bytes: SHADOW byte offset of the chunk
SHADOW = $3c00              ; RAM, 1 KiB: the mapped colours, as $2286 is laid out
W_SRC = $20                 ; zero page borrowed by the worker (saved, restored)
W_DST = $22
W_Y1 = $24
W_ENTRY = $25
W_MAP = $26
WAIT_ENTRY = $5b00          ; fixed addresses: the boot trampoline (src/bram)
CONFIGURE_ENTRY = $5b03     ; ... and the menu's set_palette (src/options)

 .bank 0
 ; The main loop's vblank wait (native: jsr $fd67): WAITR in RAM (below,
 ; "Palette timing"), the same cycles in every mode.
 .org $e061
 jsr WAITR
 ; The vblank interrupt's palette upload (native: jsr $f3b5).
 .org $fd13
 jsr palette_upload
 ; Fixed-bank trampoline: map the module's bank for the call and restore
 ; MPR2. palette_now (carry set; stage modules) writes colours X to X+Y-1 of
 ; the RAM palette to the VCE at once; palette_upload (carry clear; the
 ; vblank interrupt, which has saved A, X and Y) uploads the queue. A, X and
 ; Y are not preserved.
 .org $febe
palette_now:
 sec
 .db $24                    ; bit <$18: skips the clc
palette_upload:
 clc
 tma #2
 pha
 lda #PALETTE_BANK
 tam #2
 jsr palette_entry
 pla
 tam #2
 rts
palette_upload_end:
 .if (palette_now <> $febe)  ; stage11 and stage22 call $febe
 .fail
 .endif
 .if (palette_upload_end > $fee0)
 .fail
 .endif

 .bank PALETTE_BANK
 ; Everything between the ;@mirror lines is also assembled, byte for byte the
 ; same at the same addresses, in bank SMS_BANK (scripts/palette_tables.py
 ; writes sms-mirror.inc from these lines, every label defined here renamed
 ; sms_..., with a guard that each sms_ label equals its original).
;@mirror begin
 .org $5000
palette_entry:
 ; Cycle counts below (HuC6280, no page-crossing penalties) are those of
 ; the paths before HELL: palette_now reaches its body in 4 (was a bcc not
 ; taken and a jmp: 6), the vblank in 2 + 2 (was a bcc taken: 4).
 bcs palette_now_mapped
 nop
palette_vblank:
 ; As the native upload: nothing happens while the palette is locked
 ; (13 cycles from palette_entry to the rts, as before).
 lda PALETTE_LOCK
 bne entry_return
 ; LIVE (palette timing, 1.11-dev): zero in Original, NES-A/B and cinemas,
 ; $10 in a mapped mode's gameplay once the idle worker has seen it (see
 ; "Palette timing" at the end). Zero: the native upload, reached in 37
 ; cycles from palette_entry as before LIVE existed.
 lda LIVE                   ; 5
 beq vblank_plain           ; 4 taken
 ; Mapped gameplay. FASTOK = 1: the worker has converted every queued
 ; colour into SHADOW, so fast_upload (the native upload, reading SHADOW)
 ; runs, reached in 37 cycles as the native one is.
 dec FASTOK                 ; 7
 bne vblank_fallback        ; 2
 nop
 nop
 nop
 jmp fast_upload            ; 4: 37 cycles
vblank_plain:
 lda PALETTE_STATE          ; 5
 bmi plain_requeue          ; 2
 nop
 nop
 nop
 jmp NATIVE_UPLOAD          ; 4: 37 cycles
plain_requeue:
 ; The VCE holds mapped colours (the mode just changed to Original or NES,
 ; or a cinema began in a mapped mode): queue all 512 colours first, as
 ; cinema_requeue does.
 and #$ff - MAPPED_STATE
 sta PALETTE_STATE
 jsr QUEUE_ALL
 jmp NATIVE_UPLOAD
vblank_fallback:
 ; The worker has not converted the queue (it did not run, or the vblank
 ; came first). An empty queue costs what the native upload's does (46
 ; cycles to its rts); otherwise the mapped upload below, as before.
 lda QUEUE_COUNT            ; 5
 bne fallback_work          ; 2
 stz FASTOK                 ; 5
 sax                        ; 3
 nop                        ; 2: 46 cycles
entry_return:
 rts
fallback_work:
 stz FASTOK
 lda OPTIONS
 and #DISPATCH_BITS
 cmp #PALETTE_GB
 bne fallback_other
 jmp vblank_gb
fallback_other:
 jmp vblank_other           ; HELL, SMS (carry set); Original, NES (clear)

 ; palette_now: colours X (0-255) to X+Y-1 (Y = 1-127) of the RAM palette
 ; to the VCE at once, in the active mode's colours (the stage modules'
 ; merged palettes, which the display shows in the frame they are drawn;
 ; they queue the same range too). The upload lock is held meanwhile so the
 ; vblank upload cannot move the VCE address.
palette_now_mapped:
 lda <PTR
 pha
 lda <PTR+1
 pha
 lda <CHUNK
 pha
 lda PALETTE_LOCK
 pha
 lda #1
 sta PALETTE_LOCK
 tya
 asl a
 sta <CHUNK
 stx $0402
 stz $0403
 stz <PTR+1
 txa
 asl a
 rol <PTR+1
 adc #$86
 sta <PTR
 lda <PTR+1
 adc #$22
 sta <PTR+1
 cly
 lda OPTIONS
 and #DISPATCH_BITS
 cmp #PALETTE_GB
 bne now_other              ; Original, NES (carry clear), HELL, SMS (set)
 nop                        ; GB DMG: the 2 cycles the entry saved
now_gb:
 ; GB DMG, and SMS from now_sms (in bank SMS_BANK, with the SMS table).
 lda MASTER_STATE
 bne now_raw
now_mapped:
 lda [PTR],y
 tax
 iny
 lda [PTR],y
 iny
 lsr a
 bcs now_high
 lda gb_lo0,x
 sta $0404
 lda gb_hi0,x
 sta $0405
 cpy <CHUNK
 bne now_mapped
 bra now_done
now_high:
 lda gb_lo1,x
 sta $0404
 lda gb_hi1,x
 sta $0405
 cpy <CHUNK
 bne now_mapped
 bra now_done
now_hell_far:
 ; HELL (N clear) or SMS (N set). HELL: bank HELL_BANK in MPR3 while
 ; now_hell maps the colours below HELL_MAPPED; it comes back to
 ; now_hell_exit with Y = the bytes done (or, in a cinema, to
 ; now_hell_cinema_exit). The bmi's 2 cycles are paid in now_hell (a sec
 ; it can do without) and now_hell_cinema_exit.
 bmi now_sms_near
 tma #3
 pha
 lda #HELL_BANK
 tam #3
 jmp now_hell
now_sms_near:
 jmp now_sms
now_hell_exit:
 pla
 tam #3
 cpy <CHUNK
 bne now_raw
 bra now_done
now_other:
 bcs now_hell_far           ; Original, NES: 2 cycles, the 2 the entry saved
now_raw:
 lda [PTR],y
 sta $0404
 iny
 lda [PTR],y
 sta $0405
 iny
 cpy <CHUNK
 bne now_raw
now_done:
 pla
 sta PALETTE_LOCK
 pla
 sta <CHUNK
 pla
 sta <PTR+1
 pla
 sta <PTR
 rts

 ; Stack in mapped_upload after its 9 pushes: S+10/11 return to the
 ; trampoline, S+12 its saved MPR2, S+13/14 return to $FD16, S+15-17 the
 ; interrupt's Y, X, A, S+18 P, S+19/20 the interrupted PC.
mapped_upload:
 phx
 phy
 lda <PTR
 pha
 lda <PTR+1
 pha
 lda <BUDGET
 pha
 lda <CHUNK
 pha
 lda <ENTRY
 pha
 lda <FULL
 pha
 lda <TMP
 pha
 ; A full queue may have dropped an entry ($F350 drops when full): once
 ; this upload is done, all 512 colours are left over instead.
 stz <FULL
 lda QUEUE_COUNT
 cmp #8
 bcc queue_not_full
 inc <FULL
queue_not_full:
 lda #PALETTE_CAP
 sta <BUDGET
 ; Was the main loop waiting for vblank when the interrupt came (the
 ; interrupted PC in $FD67-$FD6F)? CHUNK = WAS_BUSY if not, ENTRY = the
 ; same for the last vblank that found work queued ($2100 bit 6).
 ldy #0
 tsx
 lda $2100 + 20,x           ; the interrupted PC, high byte (see below)
 cmp #$fd
 bne busy_now
 lda $2100 + 19,x
 cmp #$67
 bcc busy_now
 cmp #$70
 bcc idle_now
busy_now:
 ldy #WAS_BUSY
idle_now:
 sty <CHUNK
 lda PALETTE_STATE
 and #WAS_BUSY
 sta <ENTRY
 lda PALETTE_STATE
 and #$ff - WAS_BUSY
 ora <CHUNK
 sta PALETTE_STATE
 ; A single entry that an upload left over ($2100 bit 5) is work the native
 ; game does not have in this frame, and the main loop may need the time
 ; (the frames after a large upload are often an area change's load). It
 ; waits while the main loop is busy, or was at the last vblank with work;
 ; otherwise LEFTOVER_CAP colours go (about 4 lines).
 ldx QUEUE_COUNT
 cpx #1
 bne new_work
 lda PALETTE_STATE
 and #LEFTOVER
 beq new_work
 lda <CHUNK
 ora <ENTRY
 beq leftover_idle
 nop                        ; busy: 2 + 2 + 4 cycles, the taken bne and the jmp before 1.11-dev's fade rule
 jmp mapped_return
leftover_idle:
 ; A fade-out that has ended on black (FADE_LEVEL = $FF, below) is followed
 ; by a load that holds the lock and then drops the queue, so what is left
 ; over must be in the VCE before it: FADE_CAP colours go, not LEFTOVER_CAP.
 ; Otherwise this is the path before the rule, cycle for cycle (39 from the
 ; branch above to next_chunk: budget_done's work for the one entry, here).
 bit FADE_LEVEL
 bmi leftover_fade
 lda #LEFTOVER_CAP
leftover_set:
 sta <BUDGET
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 stz <ENTRY
 clx
 jmp next_chunk
leftover_fade:
 lda #FADE_CAP
 bra leftover_set
new_work:
 ; New entries: about the time the native upload would take for them (a
 ; mapped colour costs about 156 master clocks, a native one 42, so 0.266
 ; mapped colours per native one) plus NATIVE_PLUS colours, at most
 ; PALETTE_CAP, less ENTRY_COST for each further entry, at least
 ; BUDGET_MIN. An entry left over in slot 0 is not counted. PTR = the new
 ; entries' bytes.
 stz <PTR
 stz <PTR+1
 ldx #0
 lda PALETTE_STATE
 and #LEFTOVER
 beq sum_bytes
 inx
sum_bytes:
 cpx QUEUE_COUNT
 bcs bytes_summed
 lda QUEUE_BYTES_LO,x
 clc
 adc <PTR
 sta <PTR
 lda QUEUE_BYTES_HI,x
 adc <PTR+1
 sta <PTR+1
 inx
 bra sum_bytes
bytes_summed:
 lda <PTR+1
 sta <TMP                   ; 4 or more: the new entries cover 512 colours
 cmp #8
 bcs budget_large           ; 2048 bytes or more
 ; colours x 0.266 = bytes / 8 + bytes / 128
 lda <PTR
 asl a
 lda <PTR+1
 rol a
 sta <CHUNK                 ; bytes / 128
 lsr <PTR+1
 ror <PTR
 lsr <PTR+1
 ror <PTR
 lsr <PTR+1
 ror <PTR                   ; bytes / 8 (< 256)
 lda <PTR
 clc
 adc <CHUNK
 bcs budget_large
 adc #NATIVE_PLUS
 bcc budget_costs
budget_large:
 lda #$ff
budget_costs:
 cmp #PALETTE_CAP
 bcc budget_capped
 lda #PALETTE_CAP
budget_capped:
 ldx QUEUE_COUNT
 sec
 sbc entry_costs-1,x
 bcc budget_min
 cmp #BUDGET_MIN
 bcs budget_set
budget_min:
 lda #BUDGET_MIN
budget_set:
 sta <BUDGET
 ; Small new entries (a palette animation) go before an entry left over in
 ; slot 0, which moves to the end, so they are not held up behind it. New
 ; entries of 512 colours or more (a fade step) go after it: the left-over
 ; entry then carries on from where it stopped and every colour comes in
 ; turn.
 lda PALETTE_STATE
 and #LEFTOVER
 beq budget_done
 lda <TMP
 cmp #4
 bcs budget_done
 lda QUEUE_BYTES_LO
 pha
 lda QUEUE_BYTES_HI
 pha
 lda QUEUE_INDEX_LO
 pha
 lda QUEUE_INDEX_HI
 pha
 ldx #0
rotate_entry:
 lda QUEUE_BYTES_LO+1,x
 sta QUEUE_BYTES_LO,x
 lda QUEUE_BYTES_HI+1,x
 sta QUEUE_BYTES_HI,x
 lda QUEUE_INDEX_LO+1,x
 sta QUEUE_INDEX_LO,x
 lda QUEUE_INDEX_HI+1,x
 sta QUEUE_INDEX_HI,x
 inx
 cpx QUEUE_COUNT
 bcc rotate_entry
 ldx QUEUE_COUNT
 pla
 sta QUEUE_INDEX_HI-1,x
 pla
 sta QUEUE_INDEX_LO-1,x
 pla
 sta QUEUE_BYTES_HI-1,x
 pla
 sta QUEUE_BYTES_LO-1,x
budget_done:
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 stz <ENTRY
next_entry:
 ldx <ENTRY
 cpx QUEUE_COUNT
 bcs queue_done
next_chunk:
 lda QUEUE_BYTES_LO,x
 ora QUEUE_BYTES_HI,x
 beq entry_done
 ; CHUNK = min(128, colours left in the entry, BUDGET): one pass of the
 ; indexed loop below (Y covers at most 256 bytes).
 lda QUEUE_BYTES_HI,x
 bne entry_long
 lda QUEUE_BYTES_LO,x
 lsr a
 bra entry_short
entry_long:
 lda #128
entry_short:
 sta <CHUNK
 lda <BUDGET
 cmp <CHUNK
 bcs budget_ok
 sta <CHUNK
budget_ok:
 ; ... and no further than colour 511: a left-over entry may run on from
 ; colour 0 (only this upload sees such an entry: whenever the native
 ; upload takes over, all 512 colours are queued first).
 lda QUEUE_INDEX_HI,x
 beq to_end_ok
 lda QUEUE_INDEX_LO,x
 beq to_end_ok
 eor #$ff
 inc a
 cmp <CHUNK
 bcs to_end_ok
 sta <CHUNK
to_end_ok:
 jsr upload_chunk
 ; The entry moves on by CHUNK colours.
 ldx <ENTRY
 lda QUEUE_INDEX_LO,x
 clc
 adc <CHUNK
 sta QUEUE_INDEX_LO,x
 bcc index_done
 lda QUEUE_INDEX_HI,x
 inc a
 and #1
 sta QUEUE_INDEX_HI,x
index_done:
 lda <CHUNK
 asl a
 sta <PTR
 cla
 rol a
 sta <PTR+1
 lda QUEUE_BYTES_LO,x
 sec
 sbc <PTR
 sta QUEUE_BYTES_LO,x
 lda QUEUE_BYTES_HI,x
 sbc <PTR+1
 sta QUEUE_BYTES_HI,x
 lda <BUDGET
 sec
 sbc <CHUNK
 sta <BUDGET
 bne next_chunk
 jsr fold_queue
 bra border
entry_done:
 inc <ENTRY
 bra next_entry
queue_done:
 stz QUEUE_COUNT
border:
 lda <FULL
 beq full_done
 jsr QUEUE_ALL
full_done:
 ; Bit 5: an entry is left over (it was cleared above).
 lda QUEUE_COUNT
 beq nothing_left
 lda PALETTE_STATE
 ora #LEFTOVER
 sta PALETTE_STATE
nothing_left:
 ; The border colour (entry $100), mapped like the rest.
 stz $0402
 lda #1
 sta $0403
 ldx BORDER
 lda BORDER+1
 lsr a
 bcs border_high
 lda gb_lo0,x
 sta $0404
 lda gb_hi0,x
 sta $0405
 bra mapped_return
border_high:
 lda gb_lo1,x
 sta $0404
 lda gb_hi1,x
 sta $0405
mapped_return:
 pla
 sta <TMP
 pla
 sta <FULL
 pla
 sta <ENTRY
 pla
 sta <CHUNK
 pla
 sta <BUDGET
 pla
 sta <PTR+1
 pla
 sta <PTR
 ply
 plx
 rts
entry_costs:
 .db 0, ENTRY_COST, 2 * ENTRY_COST, 3 * ENTRY_COST
 .db 4 * ENTRY_COST, 5 * ENTRY_COST, 6 * ENTRY_COST, 7 * ENTRY_COST

 ; Upload CHUNK colours (1-128) of queue entry X, mapped, from its first
 ; colour. Y runs from -2 x CHUNK up to 0 with
 ; PTR = $2286 + 2 x (first colour + CHUNK) - 256.
upload_chunk:
 lda QUEUE_INDEX_LO,x
 sta $0402
 lda QUEUE_INDEX_HI,x
 sta $0403
 lda QUEUE_INDEX_LO,x
 clc
 adc <CHUNK
 sta <PTR
 lda QUEUE_INDEX_HI,x
 adc #0
 asl <PTR
 rol a
 sta <PTR+1
 lda <PTR
 clc
 adc #$86
 sta <PTR
 lda <PTR+1
 adc #$21
 sta <PTR+1
 lda <CHUNK
 asl a
 eor #$ff
 inc a
 tay
upload_colour:
 lda [PTR],y
 tax
 iny
 lda [PTR],y
 lsr a
 bcs upload_high
 lda gb_lo0,x
 sta $0404
 lda gb_hi0,x
 sta $0405
 iny
 bne upload_colour
 rts
upload_high:
 lda gb_lo1,x
 sta $0404
 lda gb_hi1,x
 sta $0405
 iny
 bne upload_colour
 rts

 ; The mapped upload's dispatch (the fallback since palette-lag).
vblank_gb:
 ; GB DMG, and SMS from vblank_sms (in bank SMS_BANK, with the SMS table).
 lda MASTER_STATE
 bne vblank_cinema
 ; GB DMG in gameplay. If the VCE still holds original colours (bit 7
 ; clear: the mode was just chosen, or a cinema or the title just ended),
 ; queue all 512 colours ($F394) first.
 lda PALETTE_STATE
 bmi mapped_state
 ora #MAPPED_STATE
 sta PALETTE_STATE
 bra queue_everything
mapped_state:
 lda QUEUE_COUNT
 bne queue_present
 ; Nothing queued, so nothing is left over either.
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 rts
queue_present:
 jmp mapped_upload          ; 4 cycles, as the bra it replaces
queue_everything:
 jsr QUEUE_ALL
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 jmp mapped_upload
vblank_other:
 ; Original or NES (carry clear) in 2 + 5 + 2 + 4 cycles, as the 5 + 4 + 4
 ; of the lda/bpl/jmp before HELL; HELL (carry set) has its own path.
 ; (With bit 7 set, the mode just changed to Original, the requeue below
 ; starts 4 cycles later than before HELL.)
 bcs vblank_hell
 lda PALETTE_STATE
 bmi cinema_requeue
 jmp NATIVE_UPLOAD
vblank_hell:
 ; HELL (N clear) or SMS (N set: $2100 bit 7), from the compare above.
 ; HELL's code and table are in bank HELL_BANK, mapped in MPR3 until it
 ; leaves by hell_done, which puts MPR3 back (code running in MPR3 cannot
 ; unmap itself). Cycles from the bcs, as before SMS: gameplay reaches
 ; hell_gameplay in 31 (then: tma/pha/lda/tam/jmp, and in bank HELL_BANK
 ; lda $2240 and a taken beq; now: a bmi, lda $2240 and a bne not taken,
 ; then tma/pha/lda/tam/jmp); a cinema reaches vblank_cinema in 42.
 bmi vblank_sms_near
 lda MASTER_STATE
 bne hell_cinema
 tma #3
 pha
 lda #HELL_BANK
 tam #3
 jmp hell_gameplay
hell_cinema:
 ; 27 cycles, so HELL's cinema vblank is as long as before SMS (when it
 ; mapped bank HELL_BANK, tested $2240 there and came back through here).
 tma #3                     ; 4
 pha                        ; 3
 pla                        ; 4
 tam #3                     ; 5: MPR3 as it was
 lda MASTER_STATE           ; 5
 nop                        ; 2
 nop                        ; 2
 nop                        ; 2
vblank_cinema:
 ; GB DMG or HELL in a cinema, the title or the ending: original colours.
 ; If the VCE holds mapped ones (bit 7 set: a cinema just began, or the
 ; mode was just changed), queue all 512 colours first.
 lda PALETTE_STATE
 bpl native_upload
cinema_requeue:
 and #$ff - MAPPED_STATE
 sta PALETTE_STATE
 jsr QUEUE_ALL
native_upload:
 jmp NATIVE_UPLOAD
hell_done:
 pla
 tam #3
upload_return:
 rts
vblank_sms_near:
 jmp vblank_sms

palette_code_end:
 .if (palette_code_end > $5400)
 .fail
 .endif
;@mirror end

 ; The GB DMG table (generated from gb-dmg.json by scripts/palette_tables.py):
 ; four pages, the mapped colour's low and high byte for colours $000-$0FF
 ; and $100-$1FF, indexed by the colour's low byte.
 .org $5400
 .include "gb-table.inc"
palette_tables_end:
 .if (palette_tables_end > $5800)
 .fail
 .endif

 ; Bank $46 $5A00-$5AFF (file offsets $8DA00-$8DAFF), the unused tail of
 ; the speed module's old claim ($5900-$5FFF; its fixed code ends at $598E;
 ; since 1.11-dev speed claims $5900-$59FF): code reached only by jsr or
 ; jmp, so it costs the same cycles here. Mirrored in bank SMS_BANK, where
 ; vblank_sms and now_sms go on after their tam #2.
;@mirror begin
 .org PALETTE_FAR
 ; The budget ran out in entry X: what is left of it and the entries after
 ; it become one entry that starts where the upload stopped and runs on
 ; (past colour 511 to 0) far enough to cover them all, at most 512 colours,
 ; so the producers keep seven free entries and every colour comes in turn.
 ; PTR = its first colour, BUDGET:CHUNK its length E, ENTRY:TMP scratch.
fold_queue:
 cpx QUEUE_COUNT
 bcs fold_none
 lda QUEUE_BYTES_LO,x
 ora QUEUE_BYTES_HI,x
 bne fold_start
 inx
 bra fold_queue
fold_none:
 stz QUEUE_COUNT
 rts
fold_start:
 lda QUEUE_INDEX_LO,x
 sta <PTR
 lda QUEUE_INDEX_HI,x
 sta <PTR+1
 stz <CHUNK
 stz <BUDGET
fold_entry:
 lda QUEUE_BYTES_LO,x
 ora QUEUE_BYTES_HI,x
 beq fold_next
 ; e = ((first colour - PTR) mod 512) + colours, at most 512
 lda QUEUE_INDEX_LO,x
 sec
 sbc <PTR
 sta <TMP
 lda QUEUE_INDEX_HI,x
 sbc <PTR+1
 and #1
 sta <ENTRY
 lda QUEUE_BYTES_HI,x
 lsr a
 tay
 lda QUEUE_BYTES_LO,x
 ror a
 clc
 adc <TMP
 sta <TMP
 tya
 adc <ENTRY
 sta <ENTRY
 cmp #2
 bcc fold_max
 lda #2
 sta <ENTRY
 stz <TMP
fold_max:
 lda <CHUNK
 cmp <TMP
 lda <BUDGET
 sbc <ENTRY
 bcs fold_next
 lda <TMP
 sta <CHUNK
 lda <ENTRY
 sta <BUDGET
fold_next:
 inx
 cpx QUEUE_COUNT
 bcc fold_entry
 lda <PTR
 sta QUEUE_INDEX_LO
 lda <PTR+1
 sta QUEUE_INDEX_HI
 asl <CHUNK
 rol <BUDGET
 lda <CHUNK
 sta QUEUE_BYTES_LO
 lda <BUDGET
 sta QUEUE_BYTES_HI
 lda #1
 sta QUEUE_COUNT
 rts

vblank_sms:
 ; SMS: the GB DMG path, run from bank SMS_BANK (the same code, the SMS
 ; table at $5400); the trampoline puts MPR2 back when it returns.
 lda #SMS_BANK
 tam #2
 jmp vblank_gb
now_sms:
 ; SMS: GB DMG's palette_now from bank SMS_BANK (from now_hell_far: Y = 0,
 ; PTR, CHUNK and the VCE address set, the lock held).
 lda #SMS_BANK
 tam #2
 jmp now_gb
now_hell_cinema_exit:
 ; palette_now in HELL in a cinema (Y = 0, so now_hell_exit's cpy/bne would
 ; go on to now_raw): 2 cycles less than that way, for now_hell_far's bmi.
 pla
 tam #3
 nop
 jmp now_raw
palette_far_end:
 .if (palette_far_end > PALETTE_FAR + $100)
 .fail
 .endif
;@mirror end

 ; ---------------------------------------------------------------------
 ; Palette timing (1.11-dev, branch palette-lag; docs/validation/palette-lag.md).
 ;
 ; The mapped modes (GB DMG, HELL, SMS) used to map every queued colour in
 ; the vblank interrupt: 3.6 times the native upload's time a colour, taken
 ; from the update that follows. Now the main loop's idle time does it. The
 ; main loop's only vblank wait (bank 0 $E061, jsr $FD67) calls WAITR, a
 ; copy of the native wait in RAM: in Original, NES-A, NES-B (and the
 ; unassigned values with bit 4 clear) it is the native code byte for byte
 ; ($FD67-$FD6F), so those modes run exactly as before. In a mapped mode
 ; WAITR, after the same STZ $12, calls the worker when the queue holds
 ; work; the worker converts every queued colour from the RAM palette into
 ; SHADOW (the same layout, mapped) and sets FASTOK. At the vblank the
 ; upload then is fast_upload: the native upload ($F3B5-$F421) instruction
 ; for instruction, reading SHADOW instead of $2286 and the border from
 ; BORDER_MAP, reached in the same 37 cycles as the native one, so the
 ; vblank costs what Original's costs. If the worker did not finish before
 ; the vblank (no idle time, or no wait at all), the mapped upload of
 ; before runs (the fallback).
 ;
 ; With an empty queue WAITR spends 10 cycles (tst/bne) before the native
 ; loop: a multiple of the loop's 10, so the loop's exit after the vblank
 ; interrupt is at the same cycle as Original's (unless the vblank comes
 ; within those 10 cycles of the STZ).
 ;
 ; RAM: $37C0-$37E8 and SHADOW $3C00-$3FFF, never read or written by the
 ; original game or 1.11-dev before this (docs/validation/palette-lag.md,
 ; "RAM audit"). The RAM clear zeroes them; palette_boot writes WAITR before
 ; the main loop first runs.
 .org $5b00
 jmp palette_boot           ; WAIT_ENTRY: src/bram's reset trampoline
 jmp palette_configure      ; CONFIGURE_ENTRY: src/options's set_palette

palette_boot:
 ; The reset (interrupts off, MPR2 = this bank): the saved settings
 ; (src/bram, its entry $4B00), then WAITR for the mode loaded. A, X, Y
 ; and the flags as the settings loader left them.
 jsr $4b00

 ; WAITR and LIVE for $2100's mode (bit 4: GB DMG, HELL, SMS). After any
 ; change of $2100 bits 3-5 (the menu's set_palette; the reset). A, X, Y
 ; and the flags are kept.
palette_configure:
 php
 pha
 phx
 lda OPTIONS
 and #$10
 beq configure_plain
 ldx #wait_mapped_end - wait_mapped - 1
configure_mapped:
 lda wait_mapped,x
 sta WAITR,x
 dex
 bpl configure_mapped
 bra configure_done
configure_plain:
 ldx #wait_plain_end - wait_plain - 1
configure_copy:
 lda wait_plain,x
 sta WAITR,x
 dex
 bpl configure_copy
 stz LIVE
configure_done:
 stz FASTOK
 plx
 pla
 plp
 rts

wait_plain:
 ; $FD67-$FD6F byte for byte, at WAITR.
 .db $64, $12               ; stz <$12
 .db $a5, $12               ; lda <$12
 .db $c9, $01               ; cmp #1
 .db $90, $fa               ; bcc (lda)
 .db $60                    ; rts
wait_plain_end:
wait_mapped:
 .db $64, $12               ; $37C0 stz <$12
 .db $93, $ff, $60, $22     ; $37C2 tst #$ff, $2260: 8 cycles
 .db $d0, $07               ; $37C6 bne $37CF (not taken: 2)
 .db $a5, $12               ; $37C8 lda <$12
 .db $c9, $01               ; $37CA cmp #1
 .db $90, $fa               ; $37CC bcc $37C8
 .db $60                    ; $37CE rts
 .db $43, $04               ; $37CF tma #2
 .db $48                    ; $37D1 pha
 .db $a9, PALETTE_BANK      ; $37D2 lda #PALETTE_BANK
 .db $53, $04               ; $37D4 tam #2
 .db $20, LOW(worker), HIGH(worker) ; $37D6 jsr worker
 .db $68                    ; $37D9 pla
 .db $53, $04               ; $37DA tam #2
 .db $80, $ea               ; $37DC bra $37C8
wait_mapped_end:
 .if (wait_mapped_end - wait_mapped <> $1e)
 .fail
 .endif

 ; The native upload ($F3B5-$F421) instruction for instruction, reading
 ; the colours from SHADOW and the border from BORDER_MAP: the same cycles
 ; for the same queue. Reached from palette_entry in 37 cycles, as $F3B5.
fast_upload:
 lda QUEUE_COUNT
 beq fast_return
 lda PALETTE_LOCK
 bne fast_return
 phx
 phy
 lda #$04
 sta $2208
 lda #$04
 sta $2209
 cly
fast_entry:
 lda QUEUE_INDEX_LO,y
 sta $0402
 asl a
 sta $2284
 lda QUEUE_INDEX_HI,y
 sta $0403
 rol a
 sta $2285
 lda $2284
 clc
 adc #LOW(SHADOW)
 sta $2206
 lda $2285
 adc #HIGH(SHADOW)
 sta $2207
 lda QUEUE_BYTES_LO,y
 sta $220a
 lda QUEUE_BYTES_HI,y
 sta $220b
 lda #$e3
 sta $2205
 jsr $2205
 iny
 dec QUEUE_COUNT
 bne fast_entry
 stz $0402
 lda #$01
 sta $0403
 lda BORDER_MAP
 sta $0404
 lda BORDER_MAP+1
 sta $0405
 ply
 plx
fast_return:
 rts

 ; The worker: from WAITR (main loop, interrupts on, MPR2 = this bank) when
 ; the queue holds work, after the update. Sets LIVE (0 in a cinema, $10 in
 ; gameplay) and, when it converts every queued colour before the vblank
 ; comes ($12 is checked before each colour), FASTOK = 1. X and Y are kept;
 ; the zero page it borrows and MPR3 are put back. Exit latency when the
 ; vblank comes in the middle: the colour under way, then the restores.
worker:
 phx
 phy
 stz FASTOK
 lda MASTER_STATE
 beq worker_gameplay
 stz LIVE                   ; cinema, title, ending: the native upload
 ply
 plx
 rts
worker_gameplay:
 lda #$10
 sta LIVE
 lda PALETTE_LOCK
 beq worker_unlocked
 jmp worker_exit            ; locked: no upload at this vblank anyway
worker_unlocked:
 lda PALETTE_STATE
 bmi worker_vce_mapped
 ; The VCE holds original colours (the mode was chosen, or a cinema or
 ; the title ended): all 512 colours, as the mapped upload's
 ; queue_everything does.
 jsr QUEUE_ALL
 lda PALETTE_STATE
 ora #MAPPED_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 bra worker_convert
worker_vce_mapped:
 and #LEFTOVER
 beq worker_convert
 ; An entry the fallback left over (slot 0; it may run past colour 511 to
 ; 0): split it at 511 into two entries the native upload's layout can
 ; take (all 512 colours when the queue has no room), so the fast upload
 ; carries it on.
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 lda QUEUE_INDEX_LO
 asl a
 sta W_INDEX
 lda QUEUE_INDEX_HI
 and #1
 rol a
 sta W_INDEX+1              ; 2 x first colour
 lda #LOW(1024)
 sec
 sbc W_INDEX
 sta W_LEFT
 lda #HIGH(1024)
 sbc W_INDEX+1
 sta W_LEFT+1               ; bytes up to colour 511
 cmp QUEUE_BYTES_HI
 bcc worker_split
 bne worker_convert
 lda W_LEFT
 cmp QUEUE_BYTES_LO
 bcs worker_convert         ; it does not run past 511
worker_split:
 ldx QUEUE_COUNT
 cpx #8
 bcs worker_split_full
 lda QUEUE_BYTES_LO
 sec
 sbc W_LEFT
 sta QUEUE_BYTES_LO,x
 lda QUEUE_BYTES_HI
 sbc W_LEFT+1
 sta QUEUE_BYTES_HI,x
 stz QUEUE_INDEX_LO,x
 stz QUEUE_INDEX_HI,x
 inc QUEUE_COUNT
 lda W_LEFT
 sta QUEUE_BYTES_LO
 lda W_LEFT+1
 sta QUEUE_BYTES_HI
 bra worker_convert
worker_split_full:
 jsr QUEUE_ALL
 bra worker_convert
worker_exit:
 ply
 plx
 rts
worker_convert:
 lda <W_SRC
 pha
 lda <W_SRC+1
 pha
 lda <W_DST
 pha
 lda <W_DST+1
 pha
 lda <W_Y1
 pha
 lda <W_ENTRY
 pha
 lda <W_MAP
 pha
 tma #3
 pha
 ; The table in MPR3 ($7400: GB DMG's bank $46 $5400 or SMS's bank $3B
 ; $5400; $7C00: HELL's bank $43 $7C00) and W_MAP = 0 GB DMG / SMS, 1 HELL.
 stz <W_MAP
 stz W_OVR
 lda OPTIONS
 and #DISPATCH_BITS
 cmp #PALETTE_GB
 beq worker_gb
 lda OPTIONS
 bmi worker_sms
 lda #HELL_BANK
 tam #3
 inc <W_MAP
 lda VISIBLE_STAGE
 cmp #HELL_OVERRIDE_STAGE
 bne worker_entries
 inc W_OVR
 bra worker_entries
worker_sms:
 lda #SMS_BANK
 tam #3
 bra worker_entries
worker_gb:
 lda #PALETTE_BANK
 tam #3
worker_entries:
 stz <W_ENTRY
worker_entry:
 ldx <W_ENTRY
 cpx QUEUE_COUNT
 bcc worker_entry_go
 jmp worker_border
worker_entry_go:
 ; W_INDEX = 2 x first colour (0-1022), W_LEFT = bytes (at most to colour
 ; 511: entries never run past it except one the fallback left over,
 ; which the worker does not take).
 lda QUEUE_INDEX_LO,x
 asl a
 sta W_INDEX
 lda QUEUE_INDEX_HI,x
 and #1
 rol a
 sta W_INDEX+1
 lda QUEUE_BYTES_LO,x
 sta W_LEFT
 lda QUEUE_BYTES_HI,x
 sta W_LEFT+1
 ; clamp: W_LEFT <= 1024 - W_INDEX
 lda #LOW(1024)
 sec
 sbc W_INDEX
 sta <W_Y1
 lda #HIGH(1024)
 sbc W_INDEX+1
 cmp W_LEFT+1
 bcc worker_clamp
 bne worker_chunk
 lda <W_Y1
 cmp W_LEFT
 bcs worker_chunk
worker_clamp:
 lda <W_Y1
 sta W_LEFT
 lda #HIGH(1024)
 sec
 sbc W_INDEX+1
 sta W_LEFT+1
 lda W_INDEX
 beq worker_chunk
 dec W_LEFT+1
worker_chunk:
 ; One chunk of at most 256 bytes: Y from 0 to W_Y1 (0 = 256).
 lda W_LEFT
 ora W_LEFT+1
 bne worker_chunk_go
 inc <W_ENTRY
 bra worker_entry
worker_chunk_go:
 lda W_INDEX
 clc
 adc #$86
 sta <W_SRC
 lda W_INDEX+1
 adc #$22
 sta <W_SRC+1
 lda W_INDEX
 sta <W_DST
 lda W_INDEX+1
 clc
 adc #HIGH(SHADOW)
 sta <W_DST+1
 lda W_LEFT+1
 beq worker_short
 stz <W_Y1                  ; 256 bytes
 bra worker_sized
worker_short:
 lda W_LEFT
 sta <W_Y1
worker_sized:
 cly
 lda <W_MAP
 bne worker_hell
 jsr convert_table
 bcs worker_abort
 bra worker_advance
worker_hell:
 jsr convert_hell
 bcs worker_abort
worker_advance:
 ; W_INDEX += chunk, W_LEFT -= chunk (chunk = W_Y1, 0 = 256).
 lda <W_Y1
 beq worker_advance_page
 clc
 adc W_INDEX
 sta W_INDEX
 bcc worker_advance_index
 inc W_INDEX+1
worker_advance_index:
 lda W_LEFT
 sec
 sbc <W_Y1
 sta W_LEFT
 bcs worker_chunk
 dec W_LEFT+1
 bra worker_chunk
worker_advance_page:
 inc W_INDEX+1
 dec W_LEFT+1
 jmp worker_chunk
worker_border:
 ; The border colour (entry $100): mapped in GB DMG and SMS, as the
 ; mapped upload writes it; HELL keeps it (a sprite-palette entry).
 lda <W_MAP
 bne worker_border_raw
 ldx BORDER
 lda BORDER+1
 lsr a
 bcs worker_border_high
 lda $7400,x
 sta BORDER_MAP
 lda $7500,x
 sta BORDER_MAP+1
 bra worker_done
worker_border_high:
 lda $7600,x
 sta BORDER_MAP
 lda $7700,x
 sta BORDER_MAP+1
 bra worker_done
worker_border_raw:
 lda BORDER
 sta BORDER_MAP
 lda BORDER+1
 sta BORDER_MAP+1
worker_done:
 lda #1
 sta FASTOK
worker_abort:
 pla
 tam #3
 pla
 sta <W_MAP
 pla
 sta <W_ENTRY
 pla
 sta <W_Y1
 pla
 sta <W_DST+1
 pla
 sta <W_DST
 pla
 sta <W_SRC+1
 pla
 sta <W_SRC
 ply
 plx
 rts

 ; Convert bytes Y..W_Y1 (0 = 256) of [W_SRC] into [W_DST] through the
 ; table in MPR3 at $7400. Carry set: the vblank came ($12 nonzero) and it
 ; stopped before a colour.
convert_table:
 lda <$12
 bne convert_stop
 lda [W_SRC],y
 tax
 iny
 lda [W_SRC],y
 lsr a
 bcs convert_table_high
 lda $7500,x
 sta [W_DST],y
 dey
 lda $7400,x
 sta [W_DST],y
 iny
 iny
 cpy <W_Y1
 bne convert_table
 clc
 rts
convert_table_high:
 lda $7700,x
 sta [W_DST],y
 dey
 lda $7600,x
 sta [W_DST],y
 iny
 iny
 cpy <W_Y1
 bne convert_table
 clc
 rts
convert_stop:
 sec
 rts

 ; HELL: bytes below SHADOW offset 2 x HELL_MAPPED through the table at
 ; $7C00 (with the stage override), the rest copied.
convert_hell:
 lda <$12
 bne convert_stop
 ; this colour's SHADOW offset: W_INDEX + Y, mapped below 2 x HELL_MAPPED
 tya
 clc
 adc W_INDEX
 sta <W_MAP+0               ; scratch (W_MAP is 1 here; restored below)
 lda W_INDEX+1
 adc #0
 cmp #HIGH(2 * HELL_MAPPED)
 bcc convert_hell_mapped
 bne convert_hell_raw
 lda <W_MAP
 cmp #LOW(2 * HELL_MAPPED)
 bcc convert_hell_mapped
convert_hell_raw:
 lda #1
 sta <W_MAP
 lda [W_SRC],y
 sta [W_DST],y
 iny
 lda [W_SRC],y
 sta [W_DST],y
 iny
 cpy <W_Y1
 bne convert_hell
 clc
 rts
convert_hell_mapped:
 lda #1
 sta <W_MAP
 lda [W_SRC],y
 tax
 iny
 lda [W_SRC],y
 lsr a
 bcs convert_hell_high
 lda W_OVR
 beq convert_hell_low
 cpx #HELL_OVERRIDE_KEY
 bne convert_hell_low
 lda #HELL_OVERRIDE_HI
 sta [W_DST],y
 dey
 lda #HELL_OVERRIDE_LO
 sta [W_DST],y
 bra convert_hell_next
convert_hell_low:
 lda $7d00,x
 sta [W_DST],y
 dey
 lda $7c00,x
 sta [W_DST],y
 bra convert_hell_next
convert_hell_high:
 lda $7f00,x
 sta [W_DST],y
 dey
 lda $7e00,x
 sta [W_DST],y
convert_hell_next:
 iny
 iny
 cpy <W_Y1
 bne convert_hell
 clc
 rts
timing_end:
 .if (timing_end > $6000)
 .fail
 .endif

 ; HELL, in bank $43 $7800-$7FFF (file offsets $87800-$87FFF): the tail of
 ; stage11's last data bank, which its generator can never reach (phases 6
 ; and 7 of at most 83 pairs end by $74C0; claimed by this module since
 ; 1.11-dev, docs/validation/hell-palette.md). Mapped in MPR3 while it runs;
 ; every way out restores MPR3 from the byte vblank_hell or now_hell_far
 ; pushed.
 .bank HELL_BANK
 .org HELL_CODE
hell_gameplay:
 ; HELL in gameplay (from vblank_hell: mapped_upload's stack depth plus
 ; MPR3's byte).
 ; If the VCE holds original colours (bit 7 clear: the mode was just
 ; chosen, or a cinema or the title just ended), queue all 512 first.
 lda PALETTE_STATE
 bmi hell_mapped_state
 ora #MAPPED_STATE
 sta PALETTE_STATE
 jsr QUEUE_ALL
 bra hell_fresh
hell_mapped_state:
 lda QUEUE_COUNT
 bne hell_upload
hell_fresh:
 ; Nothing queued, so nothing is left over either (or all 512 colours were
 ; just queued afresh).
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 lda QUEUE_COUNT
 bne hell_upload
 jmp hell_done

 ; As mapped_upload (the same budget rules; the stack one byte deeper), but each
 ; chunk stops at HELL_MAPPED: below it the colours are looked up in the
 ; HELL table and cost a budget colour each; from it on they go to the VCE
 ; unchanged by a TIA and cost RAW_SETUP + n/4 + n/32 for n colours.
hell_upload:
 phx
 phy
 lda <PTR
 pha
 lda <PTR+1
 pha
 lda <BUDGET
 pha
 lda <CHUNK
 pha
 lda <ENTRY
 pha
 lda <FULL
 pha
 lda <TMP
 pha
 stz <FULL
 lda QUEUE_COUNT
 cmp #8
 bcc hell_not_full
 inc <FULL
hell_not_full:
 lda #PALETTE_CAP
 sta <BUDGET
 ldy #0
 tsx
 lda $2100 + 21,x           ; the interrupted PC (mapped_upload's S+20, +1)
 cmp #$fd
 bne hell_busy_now
 lda $2100 + 20,x
 cmp #$67
 bcc hell_busy_now
 cmp #$70
 bcc hell_idle_now
hell_busy_now:
 ldy #WAS_BUSY
hell_idle_now:
 sty <CHUNK
 lda PALETTE_STATE
 and #WAS_BUSY
 sta <ENTRY
 lda PALETTE_STATE
 and #$ff - WAS_BUSY
 ora <CHUNK
 sta PALETTE_STATE
 ldx QUEUE_COUNT
 cpx #1
 bne hell_new_work
 lda PALETTE_STATE
 and #LEFTOVER
 beq hell_new_work
 lda <CHUNK
 ora <ENTRY
 beq hell_leftover_idle
 nop                        ; busy: 8 cycles, as before the fade rule
 jmp hell_return
hell_leftover_idle:
 ; mapped_upload's fade rule (leftover_idle): FADE_CAP for what is left
 ; over once a fade-out has ended on black. Otherwise 45 cycles from the
 ; branch above to hell_next_chunk, as before the rule (the three nops).
 bit FADE_LEVEL
 bmi hell_leftover_fade
 lda #LEFTOVER_CAP
hell_leftover_set:
 sta <BUDGET
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 stz <ENTRY
 clx
 nop
 nop
 nop
 jmp hell_next_chunk
hell_leftover_fade:
 lda #FADE_CAP
 bra hell_leftover_set
hell_new_work:
 stz <PTR
 stz <PTR+1
 ldx #0
 lda PALETTE_STATE
 and #LEFTOVER
 beq hell_sum
 inx
hell_sum:
 cpx QUEUE_COUNT
 bcs hell_summed
 lda QUEUE_BYTES_LO,x
 clc
 adc <PTR
 sta <PTR
 lda QUEUE_BYTES_HI,x
 adc <PTR+1
 sta <PTR+1
 inx
 bra hell_sum
hell_summed:
 lda <PTR+1
 sta <TMP
 cmp #8
 bcs hell_large
 lda <PTR
 asl a
 lda <PTR+1
 rol a
 sta <CHUNK
 lsr <PTR+1
 ror <PTR
 lsr <PTR+1
 ror <PTR
 lsr <PTR+1
 ror <PTR
 lda <PTR
 clc
 adc <CHUNK
 bcs hell_large
 adc #NATIVE_PLUS
 bcc hell_costs
hell_large:
 lda #$ff
hell_costs:
 cmp #PALETTE_CAP
 bcc hell_capped
 lda #PALETTE_CAP
hell_capped:
 ldx QUEUE_COUNT
 sec
 sbc entry_costs-1,x
 bcc hell_min
 cmp #BUDGET_MIN
 bcs hell_set
hell_min:
 lda #BUDGET_MIN
hell_set:
 sta <BUDGET
 lda PALETTE_STATE
 and #LEFTOVER
 beq hell_budget_done
 lda <TMP
 cmp #4
 bcs hell_budget_done
 lda QUEUE_BYTES_LO
 pha
 lda QUEUE_BYTES_HI
 pha
 lda QUEUE_INDEX_LO
 pha
 lda QUEUE_INDEX_HI
 pha
 ldx #0
hell_rotate:
 lda QUEUE_BYTES_LO+1,x
 sta QUEUE_BYTES_LO,x
 lda QUEUE_BYTES_HI+1,x
 sta QUEUE_BYTES_HI,x
 lda QUEUE_INDEX_LO+1,x
 sta QUEUE_INDEX_LO,x
 lda QUEUE_INDEX_HI+1,x
 sta QUEUE_INDEX_HI,x
 inx
 cpx QUEUE_COUNT
 bcc hell_rotate
 ldx QUEUE_COUNT
 pla
 sta QUEUE_INDEX_HI-1,x
 pla
 sta QUEUE_INDEX_LO-1,x
 pla
 sta QUEUE_BYTES_HI-1,x
 pla
 sta QUEUE_BYTES_LO-1,x
hell_budget_done:
 lda PALETTE_STATE
 and #$ff - LEFTOVER
 sta PALETTE_STATE
 stz <ENTRY
 bra hell_next_entry
hell_entry_done:
 inc <ENTRY
hell_next_entry:
 ldx <ENTRY
 cpx QUEUE_COUNT
 bcc hell_next_chunk
 jmp hell_queue_done
hell_next_chunk:
 lda QUEUE_BYTES_LO,x
 ora QUEUE_BYTES_HI,x
 beq hell_entry_done
 ; CHUNK = min(128, colours left in the entry), then by the kind of colour.
 lda QUEUE_BYTES_HI,x
 bne hell_long
 lda QUEUE_BYTES_LO,x
 lsr a
 bra hell_short
hell_long:
 lda #128
hell_short:
 sta <CHUNK
 lda QUEUE_INDEX_HI,x
 bne hell_high_half
 lda #HELL_MAPPED
 sec
 sbc QUEUE_INDEX_LO,x       ; colours left below HELL_MAPPED
 beq hell_raw
 bcc hell_raw
 ; Mapped: no further than HELL_MAPPED, BUDGET colours at most.
 cmp <CHUNK
 bcs hell_below
 sta <CHUNK
hell_below:
 lda <BUDGET
 cmp <CHUNK
 bcs hell_mapped_fits
 sta <CHUNK
hell_mapped_fits:
 jsr hell_chunk
 lda <CHUNK
 bra hell_advance
hell_high_half:
 ; No further than colour 511 (a left-over entry may run on from 0).
 lda QUEUE_INDEX_LO,x
 beq hell_raw
 eor #$ff
 inc a
 cmp <CHUNK
 bcs hell_raw
 sta <CHUNK
hell_raw:
 ; Unmapped: as many as the budget pays for. With BUDGET = RAW_SETUP + k
 ; (k < RAW_ANY - RAW_SETUP), 3.5 k colours cost at most RAW_SETUP + k.
 lda <BUDGET
 cmp #RAW_ANY
 bcs hell_raw_fits
 sec
 sbc #RAW_SETUP
 bcc hell_spent
 beq hell_spent
 sta <TMP
 asl a
 clc
 adc <TMP
 lsr <TMP
 clc
 adc <TMP                   ; 3.5 k
 cmp <CHUNK
 bcs hell_raw_fits
 sta <CHUNK
hell_raw_fits:
 jsr hell_raw_chunk
 lda <CHUNK
 lsr a
 lsr a
 lsr a
 lsr a
 lsr a
 sta <TMP                   ; n / 32
 lda <CHUNK
 lsr a
 lsr a                      ; n / 4
 sec                        ; + RAW_SETUP (adc #RAW_SETUP-1 with carry)
 adc <TMP
 adc #RAW_SETUP - 1
hell_advance:
 ; A = the chunk's cost. The entry moves on by CHUNK colours.
 sta <TMP
 ldx <ENTRY
 lda QUEUE_INDEX_LO,x
 clc
 adc <CHUNK
 sta QUEUE_INDEX_LO,x
 bcc hell_index_done
 lda QUEUE_INDEX_HI,x
 inc a
 and #1
 sta QUEUE_INDEX_HI,x
hell_index_done:
 lda <CHUNK
 asl a
 sta <PTR
 cla
 rol a
 sta <PTR+1
 lda QUEUE_BYTES_LO,x
 sec
 sbc <PTR
 sta QUEUE_BYTES_LO,x
 lda QUEUE_BYTES_HI,x
 sbc <PTR+1
 sta QUEUE_BYTES_HI,x
 lda <BUDGET
 sec
 sbc <TMP
 sta <BUDGET
 beq hell_spent
 jmp hell_next_chunk
hell_spent:
 ldx <ENTRY
 jsr fold_queue
 bra hell_border
hell_queue_done:
 stz QUEUE_COUNT
hell_border:
 lda <FULL
 beq hell_full_done
 jsr QUEUE_ALL
hell_full_done:
 lda QUEUE_COUNT
 beq hell_nothing_left
 lda PALETTE_STATE
 ora #LEFTOVER
 sta PALETTE_STATE
hell_nothing_left:
 ; The border colour (entry $100, sprite palette 0's transparent colour):
 ; unmapped, like the rest of the sprite palettes.
 stz $0402
 lda #1
 sta $0403
 lda BORDER
 sta $0404
 lda BORDER+1
 sta $0405
hell_return:
 ; mapped_return, then MPR3 as it was (hell_done).
 pla
 sta <TMP
 pla
 sta <FULL
 pla
 sta <ENTRY
 pla
 sta <CHUNK
 pla
 sta <BUDGET
 pla
 sta <PTR+1
 pla
 sta <PTR
 ply
 plx
 jmp hell_done

 ; CHUNK colours (1-128, all below HELL_MAPPED) of queue entry X, mapped:
 ; upload_chunk with the HELL table.
hell_chunk:
 lda QUEUE_INDEX_LO,x
 sta $0402
 stz $0403
 clc
 adc <CHUNK
 stz <PTR+1
 asl a
 rol <PTR+1
 clc
 adc #$86
 sta <PTR
 lda <PTR+1
 adc #$21                   ; $2286 + 2 x (first + CHUNK) - 256
 sta <PTR+1
 lda <CHUNK
 asl a
 eor #$ff
 inc a
 tay
 lda VISIBLE_STAGE          ; the stage with an override (1-1) has its
 cmp #HELL_OVERRIDE_STAGE   ; own loop: 9 cycles a chunk elsewhere
 beq hell_colour_ovr
hell_colour:
 lda [PTR],y
 tax
 iny
 lda [PTR],y
 lsr a
 bcs hell_colour_high
 lda hell_lo0,x
 sta $0404
 lda hell_hi0,x
 sta $0405
 iny
 bne hell_colour
 rts
hell_colour_high:
 lda hell_lo1,x
 sta $0404
 lda hell_hi1,x
 sta $0405
 iny
 bne hell_colour
 rts

 ; The per-stage override (1.11-dev, hell.json "stage_overrides"; the
 ; generated HELL_OVERRIDE_* equates): in the visible stage
 ; HELL_OVERRIDE_STAGE ($2E5F, Level Select numbering) the colour
 ; HELL_OVERRIDE_KEY (low half, $001-$0FF) shows HELL_OVERRIDE_LO/HI instead
 ; of its table colour; the table stays as it is for every other stage (1-1's
 ; sidewalk fleck and skyline shadow $094 is 2-2's far ridge too). These are
 ; hell_colour's and now_hell_map's loops with one compare more on the low
 ; half (cpx #/beq: 4 cycles a colour, in that stage only; a hit costs 4
 ; fewer than the lookup). No RAM: the stage is read where the loop is
 ; chosen. A further colour for the stage is one more cpx/beq and hit in
 ; each loop (4 cycles a low-half colour each).
hell_colour_ovr:
 lda [PTR],y
 tax
 iny
 lda [PTR],y
 lsr a
 bcs hell_ovr_high
 cpx #HELL_OVERRIDE_KEY
 beq hell_ovr_hit
 lda hell_lo0,x
 sta $0404
 lda hell_hi0,x
 sta $0405
 iny
 bne hell_colour_ovr
 rts
hell_ovr_hit:
 lda #HELL_OVERRIDE_LO
 sta $0404
 lda #HELL_OVERRIDE_HI
 sta $0405
 iny
 bne hell_colour_ovr
 rts
hell_ovr_high:
 lda hell_lo1,x
 sta $0404
 lda hell_hi1,x
 sta $0405
 iny
 bne hell_colour_ovr
 rts

 ; CHUNK colours (1-128) of queue entry X unchanged, by a TIA built on the
 ; stack (the vblank interrupt's; anything nested goes below it):
 ; tia $2286 + 2 x first, $0404, 2 x CHUNK / rts. X and Y are not kept.
hell_raw_chunk:
 lda QUEUE_INDEX_LO,x
 sta $0402
 lda QUEUE_INDEX_HI,x
 sta $0403
 lda #$60                   ; rts
 pha
 lda <CHUNK
 asl a
 tay
 cla
 rol a
 pha                        ; length, high byte
 phy                        ; low byte
 lda #$04
 pha                        ; destination $0404 (the TIA alternates
 pha                        ; $0404 and $0405)
 lda QUEUE_INDEX_LO,x
 asl a
 tay
 lda QUEUE_INDEX_HI,x
 rol a
 tax
 tya
 clc
 adc #$86
 tay
 txa
 adc #$22
 pha                        ; source $2286 + 2 x first, high byte
 phy                        ; low byte
 lda #$e3                   ; tia
 pha
 tsx
 inx
 stx <PTR
 lda #$21
 sta <PTR+1
 jsr hell_run_tia
 tsx
 txa
 clc
 adc #8
 tax
 txs
 rts
hell_run_tia:
 jmp [$2000 + PTR]

 ; palette_now in HELL (from now_hell_far, MPR3's byte on the stack; Y = 0,
 ; CHUNK = 2 x count, PTR = the first colour's RAM word, VCE address set,
 ; X = the first colour): colours below HELL_MAPPED mapped here, the rest
 ; (HUD and sprite palettes) as they are by now_raw, after now_hell_exit.
now_hell:
 lda MASTER_STATE
 bne now_hell_cinema
 lda <CHUNK
 pha
 txa
 eor #$ff                   ; carry is set (HELL's cmp in palette_now)
 adc #HELL_MAPPED           ; colours below HELL_MAPPED from X on
 bcc now_hell_mapped
 beq now_hell_mapped
 cmp #128
 bcs now_hell_stage
 asl a
 cmp <CHUNK
 bcs now_hell_stage
 sta <CHUNK                 ; their bytes, the end of the mapped part
now_hell_stage:
 lda VISIBLE_STAGE          ; as hell_chunk: the override stage's own loop
 cmp #HELL_OVERRIDE_STAGE
 beq now_hell_ovr
now_hell_map:
 lda [PTR],y
 tax
 iny
 lda [PTR],y
 iny
 lsr a
 bcs now_hell_high
 lda hell_lo0,x
 sta $0404
 lda hell_hi0,x
 sta $0405
 cpy <CHUNK
 bne now_hell_map
 bra now_hell_mapped
now_hell_high:
 lda hell_lo1,x
 sta $0404
 lda hell_hi1,x
 sta $0405
 cpy <CHUNK
 bne now_hell_map
now_hell_mapped:
 pla
 sta <CHUNK
 jmp now_hell_exit
now_hell_cinema:
 jmp now_hell_cinema_exit

 ; palette_now in the override stage: now_hell_map with the compare
 ; (hell_colour_ovr above).
now_hell_ovr:
 lda [PTR],y
 tax
 iny
 lda [PTR],y
 iny
 lsr a
 bcs now_ovr_high
 cpx #HELL_OVERRIDE_KEY
 beq now_ovr_hit
 lda hell_lo0,x
 sta $0404
 lda hell_hi0,x
 sta $0405
 cpy <CHUNK
 bne now_hell_ovr
 bra now_hell_mapped
now_ovr_hit:
 lda #HELL_OVERRIDE_LO
 sta $0404
 lda #HELL_OVERRIDE_HI
 sta $0405
 cpy <CHUNK
 bne now_hell_ovr
 bra now_hell_mapped
now_ovr_high:
 lda hell_lo1,x
 sta $0404
 lda hell_hi1,x
 sta $0405
 cpy <CHUNK
 bne now_hell_ovr
 bra now_hell_mapped
hell_code_end:
 .if (hell_code_end > HELL_TABLE)
 .fail
 .endif

 ; The HELL table (generated from hell.json by scripts/palette_tables.py),
 ; in the GB DMG table's format.
 .org HELL_TABLE
 .include "hell-table.inc"
hell_table_end:
 .if (hell_table_end > $8000)
 .fail
 .endif
 .if (HELL_MAPPED > 256)
 .fail
 .endif

 ; SMS, in bank SMS_BANK ($3B): a copy of bank $46 $5000-$53FF and
 ; PALETTE_FAR at the same addresses (sms-mirror.inc, from the ;@mirror
 ; lines above), and at $5400-$57FF the SMS table in the GB DMG table's
 ; format (sms-table.inc, from sms.json). File offsets $77000-$777FF and
 ; $77A00-$77AFF: the original game's $FF tail of bank $3B (its data ends
 ; at $761CE), never read or executed (docs/validation/sms-palette.md).
 ; vblank_sms and now_sms map this bank into MPR2 in place of bank $46 and
 ; carry on with GB DMG's code here, which reads the SMS table where GB DMG
 ; reads its own; the trampoline restores MPR2 on return.
 .bank SMS_BANK
 .include "sms-mirror.inc"
 .org $5400
 .include "sms-table.inc"
sms_tables_end:
 .if (sms_tables_end > $5800)
 .fail
 .endif
 .if (sms_lo0 <> gb_lo0) | (sms_hi0 <> gb_hi0) | (sms_lo1 <> gb_lo1) | (sms_hi1 <> gb_hi1)
 .fail
 .endif
