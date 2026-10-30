# Board Game - Top Shop: English Fix

Board Game - Top Shop has been one of my favorite PlayStation games for a long time. It's
an honest, charming little board game similar to Monopoly, but with a few twists and an anime
art style and plenty of Japanese flair. I have a lot of good memories of this game, and it's
really satisfying for a budget title.

The English release was always a bit rough, though. Menus and messages sometimes read
awkwardly, there were typos here and there, and some of the event cards and point-exchange
items had descriptions which weren't especially accurate. This patch is my attempt to clean
that up while leaving the game itself alone.

## What's changed

- Typos and grammar are fixed throughout: menus, shopping, event cards, the points
  exchange, Story mode and the memory card screens.
- Event cards and points-exchange items whose descriptions weren't accurate now say what
  they actually do, checked against the game's disassembled code.
- A few typos drawn into the pictures were fixed too, like "From Bigining" on the Story
  mode menu and the job titles in the staff credits.
- On a computer player's turn, the wordier events leave their text up a little longer, so
  you can read what happened.

The full list is in [docs/changes.md](docs/changes.md).

## What hasn't changed

I love this game's innocent, very Japanese style, and I tried hard to keep it. If
something wasn't plainly wrong, I left it alone.

The Story mode scenes are almost word for word what they were. They got typo and grammar
fixes and a couple of small rewordings, and two lines that ran past the edge of their box
now fit. The characters are all the
same, and so are the shop names and most of the item names, "Fruits Market" included.
Changing the shop names would have meant redrawing the signs, but that wasn't really the
reason. They're a big part of what makes the game what it is.

A few other things were left as they are on purpose, like "Wining Conditions" on the
setup screen, which is drawn into a graphic where there's no room for the extra letter.
The full list, with the reasons, is in [docs/decisions.md](docs/decisions.md).

Apart from that event text timing, the game plays exactly as it always has.

I personally reviewed and approved every change to the text and graphics, and checked
every event and every Story mode scene on screen. I've tested it in emulators (Beetle PSX
and DuckStation) from power-on through a good stretch of play, but I haven't tried it on
real hardware yet.

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

## How this was made

I made this patch with Claude, Anthropic's AI model, working in Claude Code. Claude did the
reverse engineering, wrote the tools that pull the text out of the game and put it back,
and drafted the rewritten lines. I decided what should change and what should stay, and I
reviewed and approved (or edited) every change to the text and graphics on screen in the
game before it went in. Where a description says what an item or event actually does, that
was checked against the game's code.

This isn't a machine translation. The patch starts from the original English release and
only changes what needed it, with the Japanese release as a reference where the English
was unclear.

The commit history shows the whole process, if you're curious.

## Building it yourself

Everything that produced the patch is in this repository. [docs/building.md](docs/building.md)
covers extracting the disc and building, and `scripts/mkpatch.py` builds the disc and
makes the patch from your original image. The repository doesn't contain the game's
script, only the changed lines.

If you spot a line that still reads wrong, or one I made worse, feel free to open an
issue. I'd be glad to hear about it.
