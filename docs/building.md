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

## Graphics

`scripts/gfx.py DISCROOT OUTDIR` renders every image on an extracted disc to PNG (the
wrappers it understands are described at its top), and `gfx.frames` puts together the
tiled frames of the animation archives. `scripts/mksurvey.py` builds
`docs/graphics-survey.html` from those renders and the emulator screenshots in
`docs/shots`:

```sh
python3 scripts/gfx.py rips/clean/topshop rips/gfx/us
python3 scripts/mksurvey.py
```
