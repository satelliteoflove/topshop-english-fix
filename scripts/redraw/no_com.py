#!/usr/bin/env python3
"""Make graphics/SET3_b2.png: the Free Play picture for 0 CPUs, "COM なし", as "NO / COM".

The panel is the top left 64x48 of the sheet's first block (sprite 10). "COM" moves to the
second line, closed up and shifted left to clear the little character peeking in at the
bottom right, and "NO" goes on the first line: the O is the original's, the N is drawn in
the same brush, with the M's soft edges on the outsides of its legs.

The background behind the old lettering comes from the other three CPU pictures, which
share the same background layer pixel for pixel wherever nothing is drawn over it. Where
all three have a character in the way, it's grown from the panel's own hatching, one
pixel at a time from the best-matching 7x7 neighbourhood (Efros and Leung). A few pixels
were then set by hand.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..') + '/'
sys.path.insert(0, R + 'scripts')
import gfx

d = gfx.maybe_lzss(open(R + 'rips/clean/topshop/A/SET3.SPC', 'rb').read())
sp, bl = gfx.parse(d)
x, y, w, h, px = bl[2]['img']
sheet = gfx.indices(np.frombuffer(px, '<u2').reshape(h, w).astype(np.uint32), 1)
vram = np.zeros((512, 1024), np.uint16)
for b in bl:
    X, Y, W, H, P = b['img']
    vram[Y:Y + H, X:X + W] = np.frombuffer(P, '<u2').reshape(H, W)
pal8 = gfx.palette(vram, 0, 487, 256)
pal = pal8[:, :3].astype(float)

panels = np.stack([sheet[48 * k:48 * k + 48, 0:64] for k in range(4)])
P0 = panels[0].copy()
L0 = pal[P0].mean(2)
text = np.zeros((48, 64), bool)
text[4:22, 5:61] = True
text[25:46, 12:53] = True
text[32:, 53:] = False
ink = (L0 < 150) & text
hole = ndimage.binary_dilation(ink, iterations=1) & text

# background from the other panels: colours panel 0 shows away from its lettering, taken
# from the first panel that has one there with nothing drawn right beside it
clean0 = np.zeros((48, 64), bool)
clean0[3:45, 3:61] = True
clean0 &= ~ndimage.binary_dilation(ink, iterations=2)
clean0[30:, 50:] = False
bgset = list(set(np.unique(P0[clean0 & (L0 > 150)]).tolist()))
bg = np.full((48, 64), -1)
for k in (1, 2, 3):
    ok = np.isin(panels[k], bgset)
    ok &= ~ndimage.binary_dilation(~ok, iterations=1)
    take = hole & ok & (bg < 0)
    bg[take] = panels[k][take]

out = P0.copy()
out[hole & (bg >= 0)] = bg[hole & (bg >= 0)]
unknown = hole & (bg < 0)

# the rest grown from the panel's real background
rgb = pal[out].copy()
known = ~unknown
inner = np.zeros((48, 64), bool)
inner[5:43, 5:59] = True
inner[28:, 48:] = False
src = inner & known & ~hole | (inner & hole & (bg >= 0))
src &= ~ndimage.binary_dilation(ink & ~hole, iterations=1)
K = 3
cands = [(r, c) for r, c in zip(*np.nonzero(src)) if K <= r < 48 - K and K <= c < 64 - K]
cpatch = np.stack([rgb[r - K:r + K + 1, c - K:c + K + 1] for r, c in cands])
cknown = np.stack([known[r - K:r + K + 1, c - K:c + K + 1] for r, c in cands])
rng = np.random.default_rng(7)
while unknown.any():
    edge = unknown & ndimage.binary_dilation(known, structure=np.ones((3, 3)))
    pts = list(zip(*np.nonzero(edge)))
    pts.sort(key=lambda p: -known[max(0, p[0] - K):p[0] + K + 1, max(0, p[1] - K):p[1] + K + 1].sum())
    for r, c in pts[:max(1, len(pts) // 3)]:
        r0, c0 = r - K, c - K
        pr = np.zeros((2 * K + 1, 2 * K + 1, 3))
        pk = np.zeros((2 * K + 1, 2 * K + 1), bool)
        for i in range(2 * K + 1):
            for j in range(2 * K + 1):
                rr, cc = r0 + i, c0 + j
                if 0 <= rr < 48 and 0 <= cc < 64 and known[rr, cc]:
                    pr[i, j] = rgb[rr, cc]
                    pk[i, j] = True
        m = pk[None] & cknown
        dist = (((cpatch - pr[None]) ** 2).sum(3) * m).sum((1, 2)) / np.maximum(m.sum((1, 2)), 1)
        best = np.argsort(dist)[:3]
        pick = cands[best[rng.integers(0, len(best))]]
        out[r, c] = out[pick]
        rgb[r, c] = rgb[pick]
        known[r, c] = True
        unknown[r, c] = False


def letter(c0, c1):
    return P0[4:22, c0:c1], ink[4:22, c0:c1]


def paste(gl, r, c):
    g, m = gl
    for i, j in zip(*np.nonzero(m)):
        out[r + i, c + j] = g[i, j]


used = np.unique(P0[2:46, 2:62])
upal = pal[used]
navy = pal[np.bincount(P0[ink & (L0 < 90)]).argmax()]


def draw_N(r0, c0, wN=14, hN=15):
    """Three strokes about 2 pixels wide, drawn at 8x and averaged for soft edges."""
    S = 8
    H, W = (hN + 2) * S, (wN + 2) * S
    yy, xx = np.mgrid[0:H, 0:W] / S

    def seg(ax, ay, bx, by, t=0.95):
        vx, vy = bx - ax, by - ay
        u = np.clip(((xx - ax) * vx + (yy - ay) * vy) / (vx * vx + vy * vy), 0, 1)
        return np.hypot(xx - ax - u * vx, yy - ay - u * vy) < t
    a, b = 2.0, wN - 1.0
    cov = (seg(a, 1.5, a, hN) | seg(a, 1.5, b, hN) | seg(b, 1.5, b, hN))
    cov = cov.reshape(hN + 2, S, wN + 2, S).mean((1, 3))
    for i, j in zip(*np.nonzero(cov > 0.15)):
        col = pal[out[r0 + i, c0 + j]] * (1 - cov[i, j]) + navy * cov[i, j]
        out[r0 + i, c0 + j] = used[np.argmin(((upal - col) ** 2).sum(1))]


draw_N(4, 15)
# the M's soft edges on the outsides of the N's legs: its left-leg sequence on the left,
# plain 80 on the right
left = [80, 80, 90, 80, 80, 80, 90, 91, 91, 91, 90, 90, 80, 80]
for k, r in enumerate(range(5, 19)):
    out[r, 15] = left[k]
    out[r, 29] = 80
paste(letter(24, 40), 4, 34)        # O
paste(letter(6, 22), 24, 2)         # C
paste(letter(24, 40), 24, 19)       # O
paste(letter(42, 61), 24, 35)       # M
# by hand: stray yellows beside the upper O and N
for (r, c), v in {(18, 34): 63, (18, 35): 63, (16, 30): 57, (17, 30): 57,
                  (18, 29): 57, (19, 29): 57}.items():
    out[r, c] = v

full = sheet.copy()
full[0:48, 0:64] = out
im = Image.fromarray(full.astype(np.uint8), 'P')
im.putpalette([int(v) for c in pal8 for v in c[:3]])
im.save(R + 'graphics/SET3_b2.png')
ys, xs = np.nonzero(sheet != full)
print(f'{len(ys)} pixels changed, rows {ys.min()}-{ys.max()}, columns {xs.min()}-{xs.max()}')
