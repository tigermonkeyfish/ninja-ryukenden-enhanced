; Palette modes: $2100 bits 3-4. 00 Original (the shipped colours; zero is
; the default), 01 NES (reserved, shown as Original for now), 10 GB DMG,
; 11 reserved (Original). No menu row yet (see docs/ARCHITECTURE.md).
;
; The native game keeps its live palette in RAM ($2286, 512 words) and queues
; ranges to upload ($F350; up to 8 entries at $2260-$2280). The vblank
; interrupt uploads the queue with a TIA ($F3B5, called from $FD13), then
; writes the border colour $2281/$2282 to entry $100; a lock ($2283) holds
; it off. In GB DMG mode during gameplay this module uploads the same queue
; with every colour looked up in the mode's table, so the RAM palette always
; holds the original colours and fades map every step. Cinemas, the title
; and the ending ($2240 = 1 or 2) keep the native upload in every mode.
;
; $2100 bit 7 is this module's state, not an option: set while the VCE holds
; mapped colours. Whenever the colours due (mapped in GB DMG gameplay,
; original otherwise) differ from that state, the vblank upload queues all
; 512 colours ($F394) and flips the bit, so a mode change, or a cinema
; starting or ending, re-uploads everything by itself (a menu need only
; change bits 3-4). Menus and saved settings must mask bit 7 out; clearing
; it costs at most one needless full re-upload.
;
; The mapped upload costs about 3.5 times the native TIA per colour, so it
; uploads at most PALETTE_CAP colours per vblank, less ENTRY_COST for each
; queue entry after the first (it must end before the display starts), and
; leaves the rest queued in the native format: what is left of the entry it
; stopped in and the entries it did not reach become one entry covering them
; (lowest to highest colour), so the producers keep seven free entries. A
; queue found full (8 entries) may have lost an entry ($F350 drops when full),
; so it is replaced by all 512 colours.

OPTIONS = $2100
PALETTE_BITS = $18
PALETTE_GB = $10
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

PALETTE_CAP = 168           ; colours per vblank (measured: docs/validation/gb-palette.md)
ENTRY_COST = 6              ; colours' worth of time per further queue entry
LEFTOVER_CAP = 32           ; colours a vblank for a left-over entry alone
NATIVE_PLUS = 36            ; colours (about 4 lines) beyond the native upload's time
BUDGET_MIN = 16

; Zero page borrowed by the mapped upload; saved and restored around it.
PTR = $20                   ; and $21: source pointer
BUDGET = $22                ; colours left this vblank
CHUNK = $23                 ; colours in this chunk (1-128)
ENTRY = $24                 ; queue entry being read
FULL = $25                  ; nonzero: the queue was full (8 entries)

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
 bcc palette_vblank
 jmp palette_now_mapped
palette_vblank:
 ; As the native upload: nothing happens while the palette is locked.
 lda PALETTE_LOCK
 bne upload_return
 lda OPTIONS
 and #PALETTE_BITS
 cmp #PALETTE_GB
 bne vblank_original
 lda MASTER_STATE
 bne vblank_original
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
 bra mapped_upload
queue_everything:
 jsr QUEUE_ALL
 lda OPTIONS
 and #$ff - LEFTOVER
 sta OPTIONS
 bra mapped_upload
vblank_original:
 ; Original colours. If the VCE holds mapped ones (bit 7 set: the mode was
 ; just changed, or a cinema just began), queue all 512 colours first.
 lda OPTIONS
 bpl native_upload
 and #$ff - MAPPED_STATE
 sta OPTIONS
 jsr QUEUE_ALL
native_upload:
 jmp NATIVE_UPLOAD
upload_return:
 rts

 ; Stack in mapped_upload after its 8 pushes: S+9/10 return to the
 ; trampoline, S+11 its saved MPR2, S+12/13 return to $FD16, S+14-16 the
 ; interrupt's Y, X, A, S+17 P, S+18/19 the interrupted PC.
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
 lda $2100 + 19,x           ; the interrupted PC, high byte (see below)
 cmp #$fd
 bne busy_now
 lda $2100 + 18,x
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
 ; New entries go before an entry left over in slot 0, which moves to the
 ; end: it is the one most likely to be cut by the budget, and what is left
 ; over then stays that one range.
 lda OPTIONS
 and #LEFTOVER
 beq budget_done
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
 jsr upload_chunk
 ; The entry moves on by CHUNK colours.
 ldx <ENTRY
 lda QUEUE_INDEX_LO,x
 clc
 adc <CHUNK
 sta QUEUE_INDEX_LO,x
 bcc index_done
 inc QUEUE_INDEX_HI,x
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
 ; it become one entry, from the lowest first colour to the highest last
 ; colour, so the producers keep seven free entries. PTR = lowest first
 ; colour, CHUNK/BUDGET = highest end (0: nothing left).
fold_queue:
 lda #$ff
 sta <PTR
 sta <PTR+1
 stz <CHUNK
 stz <BUDGET
fold_entry:
 lda QUEUE_BYTES_LO,x
 ora QUEUE_BYTES_HI,x
 beq fold_next
 lda QUEUE_INDEX_LO,x
 cmp <PTR
 lda QUEUE_INDEX_HI,x
 sbc <PTR+1
 bcs fold_end
 lda QUEUE_INDEX_LO,x
 sta <PTR
 lda QUEUE_INDEX_HI,x
 sta <PTR+1
fold_end:
 ; end = first colour + bytes / 2
 lda QUEUE_BYTES_HI,x
 lsr a
 tay
 lda QUEUE_BYTES_LO,x
 ror a
 clc
 adc QUEUE_INDEX_LO,x
 pha
 tya
 adc QUEUE_INDEX_HI,x
 tay
 pla
 cmp <CHUNK
 pha
 tya
 sbc <BUDGET
 pla
 bcc fold_next
 sta <CHUNK
 sty <BUDGET
fold_next:
 inx
 cpx QUEUE_COUNT
 bcc fold_entry
 lda <CHUNK
 ora <BUDGET
 bne fold_write
 stz QUEUE_COUNT
 rts
fold_write:
 lda <PTR
 sta QUEUE_INDEX_LO
 lda <PTR+1
 sta QUEUE_INDEX_HI
 lda <CHUNK
 sec
 sbc <PTR
 sta <CHUNK
 lda <BUDGET
 sbc <PTR+1
 asl <CHUNK
 rol a
 sta QUEUE_BYTES_HI
 lda <CHUNK
 sta QUEUE_BYTES_LO
 lda #1
 sta QUEUE_COUNT
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
 bne now_raw
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
