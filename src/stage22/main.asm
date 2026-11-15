 .include "loop.inc"
 .bank $56
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
 cmp #$fc                   ; $FF, or a stage load's pending draw ($FD, $FC)
 bcs phase_changed
 lda $2259
 and #7
 cmp <$27
 beq same_phase
phase_changed:
 inc <$2d
same_phase:
 ; <$2b: how rows of equal entries (uniform_rows) are drawn: $80 like the
 ; others, $ff not at all, 0-63 only that BAT column.
 lda #$80
 sta <$2b
 lda #33
 sta <$30
 lda <$25
 sta <$2f
 lda $2258
 cmp #$fc
 bcs init_select
 lda <$25
 sec
 sbc $225a
 and #63
 tax
 lda $2259
 lsr a
 lsr a
 lsr a
 cmp <$26
 beq offset_same
 ; The backdrop moved a whole tile: every row is redrawn, but rows of equal
 ; entries are unchanged and only need the camera's new edge column.
 txa
 beq uniform_skip
 cmp #1
 beq uniform_right
 cmp #63
 bne cache
 lda <$25
 bra uniform_edge
uniform_right:
 lda <$25
 clc
 adc #32
 and #63
uniform_edge:
 sta <$2b
 bra cache
uniform_skip:
 lda #$ff
 sta <$2b
 bra cache
offset_same:
 ; The existing tile-map entries are still correct except at a new edge.
 stz <$30
 txa
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
init_select:
 ; (out of line: initialize_far, with the palette copy)
 jmp initialize_far
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
 ; floor((D + LOOP_SPAN - C%8)/8) + (<$2f - left column) + round offset,
 ; mod LOOP_LENGTH. Every row shares the loop.
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
mountain_mod:
 lda <$2a
 bne mountain_sub
 lda <$29
 cmp #LOOP_LENGTH
 bcc mountain_offset
mountain_sub:
 lda <$29
 sec
 sbc #LOOP_LENGTH
 sta <$29
 lda <$2a
 sbc #0
 sta <$2a
 bra mountain_mod
mountain_offset:
 lda $2e60
 and #3
 tax
 lda <$2f
 sec
 sbc $225a
 and #63
 clc
 adc <$29
 ; Per-round offset so each round opens on the original's columns.
 clc
 adc opening_fix,x
mountain_edge_mod:
 cmp #LOOP_LENGTH
 bcc mountain_ready
 sbc #LOOP_LENGTH
 bra mountain_edge_mod
mountain_ready:
 sta <$2e
 stz <$06
 lda #$44
 sta <$07
 sta <$0b
 lda #$40
 sta <$0a
 stz <$08
 stz <$09
 lda <$30
 beq planned
 jsr plan_columns
planned:
 lda #16
 sta <$28
row_loop:
 lda <$2d
 beq no_copy
 lda #16
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
 ldx <$28
 lda uniform_rows-1,x
 beq draw_full
 bit <$2b
 bpl draw_edge
 bvs next_row
draw_full:
 jsr draw_row
 bra next_row
draw_edge:
 ; One entry at column <$2b; any map index gives the row's only entry.
 cly
 lda <$2b
 jsr set_ports
 ldx #2
 jsr dispatch
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
copy_dispatch:
 jmp [$2029]
