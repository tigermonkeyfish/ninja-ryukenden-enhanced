 .include "loop.inc"
 .bank $40
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
 ; Palette 1 is exclusively scenery. Preserve the original foreground palette 2.
 ; The merged palette goes into the RAM palette ($2286 + 16 colours), so
 ; fades and full re-queues keep it, and to the VCE at once, as the display
 ; shows the new backdrop in this frame (src/palette, palette_now at $FEBE,
 ; in the active palette mode's colours). The NES palette mode ($2100 bits
 ; 3-4 = 01, src/nes-palette) has its own version (nes-enhanced.inc).
 clx
 lda $2100
 and #$18
 cmp #$08
 beq nes_palette_loop
palette_loop:
 lda extra_palette,x
 sta $22a6,x
 inx
 cpx #32
 bne palette_loop
 bra palette_written
nes_palette_loop:
 lda extra_palette_nes,x
 sta $22a6,x
 inx
 cpx #32
 bne nes_palette_loop
palette_written:
 ldx #16
 ldy #16
 jsr $febe
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
 sta <$2c
 ldx <$27
 lda phase_bank,x
 tam #3
 txa
 asl a
 clc
 adc <$27
 asl a
 asl a
 asl a
 sta <$2e
 stz <$06
 lda #$48
 sta <$07
 stz <$08
 stz <$09
 lda #12
 sta <$28
row_loop:
 lda <$2d
 beq no_copy
 lda #12
 sec
 sbc <$28
 asl a
 clc
 adc <$2e
 tay
 lda row_copy,y
 sta <$29
 lda row_copy+1,y
 sta <$2a
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
 ldy <$2c
 jsr set_ports
column_loop:
 lda $0002
 sta <$2b
 lda $0003
 cmp #$20
 bcs foreground
 lda [<$06],y
 sta <$2b
 lda #$12
foreground:
 ; Write both foreground and background sequentially to avoid per-tile seeks.
 ldx <$2b
 stx $0002
 sta $0003
 iny
 ; Map rows hold 64 entries (loop position mod LOOP_LENGTH); entry 64
 ; continues at 64 mod LOOP_LENGTH.
 cpy #64
 bne map_continues
 ldy #MAP_WRAP
map_continues:
 dec <$25
 bne no_wrap
 stz <$29
 jsr set_ports
 lda #64
 sta <$25
no_wrap:
 dec <$2a
 bne column_loop
next_row:
 lda <$06
 clc
 adc #64
 sta <$06
 bcc map_no_carry
 inc <$07
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
 ; The NES palette mode's merged palette 1 (scripts/nes_palette.py).
 .include "nes-enhanced.inc"
renderer_end:
 ; Room for generated.inc's tables (about 240 bytes) before map_data at $4800.
 .if (renderer_end > $4700)
 .fail
 .endif
 .include "generated.inc"
