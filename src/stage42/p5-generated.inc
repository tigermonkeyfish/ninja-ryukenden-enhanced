 .org $4300
row_table:
 .dw row0,row1,row2,row3,row4,row5,row6,row7,row8,row9,row10,row11,row12,row13,row14,row15,row16,row17,row18,row19,row20,row21
 .org $4400
 .incbin "p5-map.bin"
 .org $5000
row0:
 .db 104,104,104,104,104,104,104,105
 .db 0,219,222,229,236,243,250,149
 .db 96,123,127,127,127,127,127,127
row1:
 .db 104,104,106,108,109,110,112,113
 .db 1,220,173,143,196,231,92,230
 .db 96,123,121,101,113,125,107,118
row2:
 .db 104,104,106,108,109,111,112,113
 .db 182,145,98,68,121,0,17,155
 .db 97,125,123,103,115,96,109,120
row3:
 .db 104,105,106,108,109,111,112,113
 .db 253,77,169,139,192,71,88,226
 .db 99,112,125,105,117,98,111,122
row4:
 .db 104,105,105,108,109,111,111,113
 .db 96,176,197,238,35,170,16,69
 .db 101,113,126,106,119,99,127,124
row5:
 .db 104,105,107,108,109,111,112,114
 .db 47,127,0,189,242,121,187,0
 .db 102,114,96,107,119,100,112,96
row6:
 .db 104,105,107,108,110,111,112,114
 .db 116,196,69,2,0,190,0,69
 .db 107,119,101,113,96,105,118,101
row7:
 .db 104,105,107,108,110,111,112,114
 .db 187,11,140,73,71,5,71,140
 .db 110,123,104,116,99,109,121,104
row8:
 .db 104,106,107,108,109,111,112,113
 .db 180,0,133,66,55,254,64,20
 .db 113,96,107,119,125,111,124,125
row9:
 .db 104,106,107,108,110,111,113,114
 .db 123,199,76,9,64,197,0,133
 .db 116,98,110,122,102,114,96,107
row10:
 .db 104,106,107,108,110,111,113,114
 .db 84,160,37,226,25,158,217,94
 .db 119,101,113,124,105,117,98,110
row11:
 .db 104,105,106,108,110,111,112,114
 .db 157,4,12,43,98,231,7,167
 .db 121,126,127,127,107,119,127,112
row12:
 .db 104,106,107,109,110,111,113,114
 .db 94,233,110,0,35,168,34,104
 .db 122,103,115,96,108,120,101,113
row13:
 .db 104,104,104,104,104,104,104,105
 .db 213,216,223,230,237,244,251,150
 .db 123,127,127,127,127,127,127,127
row14:
 .db 104,104,104,104,104,104,104,105
 .db 214,217,224,231,238,245,252,151
 .db 123,127,127,127,127,127,127,127
row15:
 .db 104,104,104,104,104,104,104,105
 .db 215,218,225,232,239,246,253,152
 .db 123,127,127,127,127,127,127,127
row16:
 .db 104,104,104,104,104,104,104,105
 .db 216,219,226,233,240,247,254,153
 .db 123,127,127,127,127,127,127,127
row17:
 .db 104,104,104,104,104,104,104,105
 .db 217,220,227,234,241,248,255,154
 .db 123,127,127,127,127,127,127,127
row18:
 .db 104,104,104,104,104,104,105,105
 .db 218,221,228,235,242,249,148,155
 .db 123,127,127,127,127,127,127,127
row19:
 .db 105,106,107,109,110,111,113,114
 .db 0,96,229,119,154,31,153,223
 .db 96,105,116,97,109,122,102,114
row20:
 .db 105,106,107,109,110,112,113,114
 .db 241,81,214,104,139,0,138,208
 .db 100,110,121,102,114,96,107,119
row21:
 .db 105,106,108,109,110,112,113,123
 .db 190,30,0,53,88,205,87,0
 .db 106,116,96,108,120,101,113,96
 .org $5300
column_entry_lo:
 .db LOW(column33),LOW(column32),LOW(column31),LOW(column30),LOW(column29),LOW(column28),LOW(column27),LOW(column26),LOW(column25),LOW(column24),LOW(column23),LOW(column22),LOW(column21),LOW(column20),LOW(column19),LOW(column18),LOW(column17),LOW(column16),LOW(column15),LOW(column14),LOW(column13),LOW(column12),LOW(column11),LOW(column10),LOW(column9),LOW(column8),LOW(column7),LOW(column6),LOW(column5),LOW(column4),LOW(column3),LOW(column2),LOW(column1),LOW(column0)
column_entry_hi:
 .db HIGH(column33),HIGH(column32),HIGH(column31),HIGH(column30),HIGH(column29),HIGH(column28),HIGH(column27),HIGH(column26),HIGH(column25),HIGH(column24),HIGH(column23),HIGH(column22),HIGH(column21),HIGH(column20),HIGH(column19),HIGH(column18),HIGH(column17),HIGH(column16),HIGH(column15),HIGH(column14),HIGH(column13),HIGH(column12),HIGH(column11),HIGH(column10),HIGH(column9),HIGH(column8),HIGH(column7),HIGH(column6),HIGH(column5),HIGH(column4),HIGH(column3),HIGH(column2),HIGH(column1),HIGH(column0)
column0:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground0
 lda [<$06],y
 tax
 lda [<$0a],y
foreground0:
 stx $0002
 sta $0003
 iny
column1:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground1
 lda [<$06],y
 tax
 lda [<$0a],y
