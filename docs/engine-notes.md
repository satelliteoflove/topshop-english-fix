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

Compared against the Japanese release, Tenant Wars (SLPS-01243, bin md5
`444ffe92ee3af2f17669a1daf158e803`, extracted to `rips/jp/tw`). The script entries of the
event files are byte-identical between the two; only their graphics entries differ.

TALK.J (32 scripts of in-play character chatter) is byte-identical in both releases. In the
US release no code loads its file index (220) as a constant, and 15 minutes of logged play
never requested it. Not checked whether the Japanese release plays it.

The Japanese lines in the event scripts all belong to events the developers had already cut:

- The Japanese executable's event-description table (0x800b3850; US 0x800ab794, one
  pointer per event number) labels events 2-23, 38, 39, 55-57, 74, 78 and 79 `ボツ`
  ("scrapped") and 89-99 `イベント無し` ("no event"). The US table leaves 2-23 and the
  others blank and calls 89-99 "No Event".
- The random event picker (8008cc4c) never chooses them in either release (below).
- They are price changes of 1-4% (2-23), one item's price ±5% (38, 39), renovation
  time-skips (55-57), "buy every empty store" (74), a TV crew and a terrorist siege
  (78, 79), and store reputation ±10% (89-94). 95-99 are copies of a price event.

## Events

An event's script is EVE_nnn.J, file index 52 + n (8006d4cc: index = event + 0x34). The
event number is stored at 0x800b2638 by one of two places:

- 80044cb8: the random picker 8008cc4c. It puts the player in one of eight brackets (asset
  gap and progress), rolls 0-199, and walks 49 nine-byte records at 0x800adc64 (event,
  then a cumulative threshold per bracket). Event 99 means the month's seasonal event,
  looked up in the bytes after the table (80-88 by month).
- 80044d34: when the flag at 0x800fe08f is set, the result of the event-select menu task
  (0x8006cecc, which shows "%CEvent:" and the description list).

The US release changed two records of the random table: rows 44 and 47 were events 73
(Chance Quiz) and 77 (Speed-up Quiz) in Japan, and are 76 ("・・・Whiff・・・", nothing
happens) in the US, with the same odds. So neither quiz comes up at random in the US, which
is likely why EVE_077's rules text was never finished and why EVE_073's dead end (below)
hasn't been seen.

The sale descriptions in the table (-20/30/40%) don't match what the sale scripts announce
(30/50/70% off). The scripts are right: op 0x18d (80082748) sets the store price percentage
(+0xe) to 70, 50 or 30. The seasonal bytes run April to March (85 85 81 81 86 81 82 87 83 80
88 84), so event 84, 総決算, is the Japanese fiscal year-end sale in March.

## Loading

8001c958(index, dest, size, ...) and 8001cb5c(index, ...) queue a file by its index in
the table at 0x800a5750 (4 bytes each: BCD minute, second, frame, mode). Both are called
through pointer tables. `/tmp`-style logging with `emu.bp` on them lists what's loaded.

## Script oddities

- EVE_073 (the chance quiz): after the gosub at 0xc5 returns, 0xc9 `0xc8`, 0xcb `0xca ""`
  (3 bytes), then 0xce holds `2c 80`, which isn't an opcode. The interpreter's default case
  shows an error box ("%Cエラー…") and stops. Either that return never happens in practice or
  it's a latent hang; not tested.
- "You are closed today." (EXE 80012210, JP 今日はおやすみです) is dead. The turn task (state
  halfword at task record +4, 0x800ce9fc for the turn; handler 80043a98) shows it in state
  3350 (0xd16), but nothing sets that state: 3320 dispatches through the five-entry table at
  0x80012314 to 3800/3400/3500/3600/3700. Store closures (EVE_030–033) only hang a "Closed"
  sign on the store; forcing event 30 and playing several rounds never reached the message.

## Rendering

8001dbb4 draws a glyph: bytes with a high nibble of 8, 9, e or f start a Shift-JIS pair,
anything else comes from the single-byte font.

## Points exchange

The list is 53 fixed 40-byte strings at 0x8001659c (label padded to column 36, cost in the
last two of 38 columns; the box is exactly that wide). Costs and pointers are pairs at
0x800abf9c, index 0 = "Earn 1 Point". 80070060 decides which items are usable (switch at
0x800173ac on index-2); the effects are the switch at 8006e4b8 (table 0x8001713c).

Store squares are 0x48-byte records at 0x80114a40. +0xd turns on a price modifier, +0xe is
the percentage, +0x10 the turn it expires. 8007661c prices each of a store's 8 item slots:
base x item percentage / 100 into +0x16, then, if +5 or +0xd is set, that x modifier / 100
into +0x18. Sales use values below 100 (80046104 treats < 100 as "on sale"). Item 31,
"Store items double (4 turns)", sets 200 on every store you own: your prices double.

Player +0x33 is a payday modifier: 1 (item 22, "Stop rival money") zeroes and 2 (item 21,
"Money double") doubles the amount 80076270 computes for the "Payday!"/"Bonus!!" task
(800579bc), which then clears it. "(Next turn)" in the US labels was wrong; it's the next
payday. Player +0x34 is a pencil mode with expiry turn at +0x58; the spinner task (around
800546a4) treats 3 (item 15, "Lower pencil movement") as spin at 0x400 instead of 0x2000
from a fixed start, and stop at once on the press instead of coasting a random amount.
Item 16 ("Reduce rival money 3/4") sets money to 3/4, not down by 3/4.

A store's shelf is +6 (items stocked, at most +7) and eight 6-byte slots from +0x14: in
stock, grade (0-5, 5 cheapest), price. Event op 0x181 (80082244, args owner, count, grade)
sets each of the owner's stores to count items of grade max(grade, 6 - 0x800ad9b4[level]);
-2 is the current player. Event 48 passes (-2, 2, 4), two of the second-cheapest product;
event 50 passes (-2, 1, 0), one of the dearest the store's level allows. Event 47's picker
(8007aba0) offers only empty spaces in areas (+2, four spaces each) where the player has no
store.

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
