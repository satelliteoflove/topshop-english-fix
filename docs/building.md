# Building

You need Linux, Python 3 with Pillow (and numpy and capstone for some research scripts),
and [mkpsxiso](https://github.com/Lameguy64/mkpsxiso) (which includes dumpsxiso). It's
for the US disc, SLUS-01333, as a single-track bin whose md5 is
`e886c77d61880e3ff655af46ac82c323`.

Extract it once:

```sh
dumpsxiso -l -x rips/clean/topshop -s rips/clean/topshop.xml "Board Game - Top Shop.cue"
python3 scripts/dumptext.py     # all the game's text, into rips/text/
```

Then build:

```sh
python3 scripts/build.py        # rips/iso/topshop-en.bin and .cue
```

With no edits the build gives back the original disc byte for byte (same md5), which is a
quick check that the tooling is sound. Set `MKPSXISO` if it isn't at `~/tools/mkpsxiso`.

## Editing text

`rips/text/SOURCE.json` has every string with its id. To change one, add an entry to
`translations/SOURCE.json`:

```json
[{"id": "CNT00:02d2", "text": "【%NMY】%KYou're just a kid!", "src": "…"}]
```

`src` is the first 8 hex digits of the sha1 of the original text (`build.src_hash`), so
the repo never has to quote the game's script; the build refuses an edit whose original
doesn't match. How each kind of string goes back in is described at the top of
`scripts/build.py`.

## Testing

`scripts/emu.py` is the headless Beetle PSX harness from the Dimguil project (see
`docs/building.md` there for setting up the core). `scripts/play.py STATE PREFIX STEPS…`
runs buttons and screenshots each step (set `CUE` to test a built disc), and
`scripts/sheet.py` tiles screenshots into one image. Save states keep the executable they
were made on, so make fresh ones after a build that changes it.

`scripts/storyscenes.py all` plays every Story Mode stage's opening scene and the exchange
after winning it, saving each dialogue box, and puts them all on
`rips/review/story-openings.html`. It needs a memory card that can start from stage 10
(the `CARD` variable); the other commands, at its top, redo a single stage.

`scripts/evtiming.py all` captures the text boxes of every event the game can pick, on a
computer player's turn, and builds `rips/review/event-timing.html`, where each event can
be played back with other wait values to choose how long its boxes stay up. It uses the
Story Mode menu state that `storyscenes.py menu` saves, so make that first. The values
chosen go in `events/timing.json`.

## Reading the code

`scripts/mips.py dis START END` disassembles the executable and `scripts/mips.py scan
REGEX` searches its game code instruction by instruction (`--build` reads the patched
one). `scripts/evscript.py` disassembles an event script, and `scripts/re/` has the Ghidra
setup. What's been found is in `docs/engine-notes.md`.

## Graphics

`scripts/gfx.py DISCROOT OUTDIR` renders every image on an extracted disc to PNG (the
wrappers it understands are described at its top), and `gfx.frames` puts together the
tiled frames of the animation archives.

`scripts/mksurvey.py` builds a survey of every graphic on the disc: which ones have text
in them, whether the game shows them, and what the patch did about each. It works from
those renders and the emulator screenshots in `docs/shots`. It's made of the game's own
art, so the repository doesn't include it, but anyone with the disc can make their own.
After extracting the disc as above:

```sh
python3 scripts/gfx.py rips/clean/topshop rips/gfx/us
python3 scripts/mksurvey.py     # rips/review/graphics-survey.html
```

It opens in any browser, with no other files needed.
