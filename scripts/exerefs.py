#!/usr/bin/env python3
"""Find what in the executable points at a given address.

Code: a `lui rX, hi` followed (within its basic block, before rX is overwritten) by an
instruction that adds a signed 16-bit low half to rX: addiu/ori, or a load/store using rX
as base. Data: aligned words equal to the address, anywhere in the executable.

    exerefs.py ADDR [ADDR ...]       list references
    from exerefs import Refs; Refs().find(addr) -> [(kind, site, lui_site)]
"""
import os, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
EXE = os.path.join(ROOT, 'rips/clean/topshop/SLUS_013.33')
BASE = 0x80010000 - 0x800
CODE = (0x80019aec, 0x8008dbfc)     # game code (the PsyQ library follows)

LOADSTORE = {0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2b}   # lb lh lw lbu lhu sb sh sw
BRANCH = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07}


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


class Refs:
    def __init__(self, data=None):
        self.d = data if data is not None else open(EXE, 'rb').read()
        self.code = {}     # target address -> [(kind, site, lui_site)]
        self.luis = {}     # lui site -> [sites that complete it]
        self._scan_code()

    def word(self, a):
        return struct.unpack_from('<I', self.d, a - BASE)[0]

    def _scan_code(self):
        lo, hi = CODE
        words = [self.word(a) for a in range(lo, hi, 4)]
        # branch and jump targets start a block with nothing known
        targets = set()
        for i, w in enumerate(words):
            a, op = lo + 4 * i, w >> 26
            if op in BRANCH:
                targets.add(a + 4 + 4 * s16(w & 0xffff))
            elif op in (0x02, 0x03):
                targets.add((a & 0xf0000000) | (w & 0x3ffffff) << 2)
        CALLER_SAVED = set(range(1, 16)) | {24, 25, 31}
        live = {}          # reg -> (hi value, lui site)
        after = None       # what to drop once the delay slot has run: 'all' or 'call'
        for i, w in enumerate(words):
            a = lo + 4 * i
            if a in targets:
                live.clear()
            drop, after = after, None
            op, rs, rt, rd = w >> 26, (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
            imm = w & 0xffff
            if op == 0x0f:                                   # lui
                live[rt] = (imm << 16, a)
            elif op in (0x09, 0x0d) and rs in live:          # addiu / ori
                h, site = live[rs]
                t = (h + s16(imm)) & 0xffffffff if op == 0x09 else h | imm
                self._add(t, 'addiu' if op == 0x09 else 'ori', a, site)
                live.pop(rt, None)
            elif op in LOADSTORE and rs in live:
                h, site = live[rs]
                self._add((h + s16(imm)) & 0xffffffff, 'mem', a, site)
                if op < 0x28:
                    live.pop(rt, None)
            elif op == 0:
                f = w & 0x3f
                if f in (8, 9):                              # jr / jalr
                    after = 'all' if f == 8 else 'call'
                if f not in (8, 0x18, 0x19, 0x1a, 0x1b, 0x11, 0x13):   # writes rd
                    live.pop(rd, None)
            elif op == 0x02:
                after = 'all'
            elif op == 0x03:
                after = 'call'
            elif op in BRANCH or op in (0x2b, 0x29, 0x28):   # branches, stores: no reg write
                pass
            else:
                live.pop(rt, None)
            if op in (0x10, 0x12):                           # cop moves: mfc writes rt
                live.pop(rt, None)
            if drop == 'all':
                live.clear()
            elif drop == 'call':
                for r in CALLER_SAVED:
                    live.pop(r, None)

    def _add(self, target, kind, site, lui):
        self.code.setdefault(target, []).append((kind, site, lui))
        self.luis.setdefault(lui, []).append(site)

    def find(self, addr):
        out = list(self.code.get(addr, []))
        for o in range(0, len(self.d) - 3, 4):
            if struct.unpack_from('<I', self.d, o)[0] == addr:
                out.append(('word', o + BASE, None))
        return out

    def shared(self, lui):
        """Sites besides one pair that use this lui."""
        return self.luis.get(lui, [])


def main():
    r = Refs()
    for x in sys.argv[1:]:
        a = int(x, 16)
        for kind, site, lui in r.find(a):
            extra = f' (lui {lui:08x}, shared by {len(r.shared(lui))})' if lui else ''
            print(f'{a:08x}  {kind:5} at {site:08x}{extra}')


if __name__ == '__main__':
    main()
