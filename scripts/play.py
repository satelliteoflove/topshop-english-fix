#!/usr/bin/env python3
"""Run a button sequence from a state, screenshotting after each step.
    play.py STATE OUTPREFIX STEP [STEP ...] [--save OUT.state]
A step is a button name (cross, circle, start, up, ...), 'wN' to wait N frames, or
'b+b' for a chord. Shots go to OUTPREFIX_NN.png."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from emu import Emu
CUE = '/mnt/WD2TB/roms/ps1/Board Game - Top Shop/Board Game - Top Shop.cue'
args = sys.argv[1:]
save = None
if '--save' in args:
    k = args.index('--save'); save = args[k + 1]; del args[k:k + 2]
state, prefix, steps = args[0], args[1], args[2:]
e = Emu(os.environ.get('CUE', CUE))
if state != '-':
    e.load(state)
for n, s in enumerate(steps):
    if s.startswith('w') and s[1:].isdigit():
        e.run(int(s[1:]))
    else:
        e.press(*s.split('+'), hold=4, after=30)
    e.shot(f'{prefix}_{n:02d}.png', scale=1)
if save:
    e.save(save)
