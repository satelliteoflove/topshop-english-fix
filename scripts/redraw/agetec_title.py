#!/usr/bin/env python3
"""Make graphics/CORNER.png: the title picture with a space in "Agetec,Inc." at the end of
its small print. Words in that line are two clear columns apart, and the comma ran into
the I with none, so "Inc." (columns 290-303 of rows 219-227) moves two pixels right. The
rest of the line, and everything after it to the right edge, is the plain background."""
import os, struct
import numpy as np
from PIL import Image
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..') + '/'

b = open(R + 'rips/clean/topshop/A/CORNER.TIM', 'rb').read()
n = struct.unpack_from('<I', b, 8)[0]
clut = np.frombuffer(b[20:8 + n], '<u2').astype(np.uint32)
size, x, y, w, h = struct.unpack_from('<I4H', b, 8 + n)
orig = np.frombuffer(b[8 + n + 12:8 + n + size], np.uint8).reshape(h, w * 2)
BG = 82
rows = slice(219, 228)
assert (orig[200:240, 304:320] == BG).all() and (orig[rows, 288:290] != BG).any()
full = orig.copy()
full[rows, 292:306] = orig[rows, 290:304]
full[rows, 290:292] = BG
pal = [int(v) for c in clut for v in ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)]
im = Image.fromarray(full, 'P')
im.putpalette(pal)
im.save(R + 'graphics/CORNER.png')
ys, xs = np.nonzero(orig != full)
print(f'{len(ys)} pixels changed, rows {ys.min()}-{ys.max()}, columns {xs.min()}-{xs.max()}')
