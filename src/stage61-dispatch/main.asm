; Bank-switch bridge: called by the isolated 6-1 mountain pass.
 .bank 0
 .org $ff09
sky_wrapper:
 lda #$44
 tam #2
 jsr $4000
 lda #$66
 tam #2
 rts
 .org $ff20
fast_sky_wrapper:
 lda #$45
 tam #2
 jsr $4400
 lda #$44
 tam #2
 rts
 .bank $46
 .org $5800
sky_dispatch:
 cpx #8
 bne original_bank
 lda $2e5f
 cmp #16
 bne original_bank
 lda #$66
 rts
original_bank:
 lda $4055,x
 rts