; Per-round loop offsets (loop.inc, from the rounds' entry cameras).
opening_fix:
 .db OPENING_0,OPENING_1,OPENING_2,OPENING_3
main_end:
 .if (main_end > $4300)
 .fail
 .endif
 .org $4c00
plan_columns:
 ; Every row copies <$30 entries from BAT column <$2f and map index <$2e.
 ; The run can cross the end of the BAT row (continue at column 0) and of
 ; the map row (continue at MAP_WRAP), in either order: <$25, <$26 = twice
 ; the length of chunks 1 and 2 (chunk 3 is the rest), <$2c = what ends after
 ; chunks 1 and 2 (bits 0-1, 2-3; bit 0 BAT row, bit 1 map row). Row uploads
 ; keep these.
 stz <$26
 stz <$2c
 lda #64
 sec
 sbc <$2f
 tax
 lda #64
 sec
 sbc <$2e
 tay
 stx <$25
 cpy <$25
 beq plan_same
 bcc plan_map_first
 lda #1
 sty <$29
 bra plan_first
plan_map_first:
 stx <$29
 tya
 tax
 lda #2
 bra plan_first
plan_same:
 lda #3
 ldy #255
 sty <$29
plan_first:
 cpx <$30
 bcs plan_one
 sta <$2c
 stx <$25
 lda <$29
 cmp <$30
 bcs plan_two
 lda <$2c
 eor #3
 asl a
 asl a
 tsb <$2c
 lda <$29
 sec
 sbc <$25
 asl a
 sta <$26
 bra plan_c1
plan_two:
 lda <$30
 sec
 sbc <$25
 asl a
 sta <$26
plan_c1:
 asl <$25
 rts
plan_one:
 lda <$30
 asl a
 sta <$25
 rts
draw_row:
 ldy <$2e
 lda <$2f
 jsr set_ports
 ldx <$25
 jsr dispatch
 ldx <$26
 beq draw_done
 lda <$2c
 jsr row_end
 ldx <$26
 jsr dispatch
 lda <$30
 asl a
 sec
 sbc <$25
 sec
 sbc <$26
 beq draw_done
 pha
 lda <$2c
 lsr a
 lsr a
 jsr row_end
 plx
dispatch:
 lda <$28
 cmp #5
 bcc dispatch_bottom
 jmp [column_entry,x]
dispatch_bottom:
 jmp [bottom_entry,x]
draw_done:
 rts
row_end:
 ; A bit 1: map row ended (Y = MAP_WRAP); bit 0: BAT row ended (seek
 ; column 0, which also sets the write-address bias for the new Y).
 bit #2
 beq row_end_bat
 ldy #MAP_WRAP
 bit #1
 bne row_end_bat
 ; Same BAT address, new Y: move the bias and the write pointer (the chunk
 ; may have ended on foreground, which leaves the write pointer behind).
 lda <$29
 clc
 adc #64 - MAP_WRAP
 sta <$29
 bcc row_end_seek
 inc <$2a
row_end_seek:
 jmp seek_write
row_end_bat:
 cla
set_ports:
 ; Read and write pointers at BAT column A of this row; <$29/<$2a = that
 ; address minus Y (map index) for the column copy's write-pointer seeks.
 clc
 adc <$08
 tax
 lda <$09
 adc #0
 sta <$2a
 lda #1
 sta <$11
 st0 #1
 stx $0002
 lda <$2a
 sta $0003
 stz <$11
 st0 #0
 stx $0002
 sta $0003
 lda #2
 sta <$11
 st0 #2
 stx <$29
 tya
 eor #$ff
 sec
 adc <$29
 sta <$29
 lda <$2a
 adc #$ff
 sta <$2a
 rts
initialize_far:
 ; $2258: $FF draws at once: an area change's draw ($2257 holds the bank the
 ; native $80AB saved there) or the gameplay fallback. A stage load
 ; (init_background: $2257 = $FF) only writes the palettes here and leaves
 ; the drawing to the entry's black frames (load_piece; load-exact).
 lda $2258
 cmp #$ff
 bne load_piece
 lda $2257
 cmp #$ff
 beq load_palette
draw_all:
 ; The native area transition keeps every VCE colour black until its last
 ; dark frame, which is this one: it queues all 512 colours ($F394) here
 ; and the vblank uploads them from the RAM palette for the original's first
 ; visible frame. Original and NES ($2100 bit 4 clear): the merged palettes
 ; go into the RAM palette only and come with that upload; writing them to
 ; the VCE at once lit the backdrop's palette 13/14 rows in the black frame
 ; (2-2 area 2: two lines; start-pos). The mapped modes (bit 4 set: GB DMG,
 ; HELL, SMS) still write them at once (palette_now): their worker does not
 ; convert all 512 colours before this vblank, which left those rows black
 ; on the first visible frame without it.
 jsr initialize
 jsr palette_ram
 lda $2100
 and #$10
 beq drawn
 jsr cache
 ldx #208
 ldy #32
 jmp $febe
drawn:
 jmp cache
