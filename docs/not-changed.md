# Left as they are, on purpose

Things a careful player or a later contributor might flag, which were looked at and
deliberately not changed. Decided during the 2026-10 translation pass.

## Graphics

- **"Wining Conditions"** (Free Play setup menu). The words are drawn into a packed menu
  texture with about 8 pixels before the next word, and the on-screen sprite size comes
  from a table that hasn't been decoded. "Winning" could get clipped or spill into the
  neighbouring graphic, so the typo stays.
- **"Totalmoney"** (same menu). If the layout depends on the word's size, adding a space
  risks the same trouble, and it reads well enough.
- **Event 87's picture says "AUTUMN SALE"** while its text says "Fall Sale." The picture
  is too detailed to redraw well, and American players know "Fall Sale" better, so the
  text stays and the mismatch with it.
- **Event 76's card and picture say "Miss"** and the text box says "Nothing happens."
  They read fine together.
- **Shop names** stay as they are, in the text as well as on the signs, because changing
  them means editing the sign graphics. That includes "Fruits Market", the "DX" names and
  "Abdominal" (a kind of massage, not a body part).
- **Japanese drawn into art the player never sees:** the shop signs in the cut 1–4% price
  events (4–7, 20–23), the cut time-skip pictures (55–57), both quiz pictures (73, 77),
  BG_M01 (an old January picture with 1月 and 賀), and the Tenant Wars logo the boot
  sequence loads into video RAM without showing.

## Text

The rule: text that exists only in Japanese in the US release has no place in this patch.
Small safe fixes to English that's already there are fine, even when it's rarely seen
("Faild" became "Failed").

- **Steal messages** (executable 0x80013714, 0x80013728, 0x80013734): still Japanese, for
  a cut feature. Nothing sets the player's thief flag during play.
- **Speed-up Quiz rules** (EVE_077): still Japanese. The US release never picks the event
  (the random table swapped both quizzes for event 76).
- **Cut events** (2–23, 38, 39, 55–57, 74, 78, 79, 89–99): Japanese or placeholder text.
  The random picker never chooses them. See docs/engine-notes.md, "Untranslated text".
- **TALK.J** in-play chatter: Japanese, and the US release never loads it.
- **"Saving point"** (0x80016e14): a 54th points-menu label. The menu shows 53.
- **The debug event list** (table at 0x800ab794, e.g. "【Bank＞Player】Receive money
  (large)"): only the unreachable event-select menu uses it. Its descriptions are wrong in
  places (events 53 and 54, and the sale percentages), but the event text is right.
- **"You are closed today."** (0x80012210): nothing reaches the turn state that shows it.
- **"Cancel point exchange?"** and **"Deliver to all your stores"**: already clear, kept
  as they are.
- **Story-mode scenes** (CNT00–19) only got grammar fixes. Their odd, very Japanese
  flavour ("Meow-wow-wow!", "Hurr!", "Myon myon!") is kept on purpose.
