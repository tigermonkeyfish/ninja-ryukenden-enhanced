"""Emit the 2-2 column copy (two chains, normal and bottom rows)."""
N = 33
out = []
w = out.append


def variant(prefix, test_bg, test_fg_skip, seg):
    """test_bg(n, target): lines that branch to target for backdrop; fall through for foreground."""
    for n in range(N, 0, -1):
        w(f'{prefix}_{n}:')
        w(' lda $0003')
        out.extend(test_bg(f'{prefix}_backdrop_{n}'))
        w(f' jmp {prefix}_skip_{n}')
        w(f'{prefix}_backdrop_{n}:')
        w(' lda [<$06],y')
        w(' sta $0002')
        w(' lda [<$0a],y')
        w(' sta $0003')
        w(' iny')
    w(' rts')
    entries = list(range(N, 0, -1))
    for s in range(0, N, seg):
        part = entries[s:s + seg]
        for n in part:
            w(f'{prefix}_unsynced_{n}:')
            w(' lda $0003')
            out.extend(test_bg(f'{prefix}_rejoin_{n}'))
            w(f'{prefix}_skip_{n}:')
            w(' iny')
        nxt = entries[s + seg] if s + seg < N else None
        w(f' bra {prefix}_unsynced_{nxt}' if nxt else ' rts')
        for n in part:
            w(f'{prefix}_rejoin_{n}:')
            w(' jsr seek_write')
            w(f' jmp {prefix}_backdrop_{n}')


w('; Column copy: N map entries from Y; the BAT read and write pointers start')
w('; at the first entry and <$29/<$2a holds its BAT address minus Y. Only the')
w('; BAT high byte is read. Foreground stays as it is and is not written; the')
w('; write pointer is moved to the next backdrop cell instead (seek_write).')
w('; Rows 12-15 (bottom) also treat palettes 13-15 as backdrop.')
w('column_entry:')
w(' .dw 0,' + ','.join(f'columns_{n}' for n in range(1, N + 1)))
w('bottom_entry:')
w(' .dw 0,' + ','.join(f'bottom_{n}' for n in range(1, N + 1)))
variant('columns', lambda t: [' cmp #48', f' bcc {t}'], None, 8)
variant('bottom', lambda t: [' cmp #$d0', f' bcs {t}', ' cmp #48', f' bcc {t}'], None, 6)
w('seek_write:')
w(' tya')
w(' clc')
w(' adc <$29')
w(' stz <$11')
w(' st0 #0')
w(' sta $0002')
w(' lda <$2a')
w(' adc #0')
w(' sta $0003')
w(' lda #2')
w(' sta <$11')
w(' st0 #2')
w(' rts')
print('\n'.join(out))
