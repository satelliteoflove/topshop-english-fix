#!/usr/bin/env python3
"""Make graphics/STAFF1_b1.png: the staff credits' job titles with their spelling fixed.

Each title has its own 256x16 strip of the sheet, centred on column 128.5. The corrected
titles are put together from the sheet's own letters: ASSISTANT takes the T of DIRECTOR,
PROGRAMMER repeats its M, DESIGNER swaps its G and N, SUPERVISOR takes the O and EXECUTIVE
the U of PRODUCER. Gaps between letters follow the same pairs elsewhere in the sheet, and a
word space is 7 clear columns, as in the names (STAFF2, STAFF3), which stay as they are.
Column ranges below are each letter group's solid columns in the original sheet.
"""
import os, sys
import numpy as np
from PIL import Image
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..') + '/'
sys.path.insert(0, R + 'scripts')
import gfx
d = gfx.maybe_lzss(open(R + 'rips/clean/topshop/A/STAFF1.SPC', 'rb').read())
sp, bl = gfx.parse(d)
x, y, w, h, px = bl[1]['img']
idx = gfx.indices(np.frombuffer(px, '<u2').reshape(h, w).astype(np.uint32), 0)
BRI = np.array([0, 232, 216, 200, 184, 168, 144, 120, 112, 96, 80, 64, 48, 32, 16, 248])
SPACE = 7

def strip(row, c0, c1):
    """Columns c0..c1 of a title (the letters' solid columns) plus the faint edge pixels
    just outside them that belong to these letters (next to a solid pixel of the edge)."""
    a = idx[16 * row:16 * row + 16]
    core = a[:, c0:c1 + 1].copy()
    lft = np.where(BRI[a[:, c0]] >= 100, a[:, c0 - 1], 0)
    rgt = np.where(BRI[a[:, c1]] >= 100, a[:, c1 + 1], 0)
    lft = np.where(BRI[lft] < 100, lft, 0); rgt = np.where(BRI[rgt] < 100, rgt, 0)
    return np.concatenate([lft[:, None], core, rgt[:, None]], 1)

def compose(parts):
    """parts: strips and ints (the clear columns between them)."""
    W = sum(p.shape[1] - 2 for p in parts if not isinstance(p, int)) + sum(p for p in parts if isinstance(p, int))
    line = np.zeros((16, W + 2), int)
    x = 1
    for p in parts:
        if isinstance(p, int):
            x += p; continue
        seg = line[:, x - 1:x - 1 + p.shape[1]]
        line[:, x - 1:x - 1 + p.shape[1]] = np.where(BRI[p] > BRI[seg], p, seg)
        x += p.shape[1] - 2
    # centre on column 128.5, like the originals
    left = int(round(128.5 - (W - 1) / 2))
    row = np.zeros((16, 256), int)
    row[:, left - 1:left - 1 + W + 2] = line
    return row

S = strip
new = {
    3: [S(3, 38, 117), 1, S(1, 137, 146), SPACE, S(3, 143, 218)],                       # ASSISTANT PLANNER
    4: [S(4, 54, 93), SPACE, S(4, 96, 179), 2, S(4, 168, 179), 2, S(4, 182, 202)],      # MAIN PROGRAMMER
    5: [S(5, 75, 158), 2, S(5, 147, 158), 2, S(5, 161, 181)],                           # PROGRAMMER
    6: [S(6, 65, 104), SPACE, S(6, 107, 143), 2, S(6, 158, 168), 2, S(6, 146, 155), 2, S(6, 171, 191)],  # MAIN DESIGNER
    7: [S(7, 86, 122), 2, S(7, 137, 147), 2, S(7, 125, 134), 2, S(7, 150, 170)],        # DESIGNER
    8: [S(8, 86, 122), 2, S(8, 137, 147), 2, S(8, 125, 134), 2, S(8, 150, 170)],        # DESIGNER
    9: [S(9, 76, 158), 2, S(0, 105, 115), 2, S(9, 171, 180)],                           # SUPERVISOR
    10: [S(10, 41, 83), 2, S(0, 130, 139), 1, S(10, 85, 121), SPACE, S(10, 123, 215)],  # EXECUTIVE PRODUCER
}
full = idx.copy()
for k, parts in new.items():
    full[16 * k:16 * k + 16] = compose(parts)
vram = np.zeros((512, 1024), np.uint16)
for b in bl:
    X, Y, W, H, P = b['img']
    vram[Y:Y + H, X:X + W] = np.frombuffer(P, '<u2').reshape(H, W)
pal = gfx.palette(vram, 0, 489, 16)
im = Image.fromarray(full.astype(np.uint8), 'P')
im.putpalette([int(v) for c in pal for v in c[:3]] + [0] * 720)
im.save(R + 'graphics/STAFF1_b1.png')
ys, xs = np.nonzero(idx != full)
print(f'{len(ys)} pixels changed, rows {ys.min()}-{ys.max()}, columns {xs.min()}-{xs.max()}')
