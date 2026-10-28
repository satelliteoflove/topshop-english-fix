#!/usr/bin/env python3
"""Make graphics/CORNER.png: the title picture with its small print corrected.

The second line said "TOP SHOP and the and TOP SHOP logo are trademarks of Agetec,Inc."

- "and the and": the second "and" (columns 104-118 of rows 219-227) is cut, and the rest
  of the line moves 17 pixels left. In the original the T's soft left edge (column 120)
  sat one clear column after "and", so it now sits one clear column after "the", the same
  spacing. The first line's descenders end at row 218, so they stay where they are.
- "Agetec,Inc.": words in that line are two clear columns apart, and the comma ran into
  the I with none, so "Inc." moves two pixels right.

Everything around the text is the plain background (index 82).
"""
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
assert (orig[rows, 102:104] == BG).all() and (orig[rows, 119] == BG).all()
full = orig.copy()
# Agetec, Inc.
full[rows, 292:306] = orig[rows, 290:304]
full[rows, 290:292] = BG
# and the TOP SHOP logo
line = full[rows].copy()
SHIFT = 17
full[rows, 120 - SHIFT:306 - SHIFT] = line[:, 120:306]
full[rows, 306 - SHIFT:306] = BG
pal = [int(v) for c in clut for v in ((c & 31) << 3, (c >> 5 & 31) << 3, (c >> 10 & 31) << 3)]
im = Image.fromarray(full, 'P')
im.putpalette(pal)
im.save(R + 'graphics/CORNER.png')
ys, xs = np.nonzero(orig != full)
print(f'{len(ys)} pixels changed, rows {ys.min()}-{ys.max()}, columns {xs.min()}-{xs.max()}')
