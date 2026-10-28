#!/usr/bin/env python3
"""Build docs/graphics-survey.html, the survey of every graphic on the disc.

    python3 scripts/gfx.py rips/clean/topshop rips/gfx/us
    python3 scripts/mksurvey.py

It reads the renders gfx.py writes to rips/gfx/us, the emulator screenshots in docs/shots
and the month animations straight from the extracted disc, and inlines every picture, so
the page opens with no other files. The text of the page is written out below; change it
here, not in the HTML.
"""
import base64, io, json, os, glob, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gfx

R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..') + '/'
G = R + 'rips/gfx/us/'
SH = R + 'docs/shots/'
DISC = R + 'rips/clean/topshop/A/'
if not os.path.exists(G + 'index.json'):
    sys.exit('No renders in rips/gfx/us; run scripts/gfx.py rips/clean/topshop rips/gfx/us first.')


def load(p):
    return Image.open(p).convert('RGB')


def g(name):
    return load(G + name)


def crop(im, box):
    return im.crop(box)


def up(im, s):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


def sheet(items, cols, pad=6, bg=(250, 249, 245), label=True):
    """items: [(caption, image)] -> labelled grid"""
    w = max(i.width for _, i in items); h = max(i.height for _, i in items) + (14 if label else 0)
    rows = (len(items) + cols - 1) // cols
    S = Image.new('RGB', (cols * (w + pad) - pad, rows * (h + pad) - pad), bg)
    d = ImageDraw.Draw(S)
    for n, (cap, im) in enumerate(items):
        x, y = n % cols * (w + pad), n // cols * (h + pad)
        if label:
            d.text((x + 1, y), cap, fill=(90, 90, 90))
        S.paste(im, (x, y + (14 if label else 0)))
    return S


def uri(im):
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def fig(im, alt, cap, width=None):
    st = f' style="width:{width}px"' if width else ''
    return f'<figure><img src="{uri(im)}" alt="{alt}"{st}><figcaption>{cap}</figcaption></figure>'


def row(*figs):
    return '<div class="row">' + ''.join(figs) + '</div>'


# ---------------------------------------------------------------- images
from_big_art = up(crop(g('SET2_5.png'), (0, 238, 248, 254)), 2)
com_shot = crop(load(SH + 'com_nashi.png'), (60, 120, 640, 440))
com_art = up(crop(g('SET3_0.png'), (0, 0, 64, 200)), 2)
credits_shot = crop(load(SH + 'credits_mainprogramer.png'), (120, 180, 520, 320))
staff1 = up(crop(g('STAFF1_0.png'), (0, 0, 256, 176)), 2)
staff23 = sheet([('STAFF2', g('STAFF2_0.png')), ('STAFF3', crop(g('STAFF3_0.png'), (0, 0, 256, 256)))], 2)
corner = g('CORNER_0.png')
legal = up(crop(corner, (20, 212, 320, 240)), 3)
titles = sheet([(n, up(crop(g(f), b), 2)) for n, f, b in [
    ('SET2_4', 'SET2_4.png', (110, 70, 230, 120)),
    ('SET2_3', 'SET2_3.png', (128, 126, 240, 176)),
    ('SET2_3', 'SET2_3.png', (0, 222, 150, 240)),
    ('SET2_0', 'SET2_0.png', (0, 0, 208, 16)),
    ('SET2_1', 'SET2_1.png', (0, 0, 192, 16)),
    ('SET2_2', 'SET2_2.png', (0, 0, 160, 16))]], 2)
publisher = sheet([('OPEN2', up(crop(g('OPEN2_3.png'), (0, 0, 150, 16)), 2)),
                   ('TIT_A', up(crop(g('TIT_A_0.png'), (88, 209, 242, 224)), 2))], 1)

wining = up(g('SET2_4.png'), 2)
ev84 = g('EVE_084_e2_0.png') if os.path.exists(G + 'EVE_084_e2_0.png') else None


def find(prefix, size=None):
    ix = json.load(open(G + 'index.json'))
    return [i['png'] for i in ix if i['png'].startswith(prefix) and (size is None or tuple(i['size']) == size)]


ev_pics = sorted(p for p in find('EVE_') if load(G + p).size in ((192, 128), (256, 176)))
ev84_png = [p for p in ev_pics if p.startswith('EVE_084')][0]
ev87_png = [p for p in ev_pics if p.startswith('EVE_087')][0]
ev76_png = [p for p in ev_pics if p.startswith('EVE_076')][0]

