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
; holds the original colours and fades map every step. Changing the mode
; only needs a full re-queue ($F394). Cinemas, the title and the ending
; ($2240 = 1 or 2) keep the native upload in every mode.
;
; The mapped upload costs about 3.5 times the native TIA per colour, so it
; uploads at most PALETTE_CAP colours per vblank, less ENTRY_COST for each
; queue entry after the first (it must end before the display starts), and
; leaves the rest queued in the native format: what is left of the entry it
; stopped in and the entries it did not reach become one entry covering them
; (lowest to highest colour), so the producers keep seven free entries.

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
PALETTE_BANK = $46

PALETTE_CAP = 176           ; colours per vblank (measured: docs/validation/gb-palette.md)
ENTRY_COST = 6              ; colours' worth of time per further queue entry

; Zero page borrowed by the mapped upload; saved and restored around it.
PTR = $20                   ; and $21: source pointer
BUDGET = $22                ; colours left this vblank
CHUNK = $23                 ; colours in this chunk (1-128)
ENTRY = $24                 ; queue entry being read

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
 .org $5100
palette_entry:
 bcc palette_vblank
 jmp palette_now_mapped
palette_vblank:
 lda OPTIONS
 and #PALETTE_BITS
 cmp #PALETTE_GB
 bne native_upload
 lda MASTER_STATE
 bne native_upload
 ; As the native upload: nothing queued or locked, nothing written.
 lda QUEUE_COUNT
 beq upload_return
 lda PALETTE_LOCK
 beq mapped_upload
upload_return:
 rts
native_upload:
 jmp NATIVE_UPLOAD

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
 ; BUDGET = PALETTE_CAP less ENTRY_COST for each entry after the first
 ; (an entry's own work, and folding what is left, cost time too).
 ldx QUEUE_COUNT
 cpx #9
 bcc count_ok
 ldx #8
count_ok:
 lda budget_by_count-1,x
 sta <BUDGET
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
budget_by_count:
 .db PALETTE_CAP, PALETTE_CAP - ENTRY_COST, PALETTE_CAP - 2 * ENTRY_COST
 .db PALETTE_CAP - 3 * ENTRY_COST, PALETTE_CAP - 4 * ENTRY_COST
 .db PALETTE_CAP - 5 * ENTRY_COST, PALETTE_CAP - 6 * ENTRY_COST
 .db PALETTE_CAP - 7 * ENTRY_COST

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
