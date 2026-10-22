#!/usr/bin/env python3
"""Tile screenshots into one image: sheet.py OUT.png IN.png ... [--cols N]"""
import sys
from PIL import Image, ImageDraw
args = sys.argv[1:]; cols = 4
if '--cols' in args:
    k = args.index('--cols'); cols = int(args[k + 1]); del args[k:k + 2]
out, ins = args[0], args[1:]
ims = [Image.open(p).convert('RGB') for p in ins]
w = max(i.width for i in ims); h = max(i.height for i in ims) + 12
rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (w * cols, h * rows), (40, 40, 40)); d = ImageDraw.Draw(S)
for n, (p, i) in enumerate(zip(ins, ims)):
    x, y = n % cols * w, n // cols * h
    S.paste(i, (x, y + 12)); d.text((x + 2, y), p.split('/')[-1], fill=(255, 255, 0))
S.save(out)