ending = sheet([('ENDING_0', g('ENDING_0.png')), ('ENDING_1', g('ENDING_1.png'))], 2)
result_shot = load(SH + 'freeplay_result.png').resize((320, 240), Image.LANCZOS)
kana = up(crop(g('SET2_5.png'), (0, 0, 248, 194)), 2)
sho4 = sheet([(f'SHO4L4_{n}', up(g(f'SHO4L4_{n}_0.png'), 2)) for n in (1, 2)], 2)
tw_logo = g('OPEN4_0.png')
staff0 = sheet([('STAFF0_0', g('STAFF0_0.png')), ('STAFF0_1', g('STAFF0_1.png'))], 2)
tv = up(crop(g('C_BG07_0.png'), (60, 0, 260, 130)), 2)

boot = sheet([(n, g(f)) for n, f in [('A1.TIM', 'A1_0.png'), ('KID_320.TIM', 'KID_320_0.png'),
                                     ('CORNER.TIM (title)', 'CORNER_0.png'), ('TIT_A.TIM', 'TIT_A_0.png'),
                                     ('WAIWAI.TIM', 'WAIWAI_0.png'), ('LOAD_256.SPC', 'LOAD_256_0.png')]], 3)
open2 = sheet([('OPEN2_0', g('OPEN2_0.png')), ('OPEN2_1', g('OPEN2_1.png')), ('OPEN2_3', g('OPEN2_3.png'))], 3)
menus = [('SET2_4', up(g('SET2_4.png'), 2)), ('SET2_3', up(g('SET2_3.png'), 2)), ('SET2_5', up(g('SET2_5.png'), 2))]
set1 = sheet([(n, up(g(f), 2)) for n, f in [('SET1_0', 'SET1_0.png'), ('SET1_1', 'SET1_1.png'), ('SET1_3', 'SET1_3.png'),
                                           ('SET2_0', 'SET2_0.png'), ('SET2_1', 'SET2_1.png'), ('SET2_2', 'SET2_2.png')]], 3)
set3 = sheet([('SET3_0', g('SET3_0.png')), ('SET3_1', g('SET3_1.png')), ('SET3_2', g('SET3_2.png'))], 3)
hud = sheet([('ETC2_2', up(g('ETC2_2.png'), 2)), ('ETC2_3', up(g('ETC2_3.png'), 2))], 2)
hud_small = sheet([('ETC2_0', up(g('ETC2_0.png'), 2)), ('ETC2_1', up(g('ETC2_1.png'), 2))], 1)
ranks = sheet([(f'R_{n:02d}', up(g(f'R_{n:02d}_0.png'), 2)) for n in range(1, 21)] + [('SET1_2', up(g('SET1_2.png'), 1))], 11)
cards = sheet([(p[:5], g(p)) for p in sorted(find('C_0'))], 10)
evs1 = sheet([(p[:7], g(p).resize((192, 128)) if g(p).size != (192, 128) else g(p)) for p in ev_pics[:48]], 6)
evs2 = sheet([(p[:7], g(p).resize((192, 128)) if g(p).size != (192, 128) else g(p)) for p in ev_pics[48:]], 6)
bgcm = sheet([(p[:6], g(p).resize((160, 120))) for p in find('BGCM')], 7)
cal = sheet([(f'CAL_{n}_{i:02d}', up(gfx.frames(open(DISC + f'CAL_{n}.J', 'rb').read())[i], 2))
             for n, i in (('01', 3), ('10', 5), ('11', 5), ('12', 1))], 4)
cbg = sheet([(n, g(f)) for n, f in [('C_BG00', 'C_BG00_0.png'), ('C_BG02', 'C_BG02_0.png'), ('C_BG07', 'C_BG07_0.png')]], 3)
story_misc = sheet([('SUCCESS.TIM', g('SUCCESS_0.png')), ('END_BG.TIM', g('END_BG_0.png')),
                    ('S00_EXC1 (attract mode)', crop(g('S00_EXC1_0.png'), (0, 0, 256, 160)))], 3)
