 .org $4300
row_table:
 .dw row0,row1,row2,row3,row4,row5,row6,row7,row8,row9,row10,row11,row12,row13,row14,row15
palette13:
 .dw 0,9,10,74,82,83,137,139,146,154,156,162,218,220,227,293
palette14:
 .dw 0,0,9,10,74,0,0,0,0,0,0,0,0,0,0,0
 .org $4400
 .incbin "p3-map.bin"
 .org $5000
row0:
 .db 87,87,87,87,87,87,87,87
 .db 0,231,184,137,141,145,149,153
 .db 96,125,126,127,127,127,127,127
row1:
 .db 87,87,87,87,87,87,87,87
 .db 1,232,185,138,142,146,150,154
 .db 96,125,126,127,127,127,127,127
row2:
 .db 87,87,87,87,87,87,87,87
 .db 2,233,186,139,143,147,151,155
 .db 96,125,126,127,127,127,127,127
row3:
 .db 87,87,87,87,87,87,87,87
 .db 3,234,187,140,144,148,152,156
 .db 96,125,126,127,127,127,127,127
row4:
 .db 87,88,90,92,92,93,97,99
 .db 4,103,183,187,60,252,74,0
 .db 96,119,110,101,125,124,105,96
row5:
 .db 87,87,87,88,88,89,90,90
 .db 75,235,188,47,252,254,69,18
 .db 98,125,126,126,126,126,126,127
row6:
 .db 87,88,90,92,94,95,97,99
 .db 24,174,254,2,0,240,145,71
 .db 99,121,112,104,96,115,107,98
row7:
 .db 87,89,90,92,94,95,97,99
 .db 153,0,127,131,129,113,18,200
 .db 103,96,117,108,100,120,112,102
row8:
 .db 87,89,91,92,94,96,97,99
 .db 232,79,0,210,208,0,97,23
 .db 108,101,96,113,105,96,117,108
row9:
 .db 87,89,91,92,94,96,98,99
 .db 245,92,13,223,221,13,0,36
 .db 114,107,102,119,111,102,96,114
row10:
 .db 87,89,91,93,94,96,98,99
 .db 82,185,106,0,58,106,93,129
 .db 120,112,107,96,117,107,101,119
row11:
 .db 88,89,91,93,95,96,98,100
 .db 0,78,255,149,0,255,242,0
 .db 96,118,112,101,96,112,106,96
row12:
 .db 88,90,91,93,95,96,98,100
 .db 57,0,56,206,57,56,43,57
 .db 101,96,118,106,101,118,112,101
row13:
 .db 88,89,90,93,94,96,97,100
 .db 166,135,206,59,207,165,110,166
 .db 106,123,122,112,122,123,123,106
row14:
 .db 88,90,92,93,95,97,98,100
 .db 29,109,0,178,166,0,152,29
 .db 110,101,96,115,106,96,117,110
row15:
 .db 88,90,91,93,95,97,98,100
 .db 216,40,165,109,97,187,83,216
 .db 115,107,123,121,112,101,123,115
 .org $5300
; Column copy: N map entries from Y; the BAT read and write pointers start
; at the first entry and <$29/<$2a holds its BAT address minus Y. Only the
; BAT high byte is read. Foreground stays as it is and is not written; the
; write pointer is moved to the next backdrop cell instead (seek_write).
; Rows 12-15 (bottom) also treat palettes 13-15 as backdrop.
column_entry:
 .dw 0,columns_1,columns_2,columns_3,columns_4,columns_5,columns_6,columns_7,columns_8,columns_9,columns_10,columns_11,columns_12,columns_13,columns_14,columns_15,columns_16,columns_17,columns_18,columns_19,columns_20,columns_21,columns_22,columns_23,columns_24,columns_25,columns_26,columns_27,columns_28,columns_29,columns_30,columns_31,columns_32,columns_33
bottom_entry:
 .dw 0,bottom_1,bottom_2,bottom_3,bottom_4,bottom_5,bottom_6,bottom_7,bottom_8,bottom_9,bottom_10,bottom_11,bottom_12,bottom_13,bottom_14,bottom_15,bottom_16,bottom_17,bottom_18,bottom_19,bottom_20,bottom_21,bottom_22,bottom_23,bottom_24,bottom_25,bottom_26,bottom_27,bottom_28,bottom_29,bottom_30,bottom_31,bottom_32,bottom_33
