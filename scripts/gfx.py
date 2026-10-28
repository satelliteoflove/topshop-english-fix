#!/usr/bin/env python3
"""Render every image on a Top Shop (or Tenant Wars) disc to PNG, for surveying.

    gfx.py DISCROOT OUTDIR

DISCROOT is an extracted disc (rips/clean/topshop or rips/jp/tw); everything under its A/
is read. Writes OUTDIR/<source>_<n>.png for each image block and OUTDIR/index.json.

Graphics come in three wrappers, all of them sequences of TIM-style blocks (a u32 tag, a
u32 flags word, then a u32 size, x, y, w, h and the data, as uploaded to video RAM):

- .TIM files, and .SPC files that decompress (LZSS) to one or more TIMs.
- .SPC sprite sheets: a u32 sprite count, 16 bytes per sprite (u16 depth (0 = 4-bit,
  1 = 8-bit), CLUT x, CLUT y, unused, then the sprite's VRAM x, y, w, h), then blocks:
  tag 0x11 is a CLUT, tag 0x10 an image. Their flags don't give the depth; the sprites do.
- .J archive entries, raw or LZSS, holding the same block sequences (EVE entry 2 etc.),
  with a CLUT block first. Their flags are 2 on every block, so the depth goes by the
  CLUT's width.

Each source is uploaded into its own video RAM, and every image block is drawn with the
CLUTs of the sprites that sit in it. Parts no sprite covers use the block's most common
sprite CLUT, or its own, or the first CLUT the source uploads. Colour 0 (transparent) is
drawn on a dark grey ground.
"""
import hashlib, json, os, struct, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lzss

GROUND = (40, 40, 44)


def maybe_lzss(e):
    if len(e) >= 8 and 0 <= len(e) - struct.unpack_from('<I', e, 0)[0] < 4 and e[:4] not in (b'\x10\0\0\0', b'\x11\0\0\0'):
        try:
            return lzss.decompress(e)
        except Exception:
            pass
    return e


def blocks_at(d, p):
    """Parse TIM-style blocks from p. Returns a list of dicts, or None if p isn't one."""
    out = []
    while p + 20 <= len(d):
        tag, flags = struct.unpack_from('<II', d, p)
        if tag not in (0x10, 0x11) or flags > 0xb:
            break
        q = p + 8
        b = {'tag': tag, 'flags': flags}
        try:
            if tag == 0x10 and flags & 8:
                n, x, y, w, h = struct.unpack_from('<I4H', d, q)
                if n != 12 + w * h * 2:
                    break
                b['clut'] = (x, y, w, h, d[q + 12:q + n]); q += n
            n, x, y, w, h = struct.unpack_from('<I4H', d, q)
        except struct.error:
            break
        if n < 12 or w == 0 or h == 0 or x + w > 1024 or y + h > 512 or n != 12 + w * h * 2 or q + n > len(d):
            break
        b['img'] = (x, y, w, h, d[q + 12:q + n])
        out.append(b); p = q + n
    return out or None


def parse(d):
    """(sprites, blocks) for a TIM sequence or a sprite sheet, or None."""
    bl = blocks_at(d, 0)
    if bl:
        return [], bl
    if len(d) >= 4:
        n = struct.unpack_from('<I', d, 0)[0]
        if 0 < n < 4096 and 4 + 16 * n + 20 <= len(d):
            bl = blocks_at(d, 4 + 16 * n)
            if bl:
                return [struct.unpack_from('<8H', d, 4 + 16 * i) for i in range(n)], bl
    return None


def palette(vram, cx, cy, n):
    row = vram[cy, cx:cx + n].astype(np.uint32)
    if len(row) < n:
        row = np.concatenate([row, np.zeros(n - len(row), np.uint32)])
    r, g, b = (row & 31) << 3, ((row >> 5) & 31) << 3, ((row >> 10) & 31) << 3
    a = np.where(row == 0, 0, 255)
    return np.stack([r, g, b, a], 1).astype(np.uint8)


def indices(raw, bpp):
    if bpp == 0:
        return np.stack([(raw >> s) & 15 for s in (0, 4, 8, 12)], 2).reshape(raw.shape[0], -1)
    if bpp == 1:
        return np.stack([raw & 255, raw >> 8], 2).reshape(raw.shape[0], -1)
    return None