staff_all = sheet([('STAFF1', g('STAFF1_0.png')), ('STAFF2', g('STAFF2_0.png')), ('STAFF3', g('STAFF3_0.png'))], 3)
boards = sheet([(f, g(f)) for f in ['SB00_00_1.png', 'SB01_00_1.png', 'SB02_00_0.png', 'SB03_00_1.png', 'SB04_00_0.png',
                                     'SB05_00_1.png', 'SB06_00_0.png', 'SB07_00_1.png', 'SB08_00_1.png', 'SB09_00_1.png']], 5)
signs = sheet([(p[:8], g(p)) for p in sorted(glob.glob(G + 'SH*L4_*_0.png')) for p in [os.path.basename(p)] if not p.startswith('SHO')], 12)

# ---------------------------------------------------------------- page
CSS = '''
:root{--ink:#222;--muted:#666;--rule:#ddd;--accent:#b03a2e;--bg:#fbfaf7}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 Georgia,"Iowan Old Style",serif}
main{max-width:1040px;margin:0 auto;padding:40px 28px 80px}
h1{font-size:30px;margin:0 0 4px} .sub{color:var(--muted);margin:0 0 28px}
h2{font-size:21px;margin:48px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--rule)}
h3{font-size:17px;margin:28px 0 6px}
p,li{max-width:74ch}
figure{margin:14px 0 22px} figure img{image-rendering:pixelated;max-width:100%;border:1px solid var(--rule);background:#111}
figcaption{font:13px/1.4 system-ui,sans-serif;color:var(--muted);margin-top:6px;max-width:80ch}
.row{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}
.tag{display:inline-block;font:600 11px system-ui,sans-serif;letter-spacing:.04em;text-transform:uppercase;padding:2px 7px;border-radius:3px;white-space:nowrap}
.fix{background:#f6d8d4;color:var(--accent)} .ok{background:#dcebd9;color:#2d6a2a} .note{background:#e6e3f3;color:#4a3f8a} .new{background:#fff0c2;color:#7a5a00}
table{border-collapse:collapse;font:14px/1.4 system-ui,sans-serif;margin:10px 0}
td,th{border-bottom:1px solid var(--rule);padding:6px 10px;text-align:left;vertical-align:top} th{color:var(--muted);font-weight:600}
code{font:13px ui-monospace,Menlo,monospace;background:#efece6;padding:1px 4px;border-radius:3px}
'''

H = []
a = H.append
a('<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8"><title>Top Shop: graphics survey</title>')
a(f'<style>{CSS}</style></head><body><main>')
a('<h1>Top Shop: graphics survey</h1>')
a('<p class="sub">Board Game – Top Shop (SLUS-01333) compared with Tenant Wars (SLPS-01243). '
  'First surveyed 2026-10-26; redone 2026-10-27 with every image on the disc decoded. '
  'What was left alone and why is in docs/decisions.md.</p>')

a('<h2>How this was done</h2>')
a('<p>The first version of this page only showed the menu graphics that happened to be in video RAM in my save states, '
  'so it missed the main menu, the CPU picture, the credits and the title screen\'s small print. '
  'This time <code>scripts/gfx.py</code> renders every image on the disc: 1,243 of them from 939 files, '
  'including the compressed sprite sheets (<code>.SPC</code>) the first pass couldn\'t read, each drawn with the palettes its own sprite table asks for. '
  'I looked at every one, compared each with the Japanese release, and checked the doubtful ones on screen in the emulator.</p>')

