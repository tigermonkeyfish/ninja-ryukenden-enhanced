 .bank $45
 .org $4400
; One 32-byte TIA per tile with a NOP between blocks: back-to-back 32-byte
; blocks can hold off the playfield split interrupt past its line
; (docs/pc-engine/LESSONS.md).
fast_sky_upload:
 ldx <$27
 lda fast_lo,x
 sta <$29
 lda fast_hi,x
 sta <$2a
 jmp [$2029]
fast_lo:
 .db LOW(fast_0),LOW(fast_1),LOW(fast_2),LOW(fast_3),LOW(fast_4),LOW(fast_5),LOW(fast_6),LOW(fast_7)
fast_hi:
 .db HIGH(fast_0),HIGH(fast_1),HIGH(fast_2),HIGH(fast_3),HIGH(fast_4),HIGH(fast_5),HIGH(fast_6),HIGH(fast_7)
fast_0:
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 nop
 tia $6040,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #128
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6060,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #144
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6040,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6080,$0002,32
 nop
 tia $60a0,$0002,32
 nop
 tia $60c0,$0002,32
 nop
 tia $60e0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6100,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #48
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #64
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6120,$0002,32
 nop
 tia $6140,$0002,32
 nop
 tia $6160,$0002,32
 nop
 tia $6180,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #176
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $61a0,$0002,32
 nop
 tia $61c0,$0002,32
 nop
 tia $61e0,$0002,32
 nop
 tia $6200,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6040,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6220,$0002,32
 nop
 tia $6240,$0002,32
 nop
 tia $6260,$0002,32
 nop
 tia $6280,$0002,32
 rts
fast_1:
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $68e0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #128
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6900,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #144
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $68e0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6920,$0002,32
 nop
 tia $6940,$0002,32
 nop
 tia $6960,$0002,32
 nop
 tia $6980,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $69a0,$0002,32
 nop
 tia $69c0,$0002,32
 nop
 tia $69e0,$0002,32
 nop
 tia $6a00,$0002,32
 nop
 tia $6a20,$0002,32
 nop
 tia $6a40,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6a60,$0002,32
 nop
 tia $6a80,$0002,32
 nop
 tia $6aa0,$0002,32
 nop
 tia $6ac0,$0002,32
 nop
 tia $6ae0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $68e0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6b00,$0002,32
 nop
 tia $6b20,$0002,32
 nop
 tia $6b40,$0002,32
 nop
 tia $6b60,$0002,32
 rts
fast_2:
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7300,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #128
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7320,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #144
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7300,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7340,$0002,32
 nop
 tia $7360,$0002,32
 nop
 tia $7380,$0002,32
 nop
 tia $73a0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $73c0,$0002,32
 nop
 tia $73e0,$0002,32
 nop
 tia $7400,$0002,32
 nop
 tia $7420,$0002,32
 nop
 tia $7440,$0002,32
 nop
 tia $7460,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7480,$0002,32
 nop
 tia $74a0,$0002,32
 nop
 tia $74c0,$0002,32
 nop
 tia $74e0,$0002,32
 nop
 tia $7500,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7300,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $7520,$0002,32
 nop
 tia $7540,$0002,32
 nop
 tia $7560,$0002,32
 nop
 tia $7580,$0002,32
 rts
fast_3:
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7d20,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7d40,$0002,32
 nop
 tia $7d60,$0002,32
 nop
 tia $7d80,$0002,32
 nop
 tia $7da0,$0002,32
 nop
 tia $7dc0,$0002,32
 nop
 tia $7de0,$0002,32
 nop
 tia $7e00,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7e20,$0002,32
 nop
 tia $7e40,$0002,32
 nop
 tia $7e60,$0002,32
 nop
 tia $7e80,$0002,32
 nop
 tia $7ea0,$0002,32
 nop
 tia $7ec0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7ee0,$0002,32
 nop
 tia $7f00,$0002,32
 nop
 tia $7f20,$0002,32
 nop
 tia $7f40,$0002,32
 nop
 tia $7f60,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7d20,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $7f80,$0002,32
 nop
 tia $7fa0,$0002,32
 nop
 tia $7fc0,$0002,32
 nop
 tia $7fe0,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #64
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6000,$0002,32
 rts
