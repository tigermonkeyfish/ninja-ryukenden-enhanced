"""Reusable PC Engine 8x8, four-bitplane background tile helpers.

No game ROMs, addresses, palettes or dependency on the Ninja patch.
Pixel values are palette indices; preserving indices preserves transparency.
"""


def decode_tile(data):
    if len(data) != 32:
        raise ValueError('A PC Engine 8x8 background tile occupies 32 bytes')
    return [[sum(((data[(b // 2) * 16 + y * 2 + b % 2] >> (7 - x)) & 1) << b
                 for b in range(4)) for x in range(8)] for y in range(8)]


def encode_tile(rows):
    if len(rows) != 8 or any(len(row) != 8 for row in rows):
        raise ValueError('Expected eight rows of eight palette indices')
    tile = bytearray(32)
    for y, row in enumerate(rows):
        for x, value in enumerate(row):
            if not isinstance(value, int) or not 0 <= value < 16:
                raise ValueError('Palette indices must be integers from 0 to 15')
            for b in range(4):
                tile[(b // 2) * 16 + y * 2 + b % 2] |= ((value >> b) & 1) << (7 - x)
    return bytes(tile)


def horizontal_phases(left, right):
    """Eight one-pixel phases for adjacent tiles that use the SAME palette.

    The caller must decide which neighboring tile follows at a map boundary.
    This function deliberately knows nothing about a game's wrap or palettes.
    """
    a, b = decode_tile(left), decode_tile(right)
    return tuple(encode_tile([(x + y)[phase:phase + 8] for x, y in zip(a, b)])
                 for phase in range(8))