a('<h2>Summary</h2>')
a('<table><tr><th>Where</th><th>What</th><th>On screen?</th><th>Status</th></tr>')
rows = [
    ('Story Mode start menu', '“From Bigining”, now “From Beginning”', 'Yes', '<span class="tag ok">redrawn</span>'),
    ('Free Play, number of players', 'The picture for 0 CPUs says “COM なし” (Japanese for “no COM”)', 'Yes', '<span class="tag new">needs a decision</span>'),
    ('Staff credits', 'Job titles: ASSISTANCEPLANNER, MAINPROGRAMER, PROGRAMER, MAINDESINGER, DESINGER, SUPERVISER, EXECTIVEPRODUCER', 'Yes, after the story', '<span class="tag new">needs a decision</span>'),
    ('Title screen', 'Small print: “TOP SHOP and the and TOP SHOP logo are trademarks…”', 'Yes, every boot', '<span class="tag new">needs a decision</span>'),
    ('Story chapter titles', 'Mixed capitals: “Middle of the ocean”, “Big brother” beside “Frog Prince”, “Magic Man”', 'Yes', '<span class="tag note">optional</span>'),
    ('Opening, publisher line', '“Published by Agetec,Inc.” has no space after the comma', 'Yes', '<span class="tag note">optional</span>'),
    ('Free Play setup menu', '“Wining Conditions”, “Totalmoney”', 'Yes', '<span class="tag ok">left as is</span>'),
    ('Event 84 picture', '“Final sale” art, text now says “Clearance Sale”', 'Yes', '<span class="tag ok">art redrawn</span>'),
    ('Event 87 picture', 'Art says “AUTUMN SALE”, text says “Fall Sale”', 'Yes', '<span class="tag ok">left as is</span>'),
    ('Event 76 card and picture', '“Miss” over the art, “Nothing happens.” in the box', 'Yes', '<span class="tag ok">left as is</span>'),
    ('TV studio backdrop', 'Romanized Japanese jokes: “ONAKASUITAYOOOH”, “NEMUIYOH”, “SUGOROKU”', 'Yes', '<span class="tag ok">kept, it\'s flavour</span>'),
    ('Results sheet', '順位発表 (“ranking announcement”) left in the art', 'No, the screen uses “RESULT”', '<span class="tag ok">unused</span>'),
    ('Name entry sheet', 'Hiragana and katakana with their mode buttons', 'No, US name entry is A–Z only', '<span class="tag ok">unused</span>'),
    ('SHO4L4 shop picture', 'An early burger shop with イチ…バーガー on the sign', 'No, not in the file table', '<span class="tag ok">unused</span>'),
    ('Credits, STAFF0', 'Staff names in kanji', 'No, the credits use the romanized names', '<span class="tag ok">unused</span>'),
    ('Boot, cut events, quizzes', 'Tenant Wars logo; Japanese in events 4–7, 20–23, 55–57, 73, 77; BG_M01', 'No', '<span class="tag ok">unused</span>'),
]
for r in rows:
    a('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>')
a('</table>')

a('<h2>Needs a decision</h2>')
a('<h3>“From Bigining” on the Story Mode start menu</h3>')
a('<p>Once a stage has been cleared, choosing Story Mode offers “From Bigining” or “From Stage N”. Every player who comes back to the story sees it. '
  'The words are drawn into the main menu sheet (<code>SET2.SPC</code>), next to “Continue” and “Off”, with room to spare on the line.</p>')
a('<p><span class="tag ok">redrawn</span> It now says “From Beginning”, put together from letters in the same sheet, with the sprite widened from 80 to 96 pixels (docs/decisions.md).</p>')
a(fig(load(SH + 'from_beginning_before_after.png'), 'From Beginning before and after', 'Before and after in the emulator, with the cursor on each line (2×).'))
a(fig(from_big_art, 'From Bigining in the art', 'The original in the menu sheet (2×).'))
a('<h3>“COM なし” for zero CPU players</h3>')
a('<p>In Free Play, with two or more people playing, the CPU count list shows a little picture for each choice. '
  'The one for CPU 0 still says COM なし, untouched from the Japanese release; the US release left the whole sheet (<code>SET3.SPC</code>) as it was. '
  'The other pictures only say “COM”, which reads fine, though the menu beside them says “CPU”.</p>')
a(row(fig(com_shot, 'COM nashi on screen', 'On screen with CPU 0 highlighted (2×).'),
      fig(com_art, 'CPU pictures', 'The CPU pictures in the sheet (2×).')))
a('<h3>Job titles in the staff credits</h3>')
a('<p>The credits roll after the last story stage. The job titles are one image (<code>STAFF1.SPC</code>), and most of them are misspelled or run together: '
  'ASSISTANCEPLANNER, MAINPROGRAMER, PROGRAMER, MAINDESINGER, DESINGER (twice), SUPERVISER, EXECTIVEPRODUCER. '
  'The titles are plain capitals on black, which would be easy to redraw in the same style.</p>')
a(row(fig(credits_shot, 'Credits on screen', 'On screen at the end of the story (2×).'),
      fig(staff1, 'Credit titles', 'The job titles (2×).')))
a('<p>The names are in lower case and use Kunrei-style spellings (simada, kadomatu, natuko, katuya), which are real romanizations, not mistakes. '
  '“hisakaz ogurau” looks like it may have lost or gained a letter, but these are people\'s names and I can\'t check them, so I\'d leave the names alone.</p>')
