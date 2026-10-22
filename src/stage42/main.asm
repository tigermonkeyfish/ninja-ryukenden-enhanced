 .include "loop.inc"
 .bank $67
 .org $4000
smooth:
 ; Original background workspace is available while its renderer is replaced.
 lda $2e4b
 cmp $2257
 bne changed
 lda $2e4c
 cmp $2258
 bne changed
 rts
changed:
 ; Shared Enhanced coordinate, anchored at stage entry.
 jsr $ffd0
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop
 nop

 pha
 and #7
 sta <$27
 pla
 lsr a
 lsr a
 lsr a
 sta <$26
 lda $2e4b
 lsr a
 lsr a
 lsr a
 sta <$25
 lda $2e4c
 and #1
 beq low_half
 lda <$25
 ora #32
 sta <$25
low_half:
 ; The original geometry at $2251-$2256 must survive death/respawn.
 ; Only $2257-$225A (old renderer's bank saves and cursor) may be reused.
 stz <$2d
 lda $2258
 cmp #$ff
 beq phase_changed
 lda $2259
 and #7
 cmp <$27
 beq same_phase
phase_changed:
 inc <$2d
same_phase:
 lda #33
 sta <$30
 lda <$25
 sta <$2f
 lda $2258
 cmp #$ff
 beq initialize
 lda $2259
 lsr a
 lsr a
 lsr a
 cmp <$26
 bne cache
 ; The existing tile-map entries are still correct except at a new edge.
 stz <$30
 lda <$25
 sec
 sbc $225a
 and #63
 beq cache
 cmp #1
 beq new_right
 cmp #63
 beq new_left
 lda #33
 sta <$30
 bra cache
new_right:
 lda <$25
 clc
 adc #32
 and #63
 sta <$2f
new_left:
 inc <$30
 bra cache
initialize:
 lda #123
 tam #3
 jsr $658f
cache:
 lda $2e4b
 sta $2257
 lda $2e4c
 sta $2258
 lda <$26
 asl a
 asl a
 asl a
 ora <$27
 sta $2259
 lda <$25
 sta $225a
 ; Loop entry for BAT column <$2f (native_backdrops.py, loop.inc):
 ; floor((D + LOOP_SPAN - C%8)/8) + (<$2f - left column), mod LOOP_LENGTH.
 ; D = floor(C/8) + anchor is still in <$29/<$2a from the jsr $ffd0 above.
 lda <$29
 clc
 adc #LOW(LOOP_SPAN)
 sta <$29
 lda <$2a
 adc #HIGH(LOOP_SPAN)
 sta <$2a
 lda $2e4b
 and #7
 sta <$2c
 lda <$29
 sec
 sbc <$2c
 sta <$29
 lda <$2a
 sbc #0
 sta <$2a
 lsr <$2a
 ror <$29
 lsr <$2a
 ror <$29
 lsr <$2a
 ror <$29
loop_mod:
 lda <$2a
 bne loop_sub
 lda <$29
 cmp #LOOP_LENGTH
 bcc loop_offset
loop_sub:
 lda <$29
 sec
 sbc #LOOP_LENGTH
 sta <$29
 lda <$2a
 sbc #0
 sta <$2a
 bra loop_mod
loop_offset:
 lda <$2f
 sec
 sbc $225a
 and #63
 clc
 adc <$29
loop_edge_mod:
 cmp #LOOP_LENGTH
 bcc loop_ready
 sbc #LOOP_LENGTH
 bra loop_edge_mod
loop_ready:
 sta <$2e
 stz <$06
 lda #$44
 sta <$07
 sta <$0b
 lda #$40
 sta <$0a
 stz <$08
 stz <$09
 lda #22
 sta <$28
row_loop:
 lda <$2d
 beq no_copy
 lda #22
 sec
 sbc <$28
 asl a
 tay
 lda row_table,y
 sta <$29
 lda row_table+1,y
 sta <$2a
 ldy <$27
 lda [<$29],y
 tam #3
 tya
 clc
 adc #8
 tay
 lda [<$29],y
 pha
 tya
 clc
 adc #8
 tay
 lda [<$29],y
 sta <$2a
 pla
 sta <$29
 jsr copy_dispatch
no_copy:
 lda <$30
 beq next_row
 sta <$2a
 lda <$2f
 sta <$29
 eor #$3f
 inc a
 sta <$25
 ldy <$2e
 jsr set_ports
 lda <$30
 sta <$2c
chunk_start:
 lda <$2c
 cmp <$25
 bcc shorter_chunk
 lda <$25
shorter_chunk:
 sta <$2a
 ; Map rows hold 64 entries (loop position mod LOOP_LENGTH): split the run
 ; at entry 64, which continues at 64 mod LOOP_LENGTH.
 sty <$2b
 lda #64
 sec
 sbc <$2b
 cmp <$2a
 bcs map_room
 sta <$2a
map_room:
 lda <$2c
 sec
 sbc <$2a
 sta <$2c
 lda <$25
 sec
 sbc <$2a
 sta <$25
 ldx <$2a
 lda column_entry_lo,x
 sta <$29
 lda column_entry_hi,x
 sta <$2a
 jsr copy_dispatch
 cpy #64
 bne map_continues
 ldy #MAP_WRAP
map_continues:
 lda <$2c
 beq next_row
 lda <$25
 bne chunk_start
 stz <$29
 jsr set_ports
 lda #64
 sta <$25
 bra chunk_start
next_row:
 lda <$06
 clc
 adc #128
 sta <$06
 ora #$40
 sta <$0a
 bcc map_no_carry
 inc <$07
 inc <$0b
map_no_carry:
 lda <$08
 clc
 adc #64
 sta <$08
 bcc bat_no_carry
 inc <$09
bat_no_carry:
 dec <$28
 beq done
 jmp row_loop
done:
 rts
set_ports:
 lda #1
 sta <$11
 st0 #1
 lda <$08
 clc
 adc <$29
 sta $0002
 lda <$09
 adc #0
 sta $0003
 stz <$11
 st0 #0
 lda <$08
 clc
 adc <$29
 sta $0002
 lda <$09
 adc #0
 sta $0003
 lda #2
 sta <$11
 st0 #2
 rts
copy_dispatch:
 jmp [$2029]
 .include "p5-generated.inc"
