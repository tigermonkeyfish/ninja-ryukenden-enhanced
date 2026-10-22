; In-game stage selector. Blocking in-game stage selector; original IRQ/input/audio run.
; HUD backup lives on the CPU stack, so no persistent game RAM is allocated.
 .bank 0
 .org $ff70
selector_hook:
 jsr $ff42
 ; deferred_draw (dispatch): an area change's pending backdrop draw
 lda $2e63
 bne selector_return
 lda $2201
 beq selector_return
 lda $2e57
 and #4
 beq selector_return
 php
 phx
 phy
 tma #2
 pha
 lda #$45
 tam #2
 jsr $4000
 tax
 pla
 tam #2
 txa
 cmp #$ff
 beq selector_cancel
 pha
 clx
clear_progress:
 stz $2e65,x
 inx
 cpx #22
 bne clear_progress
 pla
 jsr $8244
selector_cancel:
 ply
 plx
 plp
selector_return:
 lda $2e63
 rts
 .bank 1
 .org $83f3
 jsr selector_hook