a(fig(staff23, 'Credit names', 'The names (1×).'))
a('<h3>The title screen\'s small print</h3>')
a('<p>The title picture (<code>CORNER.TIM</code>) is on screen at every boot, and its trademark line says “TOP SHOP and the and TOP SHOP logo are trademarks of Agetec,Inc.” '
  'The type is tiny, two lines of about 5-pixel text, so redrawing it means matching that font by hand.</p>')
a(fig(legal, 'Title small print', 'The bottom of the title picture (3×).'))

a('<h2>Optional</h2>')
a('<h3>Story chapter titles</h3>')
a('<p>Each story stage opens with a title card. Their capitals are mixed: “Cactus Boy”, “Magic Man”, “Frog Prince”, “Become a Fan!” and “I am Samurai Man” beside '
  '“Flabby thing”, “Big brother”, “Little kid” and “Middle of the ocean”. They read fine either way.</p>')
a(fig(titles, 'Chapter titles', 'All ten chapter titles, from the menu sheets (2×).'))
a('<h3>“Published by Agetec,Inc.”</h3>')
a('<p>The opening\'s publisher line has no space after the comma, and neither does the title screen\'s small print. Barely noticeable.</p>')
a(fig(publisher, 'Publisher line', 'The opening line (2×) and the same words on TIT_A, the α logo picture (3×).'))

a('<h2>Already decided</h2>')
a('<p>These were on the first version of this page, and the reasons are in docs/decisions.md.</p>')
a(fig(wining, 'Setup menu sheet', 'The Free Play setup sheet (<code>SET2.SPC</code>, 2×), now in its real colours: “Wining Conditions” and “Totalmoney”.'))
a(row(fig(g(ev84_png), 'Event 84', 'Event 84 as originally drawn. The patch redraws it as “Clearance / Sale”.'),
      fig(g(ev87_png), 'Event 87', 'Event 87, “AUTUMN SALE”; the text says “Fall Sale.”'),
      fig(g(ev76_png), 'Event 76', 'Event 76, “Miss”; the text says “Nothing happens.”')))

a('<h2>Japanese and leftovers the player doesn\'t see</h2>')
a('<p>Checked one by one. Each of these is in the US disc but never reaches the screen, so they stay.</p>')
a('<h3>順位発表 on the results sheet</h3>')
a('<p>The US release replaced every other label on this sheet (“RESULT” for 結果発表, “1st” for 優勝, “Last” for びり) but left 順位発表. '
  'I played a Free Play game to its end in the emulator and stepped through the whole results sequence: it shows “RESULT”, then the ranks and the WINNER banner, and never 順位発表.</p>')
a(row(fig(ending, 'Results sheets', 'The results sheets (<code>ENDING.SPC</code>).'),
      fig(result_shot, 'RESULT on screen', 'The results screen as it appears.')))
a('<h3>Kana for name entry</h3>')
a('<p>The main menu sheet also holds the Japanese name-entry characters and their mode buttons (英数字, カタカナ, ひらがな). The US Enter Name screen offers A–Z, a–z, digits and a few symbols, and has no mode switch.</p>')
a(fig(kana, 'Kana sheet', 'The top of the sheet (2×).'))
a('<h3>The SHO4L4 shop picture</h3>')
a('<p>Four files named SHO4L4 (with a letter O), dated January 1999, show an early burger shop with Japanese on the sign. '
  'The game finds its files through a table in the executable, and no entry points at them. The real one is SH04L4, the Burger Shop.</p>')
a(fig(sho4, 'SHO4L4', 'SHO4L4_1 and _2 (2×).'))
a('<h3>Kanji staff names, the Tenant Wars logo</h3>')
a(row(fig(staff0, 'Kanji names', 'STAFF0: the staff in kanji. The US credits show the romanized names instead.'),
      fig(tw_logo, 'Tenant Wars logo', 'OPEN4: the テナントウォーズ logo, loaded at boot but not shown.')))
a('<p>The cut events (4–7, 20–23, 55–57), both quiz pictures (73, 77) and BG_M01 are as described on the first version of this page; they\'re in the event sheets below.</p>')
a('<h3>Romanized jokes in the TV studio</h3>')
a('<p>This one is seen. The TV studio backdrop in the story scenes has signs saying ONAKASUITAYOOOH (“I\'m so hungry”), NEMUIYOH (“I\'m sleepy”) and SUGOROKU (the board game). '
  'They\'re in Latin letters, and they\'re the kind of Japanese flavour the story scenes keep.</p>')
