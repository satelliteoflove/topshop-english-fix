#!/usr/bin/env python3
"""Capture every Story Mode scene in the emulator and put them on one page.

    storyscenes.py menu          boot to the Story Mode menu and save a state there
    storyscenes.py open N [N…]   stage N's title card, Start Game screen and opening scene
    storyscenes.py win N [N…]    force a win of stage N and capture the exchange after it
    storyscenes.py page          rips/review/story-openings.html from whatever was captured
    storyscenes.py all           all of the above, ten stages at a time

Stage N opens with CNT0(N-1) and closes with CNT1(N-1). The scenes need a memory card
whose story record lets "From Stage" reach stage 10; set CARD (default: DuckStation's
topshop-en_1.mcd) and CUE (default: rips/iso/topshop-en.cue). Make a new menu state after
every build, since a state keeps the executable and file table it was made on.

A box is kept once its inside has stayed the same for 10 frames, and only then is ✕
pressed, so no line is skipped; lines also advance on their own after a while. Wins are
forced by holding player 1's money above the target while pressing through turns.
Everything goes to rips/review/story/.
"""
import base64, ctypes as C, glob, io, os, struct, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emu import Emu
import build

R = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')) + '/'
OUT = R + 'rips/review/story/'
CUE = os.environ.get('CUE', R + 'rips/iso/topshop-en.cue')
CARD = os.environ.get('CARD', os.path.expanduser('~/.local/share/duckstation/memcards/topshop-en_1.mcd'))
MENU = OUT + 'menu.state'
LOADERS = (0x8001c958, 0x8001cb5c)      # queue a file by its index (docs/engine-notes.md)
MONEY = 0x80113ce8 + 0x68               # player 1's money
BOX = (slice(171, 220), slice(36, 312))  # inside of the dialogue box, 350x240 frame
RIVALS = ['Maiko', 'Merlin', 'Patty', 'Dona', 'Gummi', 'Bro', 'Oilow', 'Chat', 'Squosh', 'Santa']


def file_names():
    """File table index -> name, from the original disc's layout."""
    lba_name = {lba: n for n, (lba, _) in
                build.layout(open(os.path.join(build.CLEAN, 'topshop.xml')).read(), {})[1].items()}
    exe = open(os.path.join(build.DISC, build.EXE_NAME), 'rb').read()
    bcd = lambda v: (v >> 4) * 10 + (v & 15)
    names = {}
    for i in range(930):
        e = exe[build.LBA_TABLE - build.EXE_BASE + 4 * i:][:3]
        names[i] = lba_name.get(bcd(e[0]) * 4500 + bcd(e[1]) * 75 + bcd(e[2]) - 150)
    return names


NAMES = file_names()


def emu():
    e = Emu(CUE)
    card = open(CARD, 'rb').read()
    C.memmove(e.lib.retro_get_memory_data(0), card, len(card))
    return e


def loads(e):
    """Files queued since the last call."""
    return [NAMES.get(x['regs'][4], x['regs'][4]) for x in e.log() if x['type'] == 'X']


def menu():
    e = emu()
    e.run(3000)
    e.press('start', after=60)
    e.run(540)
    e.press('down', hold=2, after=40)    # Story Mode
    e.press('cross', after=150)          # cursor on From Stage 10
    os.makedirs(OUT, exist_ok=True)
    e.save(MENU)
    e.shot(OUT + 'menu.png', scale=1)


def start(n, out):
    """Load the menu state and pick stage n; returns the emulator at the title card."""
    e = emu(); e.load(MENU)
    for pc in LOADERS:
        e.bp(pc)
    e.log()
    if n == 1:
        e.press('up', hold=2, after=30)  # From Beginning
    else:
        for _ in range(10 - n):
            e.press('left', hold=2, after=12)
    e.press('cross', hold=2, after=120)
    e.shot(out + 'card.png', scale=1)
    e.press('cross', hold=2, after=90)
    e.shot(out + 'setup.png', scale=1)
    return e


def boxes(e, out, until):
    """Save each new dialogue box until until(files loaded so far) is true; returns the count."""
    seen, prev, last, k, idle, t = [], None, None, 0, 0, 0
    while t < 9000:
        e.run(10); t += 10
        seen += loads(e)
        if until(seen):
            break
        im = np.asarray(e.image())[BOX]
        stable = prev is not None and np.array_equal(im, prev)
        prev = im
        if not stable or im.mean() <= 20:   # moving, or no box on screen
            idle = 0; continue
        if last is None or not np.array_equal(im, last):
            e.shot(f'{out}f{k:03d}.png', scale=1); k += 1; last = im
            e.run(20); t += 20
            e.press('cross', hold=2, after=0); idle = 0
        else:
            idle += 10
            if idle >= 60:
                e.press('cross', hold=2, after=0); idle = 0
    return k