columns_33:
 lda $0003
 cmp #48
 bcc columns_backdrop_33
 jmp columns_skip_33
columns_backdrop_33:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_32:
 lda $0003
 cmp #48
 bcc columns_backdrop_32
 jmp columns_skip_32
columns_backdrop_32:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_31:
 lda $0003
 cmp #48
 bcc columns_backdrop_31
 jmp columns_skip_31
columns_backdrop_31:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_30:
 lda $0003
 cmp #48
 bcc columns_backdrop_30
 jmp columns_skip_30
columns_backdrop_30:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_29:
 lda $0003
 cmp #48
 bcc columns_backdrop_29
 jmp columns_skip_29
columns_backdrop_29:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_28:
 lda $0003
 cmp #48
 bcc columns_backdrop_28
 jmp columns_skip_28
columns_backdrop_28:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_27:
 lda $0003
 cmp #48
 bcc columns_backdrop_27
 jmp columns_skip_27
columns_backdrop_27:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_26:
 lda $0003
 cmp #48
 bcc columns_backdrop_26
 jmp columns_skip_26
columns_backdrop_26:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_25:
 lda $0003
 cmp #48
 bcc columns_backdrop_25
 jmp columns_skip_25
columns_backdrop_25:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_24:
 lda $0003
 cmp #48
 bcc columns_backdrop_24
 jmp columns_skip_24
columns_backdrop_24:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_23:
 lda $0003
 cmp #48
 bcc columns_backdrop_23
 jmp columns_skip_23
columns_backdrop_23:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_22:
 lda $0003
 cmp #48
 bcc columns_backdrop_22
 jmp columns_skip_22
columns_backdrop_22:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_21:
 lda $0003
 cmp #48
 bcc columns_backdrop_21
 jmp columns_skip_21
columns_backdrop_21:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_20:
 lda $0003
 cmp #48
 bcc columns_backdrop_20
 jmp columns_skip_20
columns_backdrop_20:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_19:
 lda $0003
 cmp #48
 bcc columns_backdrop_19
 jmp columns_skip_19
columns_backdrop_19:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_18:
 lda $0003
 cmp #48
 bcc columns_backdrop_18
 jmp columns_skip_18
columns_backdrop_18:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_17:
 lda $0003
 cmp #48
 bcc columns_backdrop_17
 jmp columns_skip_17
columns_backdrop_17:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_16:
 lda $0003
 cmp #48
 bcc columns_backdrop_16
 jmp columns_skip_16
columns_backdrop_16:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_15:
 lda $0003
 cmp #48
 bcc columns_backdrop_15
 jmp columns_skip_15
columns_backdrop_15:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_14:
 lda $0003
 cmp #48
 bcc columns_backdrop_14
 jmp columns_skip_14
columns_backdrop_14:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_13:
 lda $0003
 cmp #48
 bcc columns_backdrop_13
 jmp columns_skip_13
columns_backdrop_13:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_12:
 lda $0003
 cmp #48
 bcc columns_backdrop_12
 jmp columns_skip_12
columns_backdrop_12:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_11:
 lda $0003
 cmp #48
 bcc columns_backdrop_11
 jmp columns_skip_11
columns_backdrop_11:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_10:
 lda $0003
 cmp #48
 bcc columns_backdrop_10
 jmp columns_skip_10
columns_backdrop_10:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_9:
 lda $0003
 cmp #48
 bcc columns_backdrop_9
 jmp columns_skip_9
columns_backdrop_9:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_8:
 lda $0003
 cmp #48
 bcc columns_backdrop_8
 jmp columns_skip_8
columns_backdrop_8:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_7:
 lda $0003
 cmp #48
 bcc columns_backdrop_7
 jmp columns_skip_7
columns_backdrop_7:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_6:
 lda $0003
 cmp #48
 bcc columns_backdrop_6
 jmp columns_skip_6
columns_backdrop_6:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_5:
 lda $0003
 cmp #48
 bcc columns_backdrop_5
 jmp columns_skip_5
columns_backdrop_5:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_4:
 lda $0003
 cmp #48
 bcc columns_backdrop_4
 jmp columns_skip_4
columns_backdrop_4:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_3:
 lda $0003
 cmp #48
 bcc columns_backdrop_3
 jmp columns_skip_3