a(fig(tv, 'TV studio', 'C_BG07, the top of the backdrop (2×).'))

a('<h2>Every graphic with text</h2>')
a('<p>For reference and later review: every image on the disc with words in it, by where it appears. Rendered from the disc, not from the screen, so a few sheets hold pieces that are put together in play.</p>')
a('<h3>Boot, title and loading</h3>')
a(fig(boot, 'Boot pictures', 'Full-screen pictures. A1, KID and the title are seen at boot; TIT_A and WAIWAI KID weren\'t seen in my runs.'))
a(fig(open2, 'Opening sprites', 'Opening sprites: “A1 Games”, “PRESS START BUTTON”, the publisher line, the copyright and the disclaimer.'))
a('<h3>Menus</h3>')
for n, im in menus:
    a(fig(im, n, f'<code>{n.split("_")[0]}.SPC</code> sheet {n.split("_")[1]} (2×).'))
a(fig(set1, 'Small menu sprites', 'Rank badges and three chapter titles (2×).'))
a(fig(set3, 'Player and CPU pictures', 'SET3: the player and CPU count pictures, the memory card picture and the Story Mode pictures.'))
a('<h3>In play</h3>')
a(fig(hud, 'HUD sheets', 'The in-play HUD sheets (ETC2.SPC, 2×).'))
a(fig(hud_small, 'HUD numbers', 'Numbers and rank badges (2×).'))
a(fig(ranks, 'Ranks', 'Ranking badges R_01–R_20 (2×) and the board ranks sheet.'))
a('<h3>Event cards</h3>')
a(fig(cards, 'Event cards', 'C_000–C_099.'))
a('<h3>Event pictures</h3>')
a(fig(evs1, 'Events part 1', 'Event pictures, first half.'))
a(fig(evs2, 'Events part 2', 'Event pictures, second half. Event 84 is shown as on the original disc.'))
a('<h3>Months</h3>')
a(fig(bgcm, 'Month title cards', 'Month title cards BGCM01–13.'))
a(fig(cal, 'Month animations', 'Frames from the month animations (CAL), put together from their frame tables (2×): “JANUARY”, a wolf\'s “AOHOOON” in October, “November” and “December” banners.'))
a('<h3>Story mode</h3>')
a(fig(cbg, 'Story backdrops', 'Story scene backdrops with lettering: Cafe signs, “Kid\'s theater”, the TV studio. C_BG10–19 are copies of C_BG00–09.'))
a(fig(story_misc, 'Story misc', 'SUCCESS after a cleared stage, the End card, and the DEMO sprite from attract mode.'))
a('<h3>Results and credits</h3>')
a(fig(ending, 'Results', 'Results sheets.'))
a(fig(staff_all, 'Credits', 'Credits: titles and names.'))
a('<h3>Boards</h3>')
a(fig(boards, 'Board tiles', 'Board tile sheets with the bank sign, one per board. The board tiles have no other words. Parts of some sheets use other palettes, so their colours are off here.'))
a('<h3>Shop pictures</h3>')
a(fig(signs, 'Shop pictures', 'The level 4 picture of each shop, SH00–SH43. Shop names stay as they are (docs/decisions.md). Levels 1–3 use the same names.'))

a('<h2>No text</h2>')
a('<ul><li>Character sprites (SET0CHR, E_CHR, CHR*), faces (KAO), the rival portraits in the story scenes (CNT) and the opening\'s cat (OPEN5).</li>'
  '<li>Effects (SF), the board tiles other than the bank signs, and the story backdrops not shown above.</li>'
  '<li>HYO_BG and M256_BG (backgrounds), and 0–3.TIM, which are just the digits 0–3.</li></ul>')
a('<h2>Limits</h2>')
a('<ul><li>Sheets are drawn with each sprite\'s palette where the file has a sprite table. Without one, the renderer uses the file\'s first palette, so some board tiles and face sheets show the wrong colours. None of those have text.</li>'
  '<li>The month animations, event pictures and story portraits are cut into 16-pixel tiles and put together by frame tables. I put the month frames together; the rival portraits only partly, which was enough to see they have no words.</li></ul>')
a('</main></body></html>')
open(R + 'docs/graphics-survey.html', 'w').write('\n'.join(H))
print(os.path.getsize(R + 'docs/graphics-survey.html'), 'bytes')
