#!/usr/bin/env python3
"""Capture every pickable event's text boxes on a computer player's turn, and build a page
for choosing how long each event's boxes stay up (docs/engine-notes.md, "Event text timing").

    evtiming.py prep             save a state just before a computer draws an event card
    evtiming.py run N [N...]     capture events N: as built, later-box wait +10 ticks,
                                 first-box wait +10 ticks
    evtiming.py all              prep, run every event ten at a time, then page
    evtiming.py page             rips/review/event-timing.html

prep needs the Story Mode menu state from `storyscenes.py menu`, made on the current
build. It starts stage 1, plays a while with the same button pattern, and saves the state
in rips/review/events/. Each capture then writes the event into every record of the random
table, so the next card a computer draws is that event. The two +10 runs show which boxes
each wait controls; the page scales those differences to whatever values are typed in.
MODES (default "base between first") limits run to some of the three.
"""
import base64, hashlib, io, json, os, re, struct, subprocess, sys
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import storyscenes as S

R = S.R
OUT = R + 'rips/review/events/'
PRE = OUT + 'prepick.state'
TABLE = 0x800adc64                   # 49 nine-byte records, event number first
PICKER = 0x8008cc4c
PLAYERS = 0x80113ce8                 # 0xc0-byte records; +1 nonzero for a computer
SEQ = ['left', 'cross', 'up', 'cross', 'right', 'cross', 'down', 'cross', 'triangle']
REACH = ([24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 40, 41, 42, 43, 44, 45, 46,
          47, 48, 49, 50, 51, 52, 53, 54, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70,
          71, 72, 75, 76] + list(range(80, 89)))
# the waits, ending in the tick count (60 and 30 in the original scripts) and compare type 3
FIRST = re.compile(rb'\x00\x20..\x80\xd3\x00\x10\x00\x06\x00\x20..\x80\xc8\x07\x00\x00\x07'
                   rb'\x00\x10..\x00\x20..\x80\xf0\x00(.)\x00\x03', re.S)
BETWEEN = re.compile(rb'\x00\x21\x80\xf0\x00\x00\x00\x13..\x00\x23\x80\xf0\x00\x01\x00\x20..'
                     rb'\x80\xd3\x00\x10\x00\x06\x00\x20..\x80\xc8\x07\x00\x00\x07\x00\x32'
                     rb'\x00\x01\x00\x14\x00\x20..\x80\xf0\x00(.)\x00\x03', re.S)
DESC = 0x800ab794                    # debug event descriptions, one pointer per event


def cpu_turn(e):
    cur = e.read(0x800b271c, 1)[0]
    return e.read(PLAYERS + 0xc0 * cur + 1, 1)[0] != 0


def prep():
    """Play stage 1 until a computer draws an event card, then save the state from just
    before that, with the press count the button pattern resumes at."""
    e = S.start(1, '/tmp/evtiming_')
    seen, t = [], 0
    while not any(f.startswith('STG') for f in seen) and t < 6000:   # through to the board
        e.press('cross', hold=2, after=58); t += 60; seen += S.loads(e)
    e.run(600)
    os.makedirs(OUT, exist_ok=True)
    board = OUT + 'board.state'
    e.save(board)
    e.bp(PICKER); e.log()
    for k in range(3000):
        e.press(SEQ[k % len(SEQ)], hold=2, after=25)
        if e.log() and cpu_turn(e):
            break
    else:
        sys.exit('no computer drew an event card')
    start = max(0, k - 20)               # a few turns' slack before the draw
    e = S.emu(); e.load(board)
    for i in range(start):
        e.press(SEQ[i % len(SEQ)], hold=2, after=25)
    e.save(PRE)
    json.dump({'press': start}, open(PRE + '.json', 'w'))
    os.remove(board)
    print('prep: a computer draws at press', k, '; saved from', start)