columns_backdrop_3:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_2:
 lda $0003
 cmp #48
 bcc columns_backdrop_2
 jmp columns_skip_2
columns_backdrop_2:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
columns_1:
 lda $0003
 cmp #48
 bcc columns_backdrop_1
 jmp columns_skip_1
columns_backdrop_1:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
 rts
columns_unsynced_33:
 lda $0003
 cmp #48
 bcc columns_rejoin_33
columns_skip_33:
 iny
columns_unsynced_32:
 lda $0003
 cmp #48
 bcc columns_rejoin_32
columns_skip_32:
 iny
columns_unsynced_31:
 lda $0003
 cmp #48
 bcc columns_rejoin_31
columns_skip_31:
 iny
columns_unsynced_30:
 lda $0003
 cmp #48
 bcc columns_rejoin_30
columns_skip_30:
 iny
columns_unsynced_29:
 lda $0003
 cmp #48
 bcc columns_rejoin_29
columns_skip_29:
 iny
columns_unsynced_28:
 lda $0003
 cmp #48
 bcc columns_rejoin_28
columns_skip_28:
 iny
columns_unsynced_27:
 lda $0003
 cmp #48
 bcc columns_rejoin_27
columns_skip_27:
 iny
columns_unsynced_26:
 lda $0003
 cmp #48
 bcc columns_rejoin_26
columns_skip_26:
 iny
 bra columns_unsynced_25
columns_rejoin_33:
 jsr seek_write
 jmp columns_backdrop_33
columns_rejoin_32:
 jsr seek_write
 jmp columns_backdrop_32
columns_rejoin_31:
 jsr seek_write
 jmp columns_backdrop_31
columns_rejoin_30:
 jsr seek_write
 jmp columns_backdrop_30
columns_rejoin_29:
 jsr seek_write
 jmp columns_backdrop_29
columns_rejoin_28:
 jsr seek_write
 jmp columns_backdrop_28
columns_rejoin_27:
 jsr seek_write
 jmp columns_backdrop_27
columns_rejoin_26:
 jsr seek_write
 jmp columns_backdrop_26
columns_unsynced_25:
 lda $0003
 cmp #48
 bcc columns_rejoin_25
columns_skip_25:
 iny
columns_unsynced_24:
 lda $0003
 cmp #48
 bcc columns_rejoin_24
columns_skip_24:
 iny
columns_unsynced_23:
 lda $0003
 cmp #48
 bcc columns_rejoin_23
columns_skip_23:
 iny
columns_unsynced_22:
 lda $0003
 cmp #48
 bcc columns_rejoin_22
columns_skip_22:
 iny
columns_unsynced_21:
 lda $0003
 cmp #48
 bcc columns_rejoin_21
columns_skip_21:
 iny
columns_unsynced_20:
 lda $0003
 cmp #48
 bcc columns_rejoin_20
columns_skip_20:
 iny
columns_unsynced_19:
 lda $0003
 cmp #48
 bcc columns_rejoin_19
columns_skip_19:
 iny
columns_unsynced_18:
 lda $0003
 cmp #48
 bcc columns_rejoin_18
columns_skip_18:
 iny
 bra columns_unsynced_17
columns_rejoin_25:
 jsr seek_write
 jmp columns_backdrop_25
columns_rejoin_24:
 jsr seek_write
 jmp columns_backdrop_24
columns_rejoin_23:
 jsr seek_write
 jmp columns_backdrop_23
columns_rejoin_22:
 jsr seek_write
 jmp columns_backdrop_22
columns_rejoin_21:
 jsr seek_write
 jmp columns_backdrop_21
columns_rejoin_20:
 jsr seek_write
 jmp columns_backdrop_20
columns_rejoin_19:
 jsr seek_write
 jmp columns_backdrop_19
columns_rejoin_18:
 jsr seek_write
 jmp columns_backdrop_18
columns_unsynced_17:
 lda $0003
 cmp #48
 bcc columns_rejoin_17
columns_skip_17:
 iny
columns_unsynced_16:
 lda $0003
 cmp #48
 bcc columns_rejoin_16
columns_skip_16:
 iny
columns_unsynced_15:
 lda $0003
 cmp #48
 bcc columns_rejoin_15
columns_skip_15:
 iny
