; Palette modes: $2100 bits 3-4. 00 Original (the shipped colours; zero is
; the default), 01 NES (reserved, shown as Original for now), 10 GB DMG,
; 11 HELL. The menu's PALETTE row offers them (src/options/menu.txt).
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
; colours, written by a TIA at the native rate. Cinemas, the title and the
; ending ($2240 = 1 or 2) keep the native upload in every mode.
;
; $2100 bit 7 is this module's state, not an option: set while the VCE holds
; mapped colours (GB DMG or HELL). Whenever the colours due (mapped in GB
; DMG or HELL gameplay, original otherwise) differ from that state, the
; vblank upload queues all 512 colours ($F394) and flips the bit, so a
; change between Original (or NES) and a mapped mode, or a cinema starting or
; ending, re-uploads everything by itself. The bit does not say which table
; the VCE holds: whoever changes bits 3-4 while a mapped mode is live must
; also queue all 512 colours ($F394; the menu's preview and cancel do).
; Menus and saved settings must mask bits 5-7 out; clearing bit 7 costs at
; most one needless full re-upload.
;
; The Original and GB DMG paths take exactly the cycles they took before HELL
; existed (the HELL tests ride on branches those paths already took), so
; their timing, and that of every interrupt after them, is unchanged.
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

OPTIONS = $2100
PALETTE_BITS = $18
PALETTE_GB = $10
PALETTE_HELL = $18
MASTER_STATE = $2240        ; 0 gameplay, 1 cinema or title, 2 ending
QUEUE_COUNT = $2260
QUEUE_BYTES_LO = $2261      ; bytes to upload (2 per colour)
QUEUE_BYTES_HI = $2269
QUEUE_INDEX_LO = $2271      ; first colour (0-511)
QUEUE_INDEX_HI = $2279
BORDER = $2281              ; written to colour $100 after each upload
PALETTE_LOCK = $2283
NATIVE_UPLOAD = $f3b5
QUEUE_ALL = $f394           ; native: queue colours 0-511, under the lock
MAPPED_STATE = $80          ; $2100 bit 7: the VCE holds mapped colours
LEFTOVER = $20              ; $2100 bit 5: the queue's one entry was left over
WAS_BUSY = $40              ; $2100 bit 6: the main loop was busy at the last vblank with work
PALETTE_BANK = $46
HELL_BANK = $43            ; HELL's code and table, mapped in MPR3 ($6000)
HELL_CODE = $7800           ; while they run: bank $43 $7800-$7BFF ...
HELL_TABLE = $7c00          ; ... and $7C00-$7FFF

PALETTE_CAP = 168           ; colours per vblank (measured: docs/validation/gb-palette.md)
ENTRY_COST = 6              ; colours' worth of time per further queue entry
LEFTOVER_CAP = 16           ; colours a vblank for a left-over entry alone
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

 .bank 0
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
 .org $5000
palette_entry:
 ; Cycle counts below (HuC6280, no page-crossing penalties) are those of
 ; the paths before HELL: palette_now reaches its body in 4 (was a bcc not
 ; taken and a jmp: 6), the vblank in 2 + 2 (was a bcc taken: 4).
 bcs palette_now_mapped
 nop
palette_vblank:
 ; As the native upload: nothing happens while the palette is locked.
 lda PALETTE_LOCK
 bne upload_return
 lda OPTIONS
 and #PALETTE_BITS
 cmp #PALETTE_GB
 bne vblank_other           ; Original, NES, HELL (carry set: HELL)
 lda MASTER_STATE
 bne vblank_cinema
 ; GB DMG in gameplay. If the VCE still holds original colours (bit 7
 ; clear: the mode was just chosen, or a cinema or the title just ended),
 ; queue all 512 colours ($F394) first.
 lda OPTIONS
 bmi mapped_state
 ora #MAPPED_STATE
 sta OPTIONS
 bra queue_everything
mapped_state:
 lda QUEUE_COUNT
 bne queue_present
 ; Nothing queued, so nothing is left over either.
 lda OPTIONS
 and #$ff - LEFTOVER
 sta OPTIONS
 rts
queue_present:
 jmp mapped_upload          ; 4 cycles, as the bra it replaces
queue_everything:
 jsr QUEUE_ALL
 lda OPTIONS
 and #$ff - LEFTOVER
 sta OPTIONS
 jmp mapped_upload
vblank_other:
 ; Original or NES (carry clear) in 2 + 5 + 2 + 4 cycles, as the 5 + 4 + 4
 ; of the lda/bpl/jmp before HELL; HELL (carry set) has its own path.
 ; (With bit 7 set, the mode just changed to Original, the requeue below
 ; starts 4 cycles later than before HELL.)
 bcs vblank_hell
 lda OPTIONS
 bmi cinema_requeue
 jmp NATIVE_UPLOAD
vblank_hell:
 ; HELL: its code and table are in bank HELL_BANK, mapped in MPR3 until it
 ; leaves by hell_cinema or hell_done, which put MPR3 back (code running in
 ; MPR3 cannot unmap itself).
 tma #3
 pha
 lda #HELL_BANK
 tam #3
 jmp hell_vblank
hell_cinema:
 pla
 tam #3
vblank_cinema:
 ; GB DMG or HELL in a cinema, the title or the ending: original colours.
 ; If the VCE holds mapped ones (bit 7 set: a cinema just began, or the
 ; mode was just changed), queue all 512 colours first.
 lda OPTIONS
 bpl native_upload
cinema_requeue:
 and #$ff - MAPPED_STATE
 sta OPTIONS
 jsr QUEUE_ALL
native_upload:
 jmp NATIVE_UPLOAD
hell_done:
 pla
 tam #3
upload_return:
 rts

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
 and #PALETTE_BITS
 cmp #PALETTE_GB
 bne now_other              ; Original, NES, HELL (carry set: HELL)
 nop                        ; GB DMG: the 2 cycles the entry saved
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
 ; HELL: bank HELL_BANK in MPR3 while now_hell maps the colours below
 ; HELL_MAPPED; it comes back to now_hell_exit with Y = the bytes done.
 tma #3
 pha
 lda #HELL_BANK
 tam #3
 jmp now_hell
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
 lda OPTIONS
 and #WAS_BUSY
 sta <ENTRY
 lda OPTIONS
 and #$ff - WAS_BUSY
 ora <CHUNK
 sta OPTIONS
 ; A single entry that an upload left over ($2100 bit 5) is work the native
 ; game does not have in this frame, and the main loop may need the time
 ; (the frames after a large upload are often an area change's load). It
 ; waits while the main loop is busy, or was at the last vblank with work;
 ; otherwise LEFTOVER_CAP colours go (about 4 lines).
 ldx QUEUE_COUNT
 cpx #1
 bne new_work
 lda OPTIONS
 and #LEFTOVER
 beq new_work
 lda <CHUNK
 ora <ENTRY
 bne main_loop_busy
 lda #LEFTOVER_CAP
 sta <BUDGET
 jmp budget_done
main_loop_busy:
 jmp mapped_return
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
 lda OPTIONS
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
 lda OPTIONS
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
 lda OPTIONS
 and #$ff - LEFTOVER
 sta OPTIONS
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
 lda OPTIONS
 ora #LEFTOVER
 sta OPTIONS
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

palette_code_end:
 .if (palette_code_end > $5400)
 .fail
 .endif

 ; The GB DMG table (generated from gb-dmg.json by scripts/palette_tables.py):
 ; four pages, the mapped colour's low and high byte for colours $000-$0FF
 ; and $100-$1FF, indexed by the colour's low byte.
 .org $5400
 .include "gb-table.inc"
palette_tables_end:
 .if (palette_tables_end > $5800)
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
hell_vblank:
 ; HELL (from vblank_hell: mapped_upload's stack depth plus MPR3's byte).
 lda MASTER_STATE
 beq hell_gameplay
 jmp hell_cinema
hell_gameplay:
 ; If the VCE holds original colours (bit 7 clear: the mode was just
 ; chosen, or a cinema or the title just ended), queue all 512 first.
 lda OPTIONS
 bmi hell_mapped_state
 ora #MAPPED_STATE
 sta OPTIONS
 jsr QUEUE_ALL
 bra hell_fresh
hell_mapped_state:
 lda QUEUE_COUNT
 bne hell_upload
hell_fresh:
 ; Nothing queued, so nothing is left over either (or all 512 colours were
 ; just queued afresh).
 lda OPTIONS
 and #$ff - LEFTOVER
 sta OPTIONS
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
 lda OPTIONS
 and #WAS_BUSY
 sta <ENTRY
 lda OPTIONS
 and #$ff - WAS_BUSY
 ora <CHUNK
 sta OPTIONS
 ldx QUEUE_COUNT
 cpx #1
 bne hell_new_work
 lda OPTIONS
 and #LEFTOVER
 beq hell_new_work
 lda <CHUNK
 ora <ENTRY
 bne hell_busy
 lda #LEFTOVER_CAP
 sta <BUDGET
 jmp hell_budget_done
hell_busy:
 jmp hell_return
hell_new_work:
 stz <PTR
 stz <PTR+1
 ldx #0
 lda OPTIONS
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
 lda OPTIONS
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
 lda OPTIONS
 and #$ff - LEFTOVER
 sta OPTIONS
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
 lda OPTIONS
 ora #LEFTOVER
 sta OPTIONS
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
 bne now_hell_done
 lda <CHUNK
 pha
 txa
 eor #$ff
 sec
 adc #HELL_MAPPED           ; colours below HELL_MAPPED from X on
 bcc now_hell_mapped
 beq now_hell_mapped
 cmp #128
 bcs now_hell_map
 asl a
 cmp <CHUNK
 bcs now_hell_map
 sta <CHUNK                 ; their bytes, the end of the mapped part
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
now_hell_done:
 jmp now_hell_exit
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