fast_4:
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6780,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $67a0,$0002,32
 nop
 tia $67c0,$0002,32
 nop
 tia $67e0,$0002,32
 nop
 tia $6800,$0002,32
 nop
 tia $6820,$0002,32
 nop
 tia $6840,$0002,32
 nop
 tia $6860,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6880,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #48
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $68a0,$0002,32
 nop
 tia $68c0,$0002,32
 nop
 tia $68e0,$0002,32
 nop
 tia $6900,$0002,32
 nop
 tia $6920,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6940,$0002,32
 nop
 tia $6960,$0002,32
 nop
 tia $6980,$0002,32
 nop
 tia $69a0,$0002,32
 nop
 tia $69c0,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6780,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $69e0,$0002,32
 nop
 tia $6a00,$0002,32
 nop
 tia $6a20,$0002,32
 nop
 tia $6a40,$0002,32
 nop
 tia $6a60,$0002,32
 rts
fast_5:
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $71a0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $71c0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #128
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #144
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $71e0,$0002,32
 nop
 tia $7200,$0002,32
 nop
 tia $7220,$0002,32
 nop
 tia $7240,$0002,32
 nop
 tia $7260,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7280,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #48
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $72a0,$0002,32
 nop
 tia $72c0,$0002,32
 nop
 tia $72e0,$0002,32
 nop
 tia $7300,$0002,32
 nop
 tia $7320,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7340,$0002,32
 nop
 tia $7360,$0002,32
 nop
 tia $7380,$0002,32
 nop
 tia $73a0,$0002,32
 nop
 tia $73c0,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $71a0,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $73e0,$0002,32
 nop
 tia $7400,$0002,32
 nop
 tia $7420,$0002,32
 nop
 tia $7440,$0002,32
 nop
 tia $7460,$0002,32
 rts
fast_6:
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7be0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7c00,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #128
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #144
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $7c20,$0002,32
 nop
 tia $7c40,$0002,32
 nop
 tia $7c60,$0002,32
 nop
 tia $7c80,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #208
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7ca0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #48
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7cc0,$0002,32
 nop
 tia $7ce0,$0002,32
 nop
 tia $7d00,$0002,32
 nop
 tia $7d20,$0002,32
 nop
 tia $7d40,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7d60,$0002,32
 nop
 tia $7d80,$0002,32
 nop
 tia $7da0,$0002,32
 nop
 tia $7dc0,$0002,32
 nop
 tia $7de0,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $7be0,$0002,32
 lda #126
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $7e00,$0002,32
 nop
 tia $7e20,$0002,32
 nop
 tia $7e40,$0002,32
 nop
 tia $7e60,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #64
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 rts
fast_7:
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $65e0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #112
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6600,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #128
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #144
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6620,$0002,32
 nop
 tia $6640,$0002,32
 nop
 tia $6660,$0002,32
 nop
 tia $6680,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #208
 st2 #8
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #16
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $66a0,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #32
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #48
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $66c0,$0002,32
 nop
 tia $66e0,$0002,32
 nop
 tia $6700,$0002,32
 nop
 tia $6720,$0002,32
 nop
 tia $6740,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #160
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $6760,$0002,32
 nop
 tia $6780,$0002,32
 nop
 tia $67a0,$0002,32
 nop
 tia $67c0,$0002,32
 nop
 tia $67e0,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #240
 st2 #9
 lda #2
 sta <$11
 st0 #2
 tia $65e0,$0002,32
 lda #127
 tam #3
 stz <$11
 st0 #0
 st1 #0
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6800,$0002,32
 nop
 tia $6820,$0002,32
 nop
 tia $6840,$0002,32
 nop
 tia $6860,$0002,32
 lda #125
 tam #3
 stz <$11
 st0 #0
 st1 #64
 st2 #10
 lda #2
 sta <$11
 st0 #2
 tia $6020,$0002,32
 rts
fast_sky_end:
 .if (fast_sky_end > $6000)
 .fail
 .endif