columns_unsynced_14:
 lda $0003
 cmp #48
 bcc columns_rejoin_14
columns_skip_14:
 iny
columns_unsynced_13:
 lda $0003
 cmp #48
 bcc columns_rejoin_13
columns_skip_13:
 iny
columns_unsynced_12:
 lda $0003
 cmp #48
 bcc columns_rejoin_12
columns_skip_12:
 iny
columns_unsynced_11:
 lda $0003
 cmp #48
 bcc columns_rejoin_11
columns_skip_11:
 iny
columns_unsynced_10:
 lda $0003
 cmp #48
 bcc columns_rejoin_10
columns_skip_10:
 iny
 bra columns_unsynced_9
columns_rejoin_17:
 jsr seek_write
 jmp columns_backdrop_17
columns_rejoin_16:
 jsr seek_write
 jmp columns_backdrop_16
columns_rejoin_15:
 jsr seek_write
 jmp columns_backdrop_15
columns_rejoin_14:
 jsr seek_write
 jmp columns_backdrop_14
columns_rejoin_13:
 jsr seek_write
 jmp columns_backdrop_13
columns_rejoin_12:
 jsr seek_write
 jmp columns_backdrop_12
columns_rejoin_11:
 jsr seek_write
 jmp columns_backdrop_11
columns_rejoin_10:
 jsr seek_write
 jmp columns_backdrop_10
columns_unsynced_9:
 lda $0003
 cmp #48
 bcc columns_rejoin_9
columns_skip_9:
 iny
columns_unsynced_8:
 lda $0003
 cmp #48
 bcc columns_rejoin_8
columns_skip_8:
 iny
columns_unsynced_7:
 lda $0003
 cmp #48
 bcc columns_rejoin_7
columns_skip_7:
 iny
columns_unsynced_6:
 lda $0003
 cmp #48
 bcc columns_rejoin_6
columns_skip_6:
 iny
columns_unsynced_5:
 lda $0003
 cmp #48
 bcc columns_rejoin_5
columns_skip_5:
 iny
columns_unsynced_4:
 lda $0003
 cmp #48
 bcc columns_rejoin_4
columns_skip_4:
 iny
columns_unsynced_3:
 lda $0003
 cmp #48
 bcc columns_rejoin_3
columns_skip_3:
 iny
columns_unsynced_2:
 lda $0003
 cmp #48
 bcc columns_rejoin_2
columns_skip_2:
 iny
 bra columns_unsynced_1
columns_rejoin_9:
 jsr seek_write
 jmp columns_backdrop_9
columns_rejoin_8:
 jsr seek_write
 jmp columns_backdrop_8
columns_rejoin_7:
 jsr seek_write
 jmp columns_backdrop_7
columns_rejoin_6:
 jsr seek_write
 jmp columns_backdrop_6
columns_rejoin_5:
 jsr seek_write
 jmp columns_backdrop_5
columns_rejoin_4:
 jsr seek_write
 jmp columns_backdrop_4
columns_rejoin_3:
 jsr seek_write
 jmp columns_backdrop_3
columns_rejoin_2:
 jsr seek_write
 jmp columns_backdrop_2
columns_unsynced_1:
 lda $0003
 cmp #48
 bcc columns_rejoin_1
columns_skip_1:
 iny
 rts
columns_rejoin_1:
 jsr seek_write
 jmp columns_backdrop_1
bottom_33:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_33
 cmp #48
 bcc bottom_backdrop_33
 jmp bottom_skip_33
bottom_backdrop_33:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_32:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_32
 cmp #48
 bcc bottom_backdrop_32
 jmp bottom_skip_32
bottom_backdrop_32:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_31:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_31
 cmp #48
 bcc bottom_backdrop_31
 jmp bottom_skip_31
bottom_backdrop_31:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_30:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_30
 cmp #48
 bcc bottom_backdrop_30
 jmp bottom_skip_30
bottom_backdrop_30:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_29:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_29
 cmp #48
 bcc bottom_backdrop_29
 jmp bottom_skip_29
bottom_backdrop_29:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_28:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_28
 cmp #48
 bcc bottom_backdrop_28
 jmp bottom_skip_28
bottom_backdrop_28:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_27:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_27
 cmp #48
 bcc bottom_backdrop_27
 jmp bottom_skip_27
