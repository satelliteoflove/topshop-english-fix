#!/usr/bin/env python3
"""Make graphics/SET2_b11.png: the Story Mode menu's "From Bigining" as "From Beginning".

The letters all come from the same sheet (SET2.SPC). B, g, i and n are from "Bigining"
itself; the e is from "From Stage", which uses another CLUT, so it's recoloured row by row
to the shading of the n. Each letter is cut out with its outline columns, which it shares
with its neighbours, so the bits of neighbouring letters it picks up (the i dots above,
the g tails below) are dropped before the letters are put back side by side. The sprite
is widened from 80 to 96 pixels in graphics.json; the strip that uncovers was empty.
"""
import os, sys
import numpy as np
from PIL import Image
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..') + '/'
sys.path.insert(0, R + 'scripts')
import gfx

d = gfx.maybe_lzss(open(R + 'rips/clean/topshop/A/SET2.SPC', 'rb').read())
sp, bl = gfx.parse(d)


def idx(k):
    x, y, w, h, px = bl[k]['img']
    return gfx.indices(np.frombuffer(px, '<u2').reshape(h, w).astype(np.uint32), 0)


low = idx(11)[240:256]      # Continue / From Bigining / Off
top = idx(10)[0:16]         # the first From Stage

e = top[:, 316:324].copy()
n = low[:, 118:126]
for r in range(16):
    v = [c for c in n[r] if c > 1]
    if v:
        e[r][e[r] > 1] = max(set(v), key=v.count)
G = {'B': low[:, 97:106], 'e': e, 'g': low[:, 108:116], 'i': low[:, 115:119],
     'n': low[:, 118:126], 'g2': low[:, 135:143]}
G = {k: v.copy() for k, v in G.items()}
G['B'][0:4, -1] = 0
for k in ('e', 'n'):
    G[k][0:4] = 0
    G[k][13:] = 0
G['i'][13:] = 0
G['g'][0:4] = 0
G['g2'][0:4] = 0

new = low.copy()
new[:, 97:176] = 0
c = 97
for k in ['B', 'e', 'g', 'i', 'n', 'n', 'i', 'n', 'g2']:
    gl = G[k]
    new[:, c:c + gl.shape[1]] = np.where(gl > 0, gl, new[:, c:c + gl.shape[1]])
    c += gl.shape[1] - 1

full = idx(11).copy()
full[240:256] = new
vram = np.zeros((512, 1024), np.uint16)
for b in bl:
    X, Y, W, H, P = b['img']
    vram[Y:Y + H, X:X + W] = np.frombuffer(P, '<u2').reshape(H, W)
pal = gfx.palette(vram, 160, 490, 16)
im = Image.fromarray(full.astype(np.uint8), 'P')
im.putpalette([int(v) for col in pal for v in col[:3]] + [0] * (768 - 48))
im.save(R + 'graphics/SET2_b11.png')
ys, xs = np.nonzero(idx(11) != full)
print(f'{len(ys)} pixels changed, rows {ys.min()}-{ys.max()}, columns {xs.min()}-{xs.max()}')
