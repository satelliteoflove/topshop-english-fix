#!/usr/bin/env python3
"""Disassemble the executable, or search its game code.

    mips.py dis START END      disassemble START..END (hex addresses)
    mips.py scan REGEX         every instruction in the game code (0x80010000-0x8008dbfc)
                               whose "mnemonic operands" text matches REGEX

Reads the original executable from rips/clean/topshop; --build reads the patched one in
rips/build instead. Needs capstone (pip install capstone).
"""
import os, re, sys
import capstone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE = 0x80010000 - 0x800
CODE_END = 0x8008dbfc                    # __main: PsyQ library code follows


def main(args):
    exe = os.path.join(ROOT, 'rips/clean/topshop/SLUS_013.33')
    if '--build' in args:
        args.remove('--build')
        exe = os.path.join(ROOT, 'rips/build/SLUS_013.33')
    if len(args) < 2 or args[0] not in ('dis', 'scan'):
        sys.exit(__doc__)
    d = open(exe, 'rb').read()
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    if args[0] == 'dis':
        lo, hi = int(args[1], 16), int(args[2], 16)
        for i in md.disasm(d[lo - BASE:hi - BASE], lo):
            print(f'{i.address:08x}  {i.mnemonic:8s} {i.op_str}')
    else:
        md.skipdata = True
        pat = re.compile(args[1])
        for i in md.disasm(d[0x800:CODE_END - BASE], 0x80010000):
            s = f'{i.mnemonic} {i.op_str}'
            if pat.search(s):
                print(f'{i.address:08x}  {s}')


if __name__ == '__main__':
    main(sys.argv[1:])