bottom_backdrop_27:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_26:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_26
 cmp #48
 bcc bottom_backdrop_26
 jmp bottom_skip_26
bottom_backdrop_26:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_25:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_25
 cmp #48
 bcc bottom_backdrop_25
 jmp bottom_skip_25
bottom_backdrop_25:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_24:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_24
 cmp #48
 bcc bottom_backdrop_24
 jmp bottom_skip_24
bottom_backdrop_24:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_23:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_23
 cmp #48
 bcc bottom_backdrop_23
 jmp bottom_skip_23
bottom_backdrop_23:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_22:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_22
 cmp #48
 bcc bottom_backdrop_22
 jmp bottom_skip_22
bottom_backdrop_22:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_21:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_21
 cmp #48
 bcc bottom_backdrop_21
 jmp bottom_skip_21
bottom_backdrop_21:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_20:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_20
 cmp #48
 bcc bottom_backdrop_20
 jmp bottom_skip_20
bottom_backdrop_20:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_19:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_19
 cmp #48
 bcc bottom_backdrop_19
 jmp bottom_skip_19
bottom_backdrop_19:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_18:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_18
 cmp #48
 bcc bottom_backdrop_18
 jmp bottom_skip_18
bottom_backdrop_18:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_17:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_17
 cmp #48
 bcc bottom_backdrop_17
 jmp bottom_skip_17
bottom_backdrop_17:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_16:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_16
 cmp #48
 bcc bottom_backdrop_16
 jmp bottom_skip_16
bottom_backdrop_16:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_15:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_15
 cmp #48
 bcc bottom_backdrop_15
 jmp bottom_skip_15
bottom_backdrop_15:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_14:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_14
 cmp #48
 bcc bottom_backdrop_14
 jmp bottom_skip_14
bottom_backdrop_14:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_13:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_13
 cmp #48
 bcc bottom_backdrop_13
 jmp bottom_skip_13
bottom_backdrop_13:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_12:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_12
 cmp #48
 bcc bottom_backdrop_12
 jmp bottom_skip_12
bottom_backdrop_12:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_11:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_11
 cmp #48
 bcc bottom_backdrop_11
 jmp bottom_skip_11
bottom_backdrop_11:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_10:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_10
 cmp #48
 bcc bottom_backdrop_10
 jmp bottom_skip_10
bottom_backdrop_10:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_9:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_9
 cmp #48
 bcc bottom_backdrop_9
 jmp bottom_skip_9
bottom_backdrop_9:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_8:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_8
 cmp #48
 bcc bottom_backdrop_8
 jmp bottom_skip_8
bottom_backdrop_8:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_7:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_7
 cmp #48
 bcc bottom_backdrop_7
 jmp bottom_skip_7
bottom_backdrop_7:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_6:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_6
 cmp #48
 bcc bottom_backdrop_6
 jmp bottom_skip_6
bottom_backdrop_6:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_5:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_5
 cmp #48
 bcc bottom_backdrop_5
 jmp bottom_skip_5
bottom_backdrop_5:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_4:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_4
 cmp #48
 bcc bottom_backdrop_4
 jmp bottom_skip_4
bottom_backdrop_4:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_3:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_3
 cmp #48
 bcc bottom_backdrop_3
 jmp bottom_skip_3
bottom_backdrop_3:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_2:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_2
 cmp #48
 bcc bottom_backdrop_2
 jmp bottom_skip_2
bottom_backdrop_2:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
bottom_1:
 lda $0003
 cmp #$d0
 bcs bottom_backdrop_1
 cmp #48
 bcc bottom_backdrop_1
 jmp bottom_skip_1
bottom_backdrop_1:
 lda [<$06],y
 sta $0002
 lda [<$0a],y
 sta $0003
 iny
 rts
bottom_unsynced_33:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_33
 cmp #48
 bcc bottom_rejoin_33
bottom_skip_33:
 iny
bottom_unsynced_32:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_32
 cmp #48
 bcc bottom_rejoin_32
bottom_skip_32:
 iny
bottom_unsynced_31:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_31
 cmp #48
 bcc bottom_rejoin_31
bottom_skip_31:
 iny
bottom_unsynced_30:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_30
 cmp #48
 bcc bottom_rejoin_30
bottom_skip_30:
 iny
bottom_unsynced_29:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_29
 cmp #48
 bcc bottom_rejoin_29
