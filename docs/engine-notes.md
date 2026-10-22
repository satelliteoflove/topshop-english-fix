# Engine notes

Read from the original US disc (SLUS-01333, single-track bin md5
`e886c77d61880e3ff655af46ac82c323`) with Ghidra on 2026-10-21. Addresses are in MAIN
(the executable, `SLUS_013.33`, loaded at 0x80010000). Game code runs 0x80010000-0x8008dbfc;
PsyQ library code follows from `__main` at 0x8008dbfc.

## Disc

Everything lives in `\A\`. No filenames appear in the executable; files are read by sector
through a queued reader (8001cd60, driven from a callback).

- `.J` files are archives: a u32 count, count+1 u32 offsets (the last is the end), then the
  entries. An entry is stored raw or as an LZSS block (below); script entries (entry 0 of
  EVE, CNT, CAL, TALK) are raw. In RAM the archive keeps that layout, and
  8004309c takes entry 0 as the event script (`DAT_800b269c`) and entry 1 as a second table
  (`DAT_800b2760`).
  - `EVE_000`-`EVE_099` (3 entries): event scripts. Entry 2 is graphics.
  - `CNT00`-`CNT19` (3): rival encounter scripts ("Meow-wow-wow!").
  - `CAL_01`-`CAL_13` (3), `KAO*P` (6, faces), `CHR*P0`, `STG*` (boards), `SEQ`, `VAB`, `OPEN5`.
  - `TALK.J` (32): in-game chatter scripts, still Japanese.
- `.XA` audio, `.TIM`/`.SPC` graphics, `FONT0.FNT`/`FONT0H.FNT` fonts, `EVENT.BIN` data.

## LZSS (8001a8a8)

Okumura's LZSS: 4 KB window zeroed and written from 0xfee; a flag byte, LSB first, 1 =
literal, 0 = two bytes `lo, hi` giving offset `lo | (hi & 0xf0) << 4` and length
`(hi & 0xf) + 3`. A block starts with its own size (header included) as a u32.
`scripts/lzss.py` decodes and encodes it.

## Event scripts (interpreter 8007c9a0)

Big-endian halfword opcodes and operands, no alignment. The switch at 8007c9a0 dispatches
about 120 opcodes; each handler advances the PC (`DAT_800b2730`) through 80083c48 or jumps
through 80083c64 (target = script start + offset). An operand at 0x80ff or above names a
script variable (80083cb0), anything else is a literal. `scripts/evscript.py` has the opcode
table and traces a script from offset 0.

Ops that matter for text:

- `0x00ca` + NUL-terminated string inline (80080c90).
- `0x00cf` + offset of a string elsewhere in the script (80080f2c).
- Codes inside strings: `%K` new line (the box is 3 lines of up to 0x26 = 38 columns),
  `%Nxx` a name (`MY` = the current player, `01` etc. = a character), `%Sxx` spaces.
  Speaker tags are written `【%NMY】` with Shift-JIS brackets.
- Lines repeat with growing content: each step redraws the whole message so far.

Ops carrying script offsets: `0x10` goto, `0x13` gosub, `0x20` conditional goto (+2),
`0x12` switch (table of offsets), `0x2d` word table (+4), `0x91` 10-byte settings block
(+4), `0x90` an animation table (+4), `0xcf` string (+2). TALK reaches its lines through a
table of 6-byte records (offset, two halfwords) read with `0x2d` and printed with `0xcf`.

## Executable text

The executable holds the menus, shop and memory card messages, item and store names, the
event card list and the points-exchange list, as plain ASCII with codes `%C` (centre?),
`%K` new line, `%E` end/wait, `%L`, `%P00`.

## Untranslated text

TALK.J (32 scripts of in-play character chatter, about 312 strings) is entirely Japanese and
looks unused in the US release: the file table at 0x800a5750 still lists it (index 220),
but no code loads that index as a constant, and 15 minutes of logged play (breakpoints on
the loaders 8001c958 and 8001cb5c) never requested it. Not checked against the Japanese
release.

About 88 lines in the event scripts are Japanese (price changes, renovation events, TV crew,
quiz rules, `【お姉さん】` information-counter announcements). Script code reaches them;
whether US play ever triggers those events is still open.

## Loading

8001c958(index, dest, size, ...) and 8001cb5c(index, ...) queue a file by its index in
the table at 0x800a5750 (4 bytes each: BCD minute, second, frame, mode). Both are called
through pointer tables. `/tmp`-style logging with `emu.bp` on them lists what's loaded.

## Script oddities

- EVE_073 (the chance quiz): after the gosub at 0xc5 returns, 0xc9 `0xc8`, 0xcb `0xca ""`
  (3 bytes), then 0xce holds `2c 80`, which isn't an opcode. The interpreter's default case
  shows an error box ("%Cエラー…") and stops. Either that return never happens in practice or
  it's a latent hang; not tested.

## Rendering

8001dbb4 draws a glyph: bytes with a high nibble of 8, 9, e or f start a Shift-JIS pair,
anything else comes from the single-byte font.

## Free RAM

The game's heap (8001d48c) is 0x128 blocks of 2 KB from 0x8015c000, so it ends at
0x801f0000. Above that, up to the stack (0x801fff00, seen no deeper than 0x801ff500 in
play), nothing was ever nonzero in a RAM survey through boot, menus, Story and Free Play,
and no code or data in the executable points there. `scripts/build.py` puts relocated
executable text at 0x801f0000-0x801fa000.

## References to executable text

Every string with real text has a direct reference: 458 through pointer-table words and
112 through `lui`/`addiu` pairs, none sharing a `lui` (`scripts/exerefs.py`). The rest
(67, mostly byte soup) are reached by index or not at all and can only change in place.