foreground1:
 stx $0002
 sta $0003
 iny
column2:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground2
 lda [<$06],y
 tax
 lda [<$0a],y
foreground2:
 stx $0002
 sta $0003
 iny
column3:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground3
 lda [<$06],y
 tax
 lda [<$0a],y
foreground3:
 stx $0002
 sta $0003
 iny
column4:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground4
 lda [<$06],y
 tax
 lda [<$0a],y
foreground4:
 stx $0002
 sta $0003
 iny
column5:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground5
 lda [<$06],y
 tax
 lda [<$0a],y
foreground5:
 stx $0002
 sta $0003
 iny
column6:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground6
 lda [<$06],y
 tax
 lda [<$0a],y
foreground6:
 stx $0002
 sta $0003
 iny
column7:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground7
 lda [<$06],y
 tax
 lda [<$0a],y
foreground7:
 stx $0002
 sta $0003
 iny
column8:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground8
 lda [<$06],y
 tax
 lda [<$0a],y
foreground8:
 stx $0002
 sta $0003
 iny
column9:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground9
 lda [<$06],y
 tax
 lda [<$0a],y
foreground9:
 stx $0002
 sta $0003
 iny
column10:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground10
 lda [<$06],y
 tax
 lda [<$0a],y
foreground10:
 stx $0002
 sta $0003
 iny
column11:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground11
 lda [<$06],y
 tax
 lda [<$0a],y
foreground11:
 stx $0002
 sta $0003
 iny
column12:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground12
 lda [<$06],y
 tax
 lda [<$0a],y
foreground12:
 stx $0002
 sta $0003
 iny
column13:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground13
 lda [<$06],y
 tax
 lda [<$0a],y
foreground13:
 stx $0002
 sta $0003
 iny
column14:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground14
 lda [<$06],y
 tax
 lda [<$0a],y
foreground14:
 stx $0002
 sta $0003
 iny
column15:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground15
 lda [<$06],y
 tax
 lda [<$0a],y
foreground15:
 stx $0002
 sta $0003
 iny
column16:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground16
 lda [<$06],y
 tax
 lda [<$0a],y
foreground16:
 stx $0002
 sta $0003
 iny
column17:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground17
 lda [<$06],y
 tax
 lda [<$0a],y
foreground17:
 stx $0002
 sta $0003
 iny
column18:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground18
 lda [<$06],y
 tax
 lda [<$0a],y
foreground18:
 stx $0002
 sta $0003
 iny
column19:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground19
 lda [<$06],y
 tax
 lda [<$0a],y
foreground19:
 stx $0002
 sta $0003
 iny
column20:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground20
 lda [<$06],y
 tax
 lda [<$0a],y
foreground20:
 stx $0002
 sta $0003
 iny
column21:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground21
 lda [<$06],y
 tax
 lda [<$0a],y
foreground21:
 stx $0002
 sta $0003
 iny
column22:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground22
 lda [<$06],y
 tax
 lda [<$0a],y
foreground22:
 stx $0002
 sta $0003
 iny
column23:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground23
 lda [<$06],y
 tax
 lda [<$0a],y
foreground23:
 stx $0002
 sta $0003
 iny
column24:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground24
 lda [<$06],y
 tax
 lda [<$0a],y
foreground24:
 stx $0002
 sta $0003
 iny
column25:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground25
 lda [<$06],y
 tax
 lda [<$0a],y
foreground25:
 stx $0002
 sta $0003
 iny
column26:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground26
 lda [<$06],y
 tax
 lda [<$0a],y
foreground26:
 stx $0002
 sta $0003
 iny
column27:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground27
 lda [<$06],y
 tax
 lda [<$0a],y
foreground27:
 stx $0002
 sta $0003
 iny
column28:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground28
 lda [<$06],y
 tax
 lda [<$0a],y
foreground28:
 stx $0002
 sta $0003
 iny
column29:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground29
 lda [<$06],y
 tax
 lda [<$0a],y
foreground29:
 stx $0002
 sta $0003
 iny
column30:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground30
 lda [<$06],y
 tax
 lda [<$0a],y
foreground30:
 stx $0002
 sta $0003
 iny
column31:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground31
 lda [<$06],y
 tax
 lda [<$0a],y
foreground31:
 stx $0002
 sta $0003
 iny
column32:
 ldx $0002
 lda $0003
 cmp #16
 bcs foreground32
 lda [<$06],y
 tax
 lda [<$0a],y
foreground32:
 stx $0002
 sta $0003
 iny
column33:
 rts
renderer_end:
 .bank $68
 .org $6000
 .incbin "p5-code0.bin"
 .bank $69
 .org $6000
 .incbin "p5-code1.bin"
 .bank $6a
 .org $6000
 .incbin "p5-code2.bin"
 .bank $6b
 .org $6000
 .incbin "p5-code3.bin"
 .bank $6c
 .org $6000
 .incbin "p5-code4.bin"
 .bank $6d
 .org $6000
 .incbin "p5-code5.bin"
 .bank $6e
 .org $6000
 .incbin "p5-code6.bin"
 .bank $6f
 .org $6000
 .incbin "p5-code7.bin"
 .bank $70
 .org $6000
 .incbin "p5-code8.bin"
 .bank $71
 .org $6000
 .incbin "p5-code9.bin"
 .bank $72
 .org $6000
 .incbin "p5-code10.bin"
 .bank $7b
 .org $6000
 .incbin "p5-code11.bin"
