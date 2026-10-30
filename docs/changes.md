# What's changed

Everything this patch changes, for anyone curious. The reasons behind the less obvious
choices, and the things left alone on purpose, are in [decisions.md](decisions.md).

## Text

- Menus, shopping, deliveries, buying and selling stores, turn messages and the memory
  card screens had their typos and grammar fixed, and read more naturally.
- The points exchange list says what each item really does. A few were wrong in the
  original, and every one was checked against the code that carries it out:
  - "Receive money amount of rival." gives you cash equal to the rival's total, and they
    keep theirs: "Get cash equal to a rival's money".
  - "Stop rival money.(Next turn)" and "Money double.(Next turn)" last until the next
    payday, not the next turn: "A rival misses their next payday" and "Double your next
    payday".
  - "Stores out of stock close.(All)" and "Receive all stores out of stock." only touch
    rivals' stores: "Close rivals' out-of-stock stores" and "Take rivals' out-of-stock
    stores".
  - "Deliver expensive item." delivers one to each of your stores: "Deliver 1 costly item
    to each store".
  - "Cut rival money.(stores x 150)" and "(stores x 300)": every rival pays for their own
    stores, and the money doesn't go to you, so "Rivals lose 150 per store they own" and
    "Rivals lose 300 per store they own".
- Item names got spelling and plural fixes, and a few of the stranger Japanese-English
  terms were made plainer.
- The event cards were reworded so they're clear about who's affected and how. The
  information desk announcements open with "Attention, shoppers!"
- The March sale is the "Clearance Sale" instead of "Final Sale".
- The rival scenes in Story mode got grammar and punctuation fixes only. Meower calls
  Merlin a "phony magician", and before the fight with Dona says "Behold! I am cat, hear
  me meow!"
- Two Story mode lines ran past the edge of their box in the original release, and now
  fit: Oilow's "I can't let this happen!", which overwrote the line above it, and Santa's
  challenge, which was cut off at "let's bat".

## Pictures

- The Clearance Sale picture was redrawn to match.
- "From Bigining" on the Story mode menu is "From Beginning".
- The staff credits spell ASSISTANT PLANNER, MAIN PROGRAMMER, PROGRAMMER, MAIN DESIGNER,
  DESIGNER, SUPERVISOR and EXECUTIVE PRODUCER right.
- The title screen's small print says "Agetec, Inc." instead of "Agetec,Inc.", and "TOP
  SHOP and the TOP SHOP logo" instead of "TOP SHOP and the and TOP SHOP logo".
- The Free Play picture for no computer players said "COM なし" in Japanese, and now says
  "NO / COM".

## Event text timing

On a computer player's turn, every text box after an event's first one stayed up for one
second, which was too quick to read the longer ones. In events 30-33, 47-50, 72, 75 and
80-88 those boxes now stay up for two seconds. Nothing else about the events changed, and
on your own turn every box still waits for your button.
