"""Decode HuC6270 background layers from VRAM/VCE dumps (background only, no sprites)."""


def vce_rgb(word):
    """VCE colour: bits 0-2 blue, 3-5 red, 6-8 green -> 8-bit RGB (x36 like Geargrafx)."""
    b = word & 7
    r = (word >> 3) & 7
    g = (word >> 6) & 7
    scale = lambda v: (v * 255) // 7
    return (scale(r), scale(g), scale(b))


def words(data):
    return [data[i] | (data[i + 1] << 8) for i in range(0, len(data), 2)]


def bat_dims(mwr):
    w = (32, 64, 128, 128)[(mwr >> 4) & 3]
    h = (32, 64)[(mwr >> 6) & 1]
    return w, h


def tile_rows(vram_words, tile):
    """Return 8 rows of 8 palette indices for a 4bpp tile."""
    base = (tile * 16) & 0x7fff
    out = []
    for y in range(8):
        w01 = vram_words[base + y]
        w23 = vram_words[(base + 8 + y) & 0x7fff]
        p0, p1 = w01 & 255, w01 >> 8
        p2, p3 = w23 & 255, w23 >> 8
        row = []
        for x in range(8):
            bit = 7 - x
            row.append(((p0 >> bit) & 1) | (((p1 >> bit) & 1) << 1) |
                       (((p2 >> bit) & 1) << 2) | (((p3 >> bit) & 1) << 3))
        out.append(row)
    return out


class Background:
    def __init__(self, vram_bytes, pal_bytes, mwr):
        self.vram = words(vram_bytes)
        self.pal = [vce_rgb(w) for w in words(pal_bytes)]
        self.w, self.h = bat_dims(mwr)
        self.bat = self.vram[:self.w * self.h]
        self._cache = {}

    def cell_word(self, cx, cy):
        return self.bat[(cy % self.h) * self.w + (cx % self.w)]

    def cell_pixels(self, word):
        """8x8 RGB for a BAT word; index 0 shows the backdrop (VCE colour 0)."""
        hit = self._cache.get(word)
        if hit is None:
            palette = (word >> 12) * 16
            tile = word & 0xfff
            hit = [tuple(self.pal[0] if v == 0 else self.pal[palette + v] for v in row)
                   for row in tile_rows(self.vram, tile)]
            self._cache[word] = hit
        return hit