def capture(n, mode):
    """mode: base | between | first. Returns list of boxes {frames, png}."""
    out = f'{OUT}{n:03d}/{mode}/'
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(out + f)
    e = S.emu(); e.load(PRE)
    for r in range(49):
        e.write(TABLE + 9 * r, bytes([n]))
    e.bp(PICKER); e.log()
    i = json.load(open(PRE + '.json'))['press']
    while not e.log():
        e.press(SEQ[i % len(SEQ)], hold=2, after=25); i += 1
        assert i < 3000, 'no pick'
    who = e.read(0x800b271c, 1)[0]
    assert cpu_turn(e), 'not a computer\'s turn'
    # The script's own values. It arrives a sector at a time, so keep looking for a second
    # after the first wait turns up; single-box events have no later-box wait.
    waits, seen_at = {'F': None, 'L': None}, None
    segs, prev, t0, gone = [], None, 0, 0
    for f in range(4000):
        e.run(1)
        if seen_at is None or (waits['L'] is None and f - seen_at < 60):
            ram = e.read(0x80000000, 0x200000)
            for key, pat, m_ in (('F', FIRST, 'first'), ('L', BETWEEN, 'between')):
                ms = list(pat.finditer(ram))
                assert len(ms) <= 1, (key, len(ms))
                if ms and waits[key] is None:
                    waits[key] = ms[0][1][0]
                    if mode == m_:
                        e.write(0x80000000 + ms[0].start(1), bytes([waits[key] + 10]))
            if seen_at is None and waits['F'] is not None:
                seen_at = f
        im = np.asarray(e.image())[S.BOX]
        key = hashlib.md5(im.tobytes()).hexdigest() if S.is_box(im) else None
        if key != prev:
            if prev is not None and f - t0 >= 4:
                segs.append({'start': t0, 'frames': f - t0, 'key': prev})
            prev, t0 = key, f
        if key and f - t0 in (3, 50):
            e.shot(f'{out}tmp_{t0:05d}.png', scale=1)
        if key is None:
            gone += 1
            if segs and gone > 400:
                break
        else:
            gone = 0
        if e.read(0x800b271c, 1)[0] != who:
            break
    assert waits['F'] is not None, 'first-box wait not found in RAM'
    # keep one picture per box, taken a few frames in
    boxes = []
    for k, s in enumerate(segs):
        src = f'{out}tmp_{s["start"]:05d}.png'
        dst = f'{out}box{k:02d}.png'
        if os.path.exists(src):
            os.rename(src, dst)
        boxes.append({'frames': s['frames'], 'png': dst, 'key': s['key'][:8]})
    for f in os.listdir(out):
        if f.startswith('tmp_'):
            os.remove(out + f)
    json.dump({'event': n, 'player': who, 'waits': waits, 'boxes': boxes},
              open(out + 'boxes.json', 'w'), indent=1)
    return boxes


def run(nums):
    for n in nums:
        for mode in os.environ.get('MODES', 'base between first').split():
            try:
                b = capture(n, mode)
                print(n, mode, [x['frames'] for x in b], flush=True)
            except AssertionError as err:
                print(n, mode, 'FAILED', err, flush=True)


def uri(p):
    b = io.BytesIO(); Image.open(p).convert('RGB').save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def names():
    """Event number -> the executable's debug description of it."""
    exe = open(R + 'rips/clean/topshop/SLUS_013.33', 'rb').read()
    at = lambda a: a - 0x80010000 + 0x800
    out = {}
    for n in range(100):
        p = struct.unpack_from('<I', exe, at(DESC + 4 * n))[0]
        out[n] = exe[at(p):exe.index(b'\0', at(p))].decode('cp932') if p else ''
    return out


def page():
    names_ = names()
    events = []
    for n in REACH:
        d, waits = {}, None
        for mode in ('base', 'between', 'first'):
            p = f'{OUT}{n:03d}/{mode}/boxes.json'
            j = json.load(open(p)) if os.path.exists(p) else {}
            d[mode] = j.get('boxes')
            if mode == 'base':
                waits = j.get('waits')
        base = d['base']
        if not base:
            continue
        boxes = []
        for k, b in enumerate(base):
            def sens(mode):
                o = d[mode]
                if not o or len(o) != len(base):
                    return 0
                return max(0, round((o[k]['frames'] - b['frames']) / 20))
            boxes.append({'f': b['frames'], 'sF': sens('first'), 'sL': sens('between'),
                          'img': uri(b['png'])})
        same = all(d[m] and len(d[m]) == len(base) for m in ('between', 'first'))
        events.append({'n': n, 'name': names_.get(n, ''), 'boxes': boxes, 'ok': same,
                       'F0': (waits or {}).get('F') or 60, 'L0': (waits or {}).get('L') or 30})
    html = PAGE.replace('/*DATA*/', json.dumps(events))
    path = R + 'rips/review/event-timing.html'
    open(path, 'w').write(html)
    print(path, os.path.getsize(path), 'bytes,', len(events), 'events')