bottom_skip_29:
 iny
bottom_unsynced_28:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_28
 cmp #48
 bcc bottom_rejoin_28
bottom_skip_28:
 iny
 bra bottom_unsynced_27
bottom_rejoin_33:
 jsr seek_write
 jmp bottom_backdrop_33
bottom_rejoin_32:
 jsr seek_write
 jmp bottom_backdrop_32
bottom_rejoin_31:
 jsr seek_write
 jmp bottom_backdrop_31
bottom_rejoin_30:
 jsr seek_write
 jmp bottom_backdrop_30
bottom_rejoin_29:
 jsr seek_write
 jmp bottom_backdrop_29
bottom_rejoin_28:
 jsr seek_write
 jmp bottom_backdrop_28
bottom_unsynced_27:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_27
 cmp #48
 bcc bottom_rejoin_27
bottom_skip_27:
 iny
bottom_unsynced_26:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_26
 cmp #48
 bcc bottom_rejoin_26
bottom_skip_26:
 iny
bottom_unsynced_25:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_25
 cmp #48
 bcc bottom_rejoin_25
bottom_skip_25:
 iny
bottom_unsynced_24:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_24
 cmp #48
 bcc bottom_rejoin_24
bottom_skip_24:
 iny
bottom_unsynced_23:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_23
 cmp #48
 bcc bottom_rejoin_23
bottom_skip_23:
 iny
bottom_unsynced_22:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_22
 cmp #48
 bcc bottom_rejoin_22
bottom_skip_22:
 iny
 bra bottom_unsynced_21
bottom_rejoin_27:
 jsr seek_write
 jmp bottom_backdrop_27
bottom_rejoin_26:
 jsr seek_write
 jmp bottom_backdrop_26
bottom_rejoin_25:
 jsr seek_write
 jmp bottom_backdrop_25
bottom_rejoin_24:
 jsr seek_write
 jmp bottom_backdrop_24
bottom_rejoin_23:
 jsr seek_write
 jmp bottom_backdrop_23
bottom_rejoin_22:
 jsr seek_write
 jmp bottom_backdrop_22
bottom_unsynced_21:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_21
 cmp #48
 bcc bottom_rejoin_21
bottom_skip_21:
 iny
bottom_unsynced_20:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_20
 cmp #48
 bcc bottom_rejoin_20
bottom_skip_20:
 iny
bottom_unsynced_19:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_19
 cmp #48
 bcc bottom_rejoin_19
bottom_skip_19:
 iny
bottom_unsynced_18:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_18
 cmp #48
 bcc bottom_rejoin_18
bottom_skip_18:
 iny
bottom_unsynced_17:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_17
 cmp #48
 bcc bottom_rejoin_17
bottom_skip_17:
 iny
bottom_unsynced_16:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_16
 cmp #48
 bcc bottom_rejoin_16
bottom_skip_16:
 iny
 bra bottom_unsynced_15
bottom_rejoin_21:
 jsr seek_write
 jmp bottom_backdrop_21
bottom_rejoin_20:
 jsr seek_write
 jmp bottom_backdrop_20
bottom_rejoin_19:
 jsr seek_write
 jmp bottom_backdrop_19
bottom_rejoin_18:
 jsr seek_write
 jmp bottom_backdrop_18
bottom_rejoin_17:
 jsr seek_write
 jmp bottom_backdrop_17
bottom_rejoin_16:
 jsr seek_write
 jmp bottom_backdrop_16
bottom_unsynced_15:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_15
 cmp #48
 bcc bottom_rejoin_15
bottom_skip_15:
 iny
bottom_unsynced_14:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_14
 cmp #48
 bcc bottom_rejoin_14
bottom_skip_14:
 iny
bottom_unsynced_13:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_13
 cmp #48
 bcc bottom_rejoin_13
bottom_skip_13:
 iny
bottom_unsynced_12:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_12
 cmp #48
 bcc bottom_rejoin_12
bottom_skip_12:
 iny
bottom_unsynced_11:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_11
 cmp #48
 bcc bottom_rejoin_11
bottom_skip_11:
 iny
bottom_unsynced_10:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_10
 cmp #48
 bcc bottom_rejoin_10
bottom_skip_10:
 iny
 bra bottom_unsynced_9
bottom_rejoin_15:
 jsr seek_write
 jmp bottom_backdrop_15