def clear(out):
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(out + '*.png'):
        os.remove(f)


def opening(n):
    out = f'{OUT}open{n:02d}/'; clear(out)
    e = start(n, out)
    want, t = f'CNT{n - 1:02d}.J', 0
    seen = []
    while want not in seen and t < 3000:     # ✕ through the Start Game screen and loading
        e.press('cross', hold=2, after=58); t += 60
        seen += loads(e)
    k = boxes(e, out, lambda s: any(f.startswith('STG') for f in s))
    print(f'stage {n}: {want}, {k} boxes')


def win(n):
    out = f'{OUT}win{n:02d}/'; clear(out)
    e = start(n, out)
    want = f'CNT{n + 9:02d}.J'
    # △ backs out of the map view the directions can land in
    seq = ['left', 'cross', 'up', 'cross', 'right', 'cross', 'down', 'cross', 'triangle']
    seen, i = [], 0
    while want not in seen and i < 2500:
        e.write(MONEY, struct.pack('<i', 60000))
        e.press(seq[i % len(seq)], hold=2, after=25); i += 1
        seen += loads(e)
    if want not in seen:
        e.shot(out + 'stuck.png', scale=1)
        print(f'stage {n}: never reached {want}; see {out}stuck.png'); return
    t = [0]

    def done(s):
        t[0] += 10
        return bool(s) and t[0] > 600        # anything loaded after the scene has begun
    k = boxes(e, out, done)
    print(f'stage {n}: {want}, {k} boxes')


def uri(p):
    b = io.BytesIO(); Image.open(p).convert('RGB').save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def page():
    def fig(p, cap):
        return f'<figure><img src="{uri(p)}" alt=""><figcaption>{cap}</figcaption></figure>'
    h = ['''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Top Shop: Story Mode scenes</title><style>
body{font:15px/1.5 Georgia,serif;background:#f4f2ec;color:#222;margin:0;padding:24px 40px}
h1{font-weight:normal;font-size:26px;margin:0 0 4px}p.sub{color:#666;margin:0 0 20px;max-width:60em}
nav a{margin-right:12px;color:#335}
h2{font-weight:normal;font-size:20px;border-bottom:1px solid #ccc;padding-bottom:4px;margin-top:40px}
h3{font-weight:normal;color:#555}
.g{display:flex;flex-wrap:wrap;gap:14px}
figure{margin:0;width:700px}img{width:700px;image-rendering:pixelated;display:block;border:1px solid #bbb}
figcaption{font-size:13px;color:#666}
</style></head><body>
<h1>Story Mode: each stage's opening and win</h1>
<p class="sub">Captured in the emulator by scripts/storyscenes.py. For every stage: the title
card, the Start Game screen, every distinct dialogue box of the opening scene (CNT00 for
stage 1 through CNT09 for stage 10), then the exchange after winning it (CNT10 through
CNT19; the win is forced by holding player 1's money above the target). Native resolution
350×240, shown at 2×.</p><nav>''']
    h.append(' '.join(f'<a href="#s{n}">Stage {n}</a>' for n in range(1, 11)) + '</nav>')
    for n in range(1, 11):
        o, w = f'{OUT}open{n:02d}/', f'{OUT}win{n:02d}/'
        h.append(f'<h2 id="s{n}">Stage {n}: {RIVALS[n - 1]} (CNT{n - 1:02d})</h2><div class="g">')
        for f, cap in (('card', 'Title card'), ('setup', 'Start Game screen')):
            if os.path.exists(o + f + '.png'):
                h.append(fig(o + f + '.png', cap))
        h += [fig(f, f'Box {k + 1}') for k, f in enumerate(sorted(glob.glob(o + 'f*.png')))]
        h.append(f'</div><h3>Stage {n}: after the win (CNT{n + 9:02d})</h3><div class="g">')
        h += [fig(f, f'Box {k + 1}') for k, f in enumerate(sorted(glob.glob(w + 'f*.png')))]
        h.append('</div>')
    h.append('</body></html>')
    path = R + 'rips/review/story-openings.html'
    open(path, 'w').write('\n'.join(h))
    print(path, os.path.getsize(path), 'bytes')


def main(args):
    if not args:
        sys.exit(__doc__)
    cmd, nums = args[0], [int(a) for a in args[1:]]
    if cmd == 'menu':
        menu()
    elif cmd in ('open', 'win'):
        for n in nums:
            (opening if cmd == 'open' else win)(n)
    elif cmd == 'page':
        page()
    elif cmd == 'all':
        menu()
        me = os.path.abspath(__file__)
        for c in ('open', 'win'):
            ps = [subprocess.Popen([sys.executable, me, c, str(n)]) for n in range(1, 11)]
            if any(p.wait() for p in ps):
                sys.exit(f'{c}: a stage failed')
        page()
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
