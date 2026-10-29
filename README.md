# Board Game - Top Shop: English Fix

Board Game - Top Shop has been one of my favorite PlayStation games for a long time. It's
an odd, cheerful little board game about buying up stores in a department store, keeping
their shelves stocked and hoping your rivals do their shopping with you. I have a lot of
fond memories of it, and it has a charm I've never quite found anywhere else.

The English release was always a bit rough, though. Menus and messages read awkwardly,
there were typos here and there, and some of the event cards and point-exchange items
described something other than what actually happens. This patch is my attempt to clean
that up while leaving the game itself alone.

## What's changed

- Menus, shopping, deliveries, buying and selling stores, turn messages and the memory
  card screens all read more naturally.
- The points exchange list now says what each item really does. A few of them were
  wrong in the original ("Next turn" for an effect that lasts until the next payday, for
  one), and those were checked against the game's code.
- Item names got spelling and plural fixes, and a few of the stranger Japanese-English
  terms were made plainer.
- The event cards were rewritten so they're clear about who's affected and how. The
  information desk announcements open with "Attention, shoppers!"
- The rival scenes in Story mode only got light grammar and punctuation fixes. They have
  a lot of Japanese flavor, and I wanted to keep it. Two lines that ran past the edge of
  their box in the original release now fit.
- The March sale is now the "Clearance Sale", picture included.
- A few other pictures were fixed as well: "From Bigining" on the Story mode menu, the
  misspelled job titles in the staff credits, the title screen's small print, and the
  Free Play picture for no computer players, which said "COM なし" in Japanese and now
  says "NO / COM".
- On a computer player's turn, the events with the most to read keep their later text
  boxes up for two seconds instead of one, so you can see what happened.

## What hasn't

The shop names are exactly as they were. Changing them would have meant redrawing the
signs, but that wasn't really the reason. I love the feel of this game, and the shop
names are a big part of what makes it unique, so they stay. That goes for "Fruits Market"
and "Abdominal" too.

A few other things were left as they are on purpose, like "Wining Conditions" on the
setup screen, which is drawn into a graphic where there's no room for the extra letter.
The full list, with the reasons, is in [docs/decisions.md](docs/decisions.md), so nobody
has to wonder whether they were missed.

This is a translation fix, so the game plays exactly as it always has, apart from that
event text timing.

## Applying the patch

You'll need your own copy of the US disc (SLUS-01333) as a single-track BIN/CUE image.
The patch only applies to this exact image:

| | |
|---|---|
| Size | 89,284,272 bytes |
| CRC32 | `e2ca3bf7` |
| MD5 | `e886c77d61880e3ff655af46ac82c323` |

If your copy is a CHD or split some other way, convert it to a single BIN/CUE first.

Apply `topshop-english.xdelta` to the BIN with any xdelta3 patcher. On Windows, Delta
Patcher works fine. From a command line:

```sh
xdelta3 -d -s "Board Game - Top Shop.bin" topshop-english.xdelta "Board Game - Top Shop (English Fix).bin"
```

Then use the included `Board Game - Top Shop (English Fix).cue` with the new BIN. If you
name the BIN something else, change the name inside the CUE to match.

The patched image should come out like this:

| | |
|---|---|
| Size | 89,293,680 bytes |
| CRC32 | `0fffca3a` |
| MD5 | `3128250585b8bc0230b1e1322a64328b` |

I've tested it in an emulator (Beetle PSX) from power-on through a good stretch of play,
and every Story mode scene has been checked on screen. I haven't tried it on real hardware
yet.

## Building it yourself

Everything that produced the patch is in this repository. [docs/building.md](docs/building.md)
covers extracting the disc and building, and `scripts/mkpatch.py` builds the disc and
makes the patch from your original image. The repository doesn't contain the game's
script, only the changed lines.

If you spot a line that still reads wrong, or one I made worse, feel free to open an
issue. I'd be glad to hear about it.
