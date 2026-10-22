 ; Native languages: Japanese=0, English=1, Chinese=2.
 .bank 0
 .org $e02c
 jsr english_init
 .org $ffe6
english_init:
 lda #1
 sta $3227
 jmp $fcbe