def render_group(parts):
    """parts: [(label, data)] sharing one video RAM, uploaded in order (an archive's
    entries: the face and character archives keep their CLUT in entry 0). Yields
    (label, image, info) for every image block."""
    parsed = [(label, parse(d)) for label, d in parts]
    parsed = [(label, pr) for label, pr in parsed if pr]
    if not parsed:
        return
    sprites = [s for _, pr in parsed for s in pr[0]]
    allblocks = [(label, b) for label, pr in parsed for b in pr[1]]
    vram = np.zeros((512, 1024), np.uint16)
    cluts = []
    for _, b in allblocks:
        for key in ('clut', 'img'):
            if key in b:
                x, y, w, h, px = b[key]
                vram[y:y + h, x:x + w] = np.frombuffer(px, '<u2').reshape(h, w)
        if 'clut' in b:
            cluts.append(b['clut'][:4])
        elif b['tag'] == 0x11:
            cluts.append(b['img'][:4])
    for k, (label, b) in enumerate(allblocks):
        if b['tag'] == 0x11:
            continue
        x, y, w, h, px = b['img']
        inside = [s for s in sprites if x <= s[4] < x + w and y <= s[5] < y + h]
        if inside:
            depths = [s[0] for s in inside]
            order = sorted(set(depths), key=lambda d: -depths.count(d))
        elif 'clut' in b or not cluts:
            order = [b['flags'] & 3]
        else:
            # Beside separate CLUT blocks the flags word isn't the depth (archive entries
            # say 2 on CLUTs and images alike); go by the CLUTs' width.
            order = [1 if any(c[2] >= 256 for c in cluts) else 0]
        raw = vram[y:y + h, x:x + w].astype(np.uint32)
        h1 = hashlib.sha1(px).hexdigest()[:10]
        # A block whose sprites mix depths is drawn once per depth; after the first, only
        # the sprites of that depth are shown.
        for j, bpp in enumerate(order):
            mine = [s for s in inside if s[0] == bpp]
            rgba, src = draw(vram, raw, bpp, mine, b, cluts)
            if j:
                per = 4 if bpp == 0 else 2 if bpp == 1 else 1
                keep = np.zeros(rgba.shape[:2], bool)
                for s in mine:
                    sx, sy = (s[4] - x) * per, s[5] - y
                    keep[sy:sy + s[7], sx:sx + s[6] * per] = True
                rgba[~keep] = 0
            im = Image.new('RGBA', (rgba.shape[1], rgba.shape[0]), GROUND + (255,))
            im.alpha_composite(Image.fromarray(rgba, 'RGBA'))
            yield label, im.convert('RGB'), dict(block=k, vram=[x, y, w, h], bpp=bpp, palette=src,
                                                 sprites=len(mine), pixels=h1)


def draw(vram, raw, bpp, mine, b, cluts):
    """RGBA for one block at one depth, with each sprite's CLUT over its own area."""
    x, y = b['img'][:2]
    if bpp == 2:
        v = raw
        return np.stack([(v & 31) << 3, ((v >> 5) & 31) << 3, ((v >> 10) & 31) << 3,
                         np.full(v.shape, 255)], 2).astype(np.uint8), 'direct'
    n = 16 if bpp == 0 else 256
    idx = indices(raw, bpp)
    if mine:
        cs = [(s[1], s[2]) for s in mine]
        cx, cy = max(set(cs), key=cs.count); src = 'sprites'
    elif 'clut' in b:
        cx, cy = b['clut'][:2]; src = 'own'
    elif cluts:
        fits = [c for c in cluts if c[2] >= n] or cluts
        cx, cy = fits[0][:2]; src = 'guess'
    else:
        cx = cy = None
    if src == 'own':
        # Read a TIM's own CLUT from the TIM: the shop signs upload theirs to (0, 0) and
        # then the image on top of it.
        own = np.zeros((1, 1024), np.uint16)
        c = np.frombuffer(b['clut'][4], '<u2')[:n]
        own[0, :len(c)] = c
        pal = palette(own, 0, 0, n)
    elif cx is not None:
        pal = palette(vram, cx, cy, n)
    if cx is None or not pal[:, 3].any():
        g = (idx * (255 // (n - 1))).astype(np.uint8)
        return np.stack([g, g, g, np.full(g.shape, 255, np.uint8)], 2), 'grey'
    rgba = pal[idx]
    per = 4 if bpp == 0 else 2
    for s in mine:
        if (s[1], s[2]) == (cx, cy):
            continue
        sx, sy = (s[4] - x) * per, s[5] - y
        sub = idx[sy:sy + s[7], sx:sx + s[6] * per]
        rgba[sy:sy + s[7], sx:sx + s[6] * per] = palette(vram, s[1], s[2], n)[sub]
    return rgba, src


def sources(root):
    a = os.path.join(root, 'A')
    for f in sorted(os.listdir(a)):
        p = os.path.join(a, f)
        ext = f.rsplit('.', 1)[-1].upper()
        b = open(p, 'rb').read()
        if ext == 'TIM':
            yield f, [(None, b)]
        elif ext == 'SPC':
            yield f, [(None, maybe_lzss(b))]
        elif ext == 'J':
            n = struct.unpack_from('<I', b, 0)[0]
            offs = struct.unpack_from(f'<{n + 1}I', b, 4)
            yield f, [(i, maybe_lzss(b[offs[i]:offs[i + 1]])) for i in range(n)]


def main():
    root, out = sys.argv[1:3]
    os.makedirs(out, exist_ok=True)
    index = []
    for f, parts in sources(root):
        for n, (entry, im, info) in enumerate(render_group(parts)):
            stem = f.rsplit('.', 1)[0] + ('' if entry is None else f'_e{entry}')
            name = f'{stem}_{n}.png'
            im.save(os.path.join(out, name))
            index.append(dict(png=name, file=f, entry=entry, size=list(im.size), **info))
    json.dump(index, open(os.path.join(out, 'index.json'), 'w'), indent=0)
    print(f'{len(index)} images from {len({(i["file"], i["entry"]) for i in index})} sources')


if __name__ == '__main__':
    main()