bottom_rejoin_14:
 jsr seek_write
 jmp bottom_backdrop_14
bottom_rejoin_13:
 jsr seek_write
 jmp bottom_backdrop_13
bottom_rejoin_12:
 jsr seek_write
 jmp bottom_backdrop_12
bottom_rejoin_11:
 jsr seek_write
 jmp bottom_backdrop_11
bottom_rejoin_10:
 jsr seek_write
 jmp bottom_backdrop_10
bottom_unsynced_9:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_9
 cmp #48
 bcc bottom_rejoin_9
bottom_skip_9:
 iny
bottom_unsynced_8:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_8
 cmp #48
 bcc bottom_rejoin_8
bottom_skip_8:
 iny
bottom_unsynced_7:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_7
 cmp #48
 bcc bottom_rejoin_7
bottom_skip_7:
 iny
bottom_unsynced_6:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_6
 cmp #48
 bcc bottom_rejoin_6
bottom_skip_6:
 iny
bottom_unsynced_5:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_5
 cmp #48
 bcc bottom_rejoin_5
bottom_skip_5:
 iny
bottom_unsynced_4:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_4
 cmp #48
 bcc bottom_rejoin_4
bottom_skip_4:
 iny
 bra bottom_unsynced_3
bottom_rejoin_9:
 jsr seek_write
 jmp bottom_backdrop_9
bottom_rejoin_8:
 jsr seek_write
 jmp bottom_backdrop_8
bottom_rejoin_7:
 jsr seek_write
 jmp bottom_backdrop_7
bottom_rejoin_6:
 jsr seek_write
 jmp bottom_backdrop_6
bottom_rejoin_5:
 jsr seek_write
 jmp bottom_backdrop_5
bottom_rejoin_4:
 jsr seek_write
 jmp bottom_backdrop_4
bottom_unsynced_3:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_3
 cmp #48
 bcc bottom_rejoin_3
bottom_skip_3:
 iny
bottom_unsynced_2:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_2
 cmp #48
 bcc bottom_rejoin_2
bottom_skip_2:
 iny
bottom_unsynced_1:
 lda $0003
 cmp #$d0
 bcs bottom_rejoin_1
 cmp #48
 bcc bottom_rejoin_1
bottom_skip_1:
 iny
 rts
bottom_rejoin_3:
 jsr seek_write
 jmp bottom_backdrop_3
bottom_rejoin_2:
 jsr seek_write
 jmp bottom_backdrop_2
bottom_rejoin_1:
 jsr seek_write
 jmp bottom_backdrop_1
seek_write:
 tya
 clc
 adc <$29
 stz <$11
 st0 #0
 sta $0002
 lda <$2a
 adc #0
 sta $0003
 lda #2
 sta <$11
 st0 #2
 rts
; Rows whose map entries are all equal (native_backdrops.py), indexed by the
; row counter <$28 - 1 (row 15 first): a whole-tile backdrop move leaves them
; unchanged.
uniform_rows:
 .db 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
renderer_end:
 .if (renderer_end > $6000)
 .fail
 .endif
 .bank $57
 .org $6000
 .incbin "p3-code0.bin"
 .bank $58
 .org $6000
 .incbin "p3-code1.bin"
 .bank $59
 .org $6000
 .incbin "p3-code2.bin"
 .bank $5a
 .org $6000
 .incbin "p3-code3.bin"
 .bank $5b
 .org $6000
 .incbin "p3-code4.bin"
 .bank $5c
 .org $6000
 .incbin "p3-code5.bin"
 .bank $5d
 .org $6000
 .incbin "p3-code6.bin"
 .bank $5e
 .org $6000
 .incbin "p3-code7.bin"
 .bank $5f
 .org $6000
 .incbin "p3-code8.bin"
 .bank $60
 .org $6000
 .incbin "p3-code9.bin"
 .bank $61
 .org $6000
 .incbin "p3-code10.bin"
 .bank $62
 .org $6000
 .incbin "p3-code11.bin"
 .bank $63
 .org $6000
 .incbin "p3-code12.bin"
 .bank $64
 .org $6000
 .incbin "p3-code13.bin"
 .bank $65
 .org $6000
 .incbin "p3-code14.bin"
 .bank $66
 .org $6000
 .incbin "p3-code15.bin"