load_palette:
 ; The stage load: the merged palettes into the RAM palette only. The load's
 ; fade ($F436) copies the RAM palette to its backup and fades in from it,
 ; so the VCE gets them with the first fade step that shows anything (the
 ; original shows black until then; a VCE write here showed them early).
 jsr palette_ram
 lda #$fd
 sta $2258
 rts
load_piece:
 ; A stage load's draw in two pieces, in the entry's short updates while
 ; every colour is black: $2E63 counts the entry's updates down from $3A
 ; ($82D0); $FD at $38 uploads the tiles (fixed and phase), $FC at $37
 ; writes the tile map and the real cache. Outside the entry ($2E63 = 0;
 ; not expected) everything is drawn at once.
 ldx $2e63
 beq draw_rest
 cmp #$fd
 bne piece_two
 cpx #$38
 bne piece_wait
 jsr initialize
 stz <$30
 jsr cache
 lda #$fc
 sta $2258
piece_wait:
 rts
piece_two:
 cpx #$37
 bne piece_wait
 stz <$2d
 jmp cache
draw_rest:
 jsr initialize
 jmp cache
; The fixed tile upload (scripts/rev5_texture.py writes this bank and
; address: it matches the label and the three lines below).
initialize:
 lda #101
 tam #3
 jsr $6000
 rts
palette_ram:
 ; The merged palettes 13 and 14 into the RAM palette; the native uploads
 ; (the load's fade, the area transition's full re-queue) take them to the
 ; VCE in the active palette mode's colours (a mapped mode's area change
 ; also writes them at once, draw_all). The NES
 ; palette modes ($2100 bits 3-4 = 01, src/nes-palette) have their own
 ; versions, NES-A's and NES-B's (nes-enhanced.inc).
 clx
 lda $2100
 and #$18
 cmp #$08
 beq nes_palette
palette_loop:
 lda palette13,x
 sta $2426,x
 lda palette14,x
 sta $2446,x
 inx
 cpx #32
 bne palette_loop
 bra palette_written
nes_palette:
 ; NES-B ($2100 bit 5 set) has its own versions (the re-lit data), copied
 ; out of line (nes_b_palette_loop) to keep this block short.
 lda $2100
 and #$20
 bne nes_palette_b          ; (NES-A: 2, then the jmp: 6; see nes_palette_a)
 jmp nes_palette_a
nes_palette_b:
 jmp nes_b_palette_peeled   ; (NES-B: 4 + 4; see nes_b_palette_peeled)
nes_palette_loop:
 lda palette13_nes,x
 sta $2426,x
 lda palette14_nes,x
 sta $2446,x
 inx
 cpx #32
 bne nes_palette_loop
palette_written:
 rts
nes_palette_a:
 ; Palette timing (palette-lag): NES-A reaches here 9 cycles after
 ; Original's copy would, NES-B (below) 15: the first three colour bytes
 ; unrolled, 8 cycles faster each than a loop pass, pay for that, the
 ; ldx, the jmp back and a pad, so every mode reaches palette_written at
 ; the same cycle.
 lda palette13_nes
 sta $2426
 lda palette14_nes
 sta $2446
 lda palette13_nes+1
 sta $2426+1
 lda palette14_nes+1
 sta $2446+1
 lda palette13_nes+2
 sta $2426+2
 lda palette14_nes+2
 sta $2446+2
 php
 plp
 ldx #3
 jmp nes_palette_loop
 ; NES-B's copy loop (from initialize), back to palette_written.
nes_b_palette_peeled:
 lda palette13_nes_b
 sta $2426
 lda palette14_nes_b
 sta $2446
 lda palette13_nes_b+1
 sta $2426+1
 lda palette14_nes_b+1
 sta $2446+1
 lda palette13_nes_b+2
 sta $2426+2
 lda palette14_nes_b+2
 sta $2446+2
 nop
 sxy
 ldx #3
nes_b_palette_loop:
 lda palette13_nes_b,x
 sta $2426,x
 lda palette14_nes_b,x
 sta $2446,x
 inx
 cpx #32
 bne nes_b_palette_loop
 jmp palette_written
 ; The NES palette mode's palettes 13 and 14 (scripts/nes_palette.py).
 .include "nes-enhanced.inc"
helpers_end:
 .if (helpers_end > $5000)
 .fail
 .endif
 .include "p3-generated.inc"