PAGE = r'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Top Shop: event text timing</title>
<style>
:root{--ink:#222;--mute:#6a6a6a;--line:#d6d2c8;--bg:#f4f2ec;--card:#fffdf8;--acc:#2f4f8a}
*{box-sizing:border-box}
body{font:15px/1.5 Georgia,serif;background:var(--bg);color:var(--ink);margin:0;padding:24px 40px 80px}
h1{font-weight:normal;font-size:26px;margin:0 0 6px}
p.sub{color:#555;max-width:62em;margin:0 0 10px}
.key{font:13px/1.4 system-ui,sans-serif;color:var(--mute);margin-bottom:22px}
.ev{background:var(--card);border:1px solid var(--line);border-radius:6px;padding:16px 18px;margin:0 0 22px;display:grid;grid-template-columns:700px 1fr;gap:18px}
.ev.changed{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}
h2{grid-column:1/3;font-weight:normal;font-size:19px;margin:0}
h2 small{font:13px system-ui,sans-serif;color:var(--mute);margin-left:8px}
.screen{width:700px;height:480px;background:#000;border:1px solid #999;position:relative}
.screen img{width:700px;height:480px;image-rendering:pixelated;display:block}
.screen .clock{position:absolute;right:8px;top:6px;font:12px system-ui,sans-serif;color:#fff;background:rgba(0,0,0,.55);padding:1px 6px;border-radius:3px}
.side{font:14px/1.45 system-ui,sans-serif}
.ctl{display:grid;grid-template-columns:100px 70px auto;justify-content:start;gap:6px 10px;align-items:center;margin-bottom:12px}
.ctl input{width:70px;font:14px system-ui;padding:3px 5px}
.ctl .s{color:var(--mute)}
.ctl .na{color:#aaa}
button{font:14px system-ui;padding:5px 14px;margin-right:6px;cursor:pointer;border:1px solid #999;border-radius:4px;background:#fff}
button.play{background:var(--acc);color:#fff;border-color:var(--acc)}
.thumbs{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}
.thumb{width:140px;cursor:pointer;font:12px system-ui;color:var(--mute);text-align:center}
.thumb img{width:140px;height:96px;image-rendering:pixelated;border:2px solid transparent;display:block}
.thumb.on img{border-color:var(--acc)}
.thumb b{color:var(--ink);font-weight:600}
.warn{color:#9a5b00;font-size:13px;margin-top:8px}
#out{position:sticky;bottom:0;background:#fffdf8;border-top:2px solid var(--acc);margin:0 -40px -80px;padding:10px 40px 14px;font:13px system-ui}
#out textarea{width:100%;height:70px;font:13px ui-monospace,monospace}
#out .bar{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:6px}
#out .bar b{margin-right:auto}
@media (max-width:1000px){
body{padding:12px 12px 40px}
h1{font-size:21px}
.ev{grid-template-columns:1fr;padding:10px;gap:10px}
h2{grid-column:1}
.screen,.screen img{width:100%;height:auto;aspect-ratio:35/24}
.ctl{grid-template-columns:auto 76px auto}
.ctl input,button{font-size:16px}
button{padding:8px 14px}
.thumbs{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.thumb,.thumb img{width:100%}
.thumb img{height:auto;aspect-ratio:35/24}
#out{margin:0 -12px -40px;padding:8px 12px 10px}
#out textarea{display:none;height:90px}
#out.open textarea{display:block}
}
</style></head><body>
<h1>Event text timing on computer players' turns</h1>
<p class="sub">Every event the game can pick, captured in the emulator on a computer player's turn.
Each event script has two waits of its own. The <b>first box</b> stays up for its wait after
any voice clip ends, and <b>every later box</b> for the other. The original scripts use 60
ticks (about 2 seconds) and 30 (about 1 second); each event starts at the values in the
build it was captured from. A tick is 2 frames, 1/30 of a second. On your own turns every
box waits for your button instead, so none of this applies there.</p>
<p class="sub">Change the ticks and press Play to watch the event at that speed. A box marked
"fixed" didn't change length when either wait was raised; something else in the script
times it. The titles come from the game's own debug list and are sometimes a little off
(the sale percentages, for one). Your choices are kept in this browser and listed at the
bottom.</p>
<div class="key">Durations under each thumbnail are at the current settings, in seconds.</div>
<div id="list"></div>
<div id="out"><div class="bar"><b id="count">Changed events</b>
<button onclick="document.getElementById('out').classList.toggle('open')">Show</button>
<button onclick="copy(this)">Copy</button>
<button onclick="if(confirm('Put every event back to its captured values?')){localStorage.removeItem('evtiming');location.reload()}">Reset all</button></div>
<textarea id="summary" readonly></textarea>
</div>
<script>
const EV = /*DATA*/;
const saved = JSON.parse(localStorage.getItem('evtiming') || '{}');
const FPS = 59.94;
function dur(b, F, L, e) { return Math.max(2, b.f + 2 * (F - e.F0) * b.sF + 2 * (L - e.L0) * b.sL); }
function sec(fr) { return (fr / FPS).toFixed(1); }
function summary() {
  const lines = [];
  for (const e of EV) {
    const s = saved[e.n];
    if (s && (s.F != e.F0 || s.L != e.L0)) lines.push(`Event ${e.n}: first box ${s.F}, later boxes ${s.L}`);
  }
  document.getElementById('summary').value = lines.join('\n') || '(nothing changed yet)';
  document.getElementById('count').textContent = `Changed events: ${lines.length}`;
}
// navigator.clipboard only exists on https or localhost, not on the LAN address
function copy(btn) {
  const t = document.getElementById('summary'), v = t.value;
  const done = () => { btn.textContent = 'Copied'; setTimeout(() => btn.textContent = 'Copy', 1500); };
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(v).then(done); return; }
  const shown = getComputedStyle(t).display !== 'none';
  if (!shown) t.style.display = 'block';
  t.focus(); t.select(); t.setSelectionRange(0, v.length);
  document.execCommand('copy'); done();
  if (!shown) t.style.display = '';
}
const list = document.getElementById('list');
for (const e of EV) {
  const s = saved[e.n] || {F: e.F0, L: e.L0};
  const usesF = e.boxes.some(b => b.sF), usesL = e.boxes.some(b => b.sL);
  const div = document.createElement('div');
  div.className = 'ev'; div.id = 'e' + e.n;
  div.innerHTML = `<h2>Event ${e.n}<small>${e.name.replace(/</g,'&lt;')}</small></h2>
    <div class="screen"><img alt=""><span class="clock"></span></div>
    <div class="side">
      <div class="ctl">
        <label>First box</label><input type="number" min="1" max="255" class="F" ${usesF ? '' : 'disabled'}>
        <span class="s sF"></span>
        <label>Later boxes</label><input type="number" min="1" max="255" class="L" ${usesL ? '' : 'disabled'}>
        <span class="s sL"></span>
      </div>
      <button class="play">Play</button><button class="stop">Stop</button><button class="reset">Reset</button>
      <div class="thumbs"></div>
      ${e.ok ? '' : '<div class="warn">The test runs for this event didn\'t line up box for box, so its "fixed" labels may be wrong.</div>'}
    </div>`;
  list.appendChild(div);
  const img = div.querySelector('.screen img'), clock = div.querySelector('.clock');
  const iF = div.querySelector('.F'), iL = div.querySelector('.L');
  iF.value = s.F; iL.value = s.L;
  const th = div.querySelector('.thumbs');
  e.boxes.forEach((b, k) => {
    const t = document.createElement('div'); t.className = 'thumb';
    t.innerHTML = `<img src="${b.img}" alt=""><span></span>`;
    t.onclick = () => { stop(); show(k); };
    th.appendChild(t);
  });
  let timer = null;
  function show(k) {
    img.src = e.boxes[k].img;
    th.querySelectorAll('.thumb').forEach((t, j) => t.classList.toggle('on', j === k));
  }
  function refresh() {
    const F = +iF.value || e.F0, L = +iL.value || e.L0;
    div.querySelector('.sF').textContent = usesF ? `ticks = ${(F / 30).toFixed(1)} s` : 'not used';
    div.querySelector('.sL').textContent = usesL ? `ticks = ${(L / 30).toFixed(1)} s` : 'not used';
    th.querySelectorAll('.thumb span').forEach((sp, k) => {
      const b = e.boxes[k];
      sp.innerHTML = `<b>${sec(dur(b, F, L, e))} s</b>` + (b.sF || b.sL ? '' : ' fixed');
    });
    const total = e.boxes.reduce((a, b) => a + dur(b, F, L, e), 0);
    clock.textContent = `${sec(total)} s in all`;
    saved[e.n] = {F, L};
    if (F == e.F0 && L == e.L0) delete saved[e.n];
    localStorage.setItem('evtiming', JSON.stringify(saved));
    div.classList.toggle('changed', F != e.F0 || L != e.L0);
    summary();
  }
  function stop() { clearTimeout(timer); timer = null; }
  function play(k = 0) {
    stop();
    if (k >= e.boxes.length) { clock.textContent = 'done'; setTimeout(refresh, 1200); return; }
    show(k);
    const ms = dur(e.boxes[k], +iF.value || e.F0, +iL.value || e.L0, e) / FPS * 1000;
    clock.textContent = `box ${k + 1} of ${e.boxes.length}`;
    timer = setTimeout(() => play(k + 1), ms);
  }
  iF.oninput = iL.oninput = refresh;
  div.querySelector('.play').onclick = () => play(0);
  div.querySelector('.stop').onclick = stop;
  div.querySelector('.reset').onclick = () => { iF.value = e.F0; iL.value = e.L0; refresh(); };
  show(0); refresh();
}
summary();
</script></body></html>
'''


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'prep':
        prep()
    elif cmd == 'run':
        run([int(a) for a in sys.argv[2:]])
    elif cmd == 'page':
        page()
    elif cmd == 'all':
        prep()
        groups = [REACH[k::10] for k in range(10)]
        ps = [subprocess.Popen([sys.executable, __file__, 'run'] + [str(n) for n in g]) for g in groups]
        for p in ps:
            p.wait()
        page()
    else:
        sys.exit(__doc__)
