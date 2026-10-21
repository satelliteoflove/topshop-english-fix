#!/usr/bin/env python3
"""Top Shop's event script bytecode (interpreter: MAIN 8007c9a0's switch, opcode handlers
listed there). A script is entry 0 of a .J archive, run from its first byte. Opcodes and
operands are big-endian halfwords, with no alignment: an op can start on an odd byte.

An operand at or below -0x7f01 (0x80ff and up as unsigned) names a script variable
(MAIN 80083cb0); anything else is a literal. Jump targets and data pointers are byte
offsets from the script's start (DAT_800b269c).

    evscript.py FILE [--dis]     trace a script and report what's covered
"""
import struct, sys

# opcode: (length in bytes, or None for variable; {operand byte offset: kind})
#   kind 'jump' = a code offset, 'call' = gosub, 'data' = a data table offset,
#   'text' = an offset to a NUL-terminated string
OPS = {
    0x00: (2, {}),            # end of script (8007f3ec clears the box, stops the interpreter)
    0x01: (4, {}), 0x02: (4, {}), 0x03: (6, {}),
    0x10: (4, {2: 'jump'}),   # goto
    0x12: (None, {}),         # switch: +2 count, +4 index, then count jump offsets
    0x13: (4, {2: 'call'}),   # gosub (return address pushed by 80083e40)
    0x14: (2, {}),            # return
    0x15: (2, {}),            # yield (returns 0 without advancing)
    0x20: (10, {2: 'jump'}),  # if (a cmp b) goto +2; +4 a, +6 b, +8 comparison
    0x21: (6, {}), 0x23: (6, {}), 0x24: (6, {}), 0x25: (6, {}), 0x26: (6, {}),
    0x27: (6, {}), 0x28: (6, {}), 0x29: (6, {}), 0x2a: (6, {}),
    0x2b: (4, {}), 0x2c: (6, {}),
    0x2d: (8, {4: 'data'}),   # var(+2) = word table(+4)[index +6]
    0x2e: (8, {}),
    0x30: (4, {}), 0x31: (2, {}), 0x32: (4, {}), 0x33: (2, {}), 0x34: (4, {}),
    0x35: (2, {}), 0x36: (6, {}), 0x37: (2, {}), 0x38: (2, {}), 0x39: (4, {}),
    0x40: (4, {}), 0x41: (4, {}), 0x42: (4, {}), 0x43: (4, {}), 0x44: (10, {}), 0x45: (2, {}),
    0x60: (None, {}),         # +2 a NUL-terminated name (a file to load)
    0x61: (10, {}), 0x62: (6, {}), 0x63: (6, {}), 0x64: (2, {}),
    0x70: (10, {}), 0x71: (8, {}), 0x72: (8, {}), 0x73: (10, {}), 0x74: (10, {}),
    0x75: (10, {}), 0x76: (6, {}),
    0x80: (14, {}), 0x81: (4, {}), 0x82: (8, {}), 0x83: (6, {}), 0x84: (8, {}),
    0x85: (8, {}), 0x86: (10, {}), 0x87: (8, {}), 0x88: (8, {}), 0x89: (8, {}),
    0x8d: (6, {}), 0x8e: (6, {}), 0x8f: (6, {}),
    0x90: (6, {}),
    0x91: (6, {4: 'data'}),   # object +2 takes 10 bytes of settings from +4
    0x92: (6, {}), 0x93: (8, {}), 0x94: (8, {}), 0x95: (6, {}), 0x96: (8, {}), 0x97: (4, {}),
    0xa0: (14, {}), 0xa1: (4, {}), 0xa2: (6, {}), 0xb0: (14, {}),
    0xc0: (2, {}), 0xc1: (2, {}), 0xc2: (2, {}), 0xc3: (2, {}), 0xc4: (4, {}), 0xc5: (2, {}),
    0xc6: (4, {}), 0xc8: (2, {}), 0xc9: (4, {}),
    0xca: (None, {}),         # text: a NUL-terminated string inline at +2 (80080c90)
    0xcb: (6, {}), 0xcc: (4, {}), 0xcd: (4, {}), 0xce: (4, {}),
    0xcf: (4, {2: 'text'}),   # text: the string at script offset +2 (80080f2c)
    0xd0: (2, {}), 0xd1: (2, {}), 0xf1: (8, {}), 0xf2: (8, {}),
    0x100: (8, {}), 0x101: (4, {}), 0x102: (4, {}), 0x140: (6, {}), 0x141: (8, {}),
    0x180: (6, {}), 0x181: (8, {}), 0x182: (6, {}), 0x183: (6, {}), 0x184: (4, {}),
    0x185: (6, {}), 0x186: (6, {}), 0x187: (6, {}), 0x188: (2, {}), 0x189: (4, {}),
    0x18a: (4, {}), 0x18b: (4, {}), 0x18c: (6, {}), 0x18d: (8, {}), 0x18e: (6, {}),
    0x18f: (6, {}), 0x190: (2, {}), 0x191: (6, {}), 0x192: (8, {}), 0x193: (6, {}),
    0x194: (6, {}),
}
STOP = {0x00, 0x10, 0x14, 0x15}   # flow doesn't fall through (0x15 resumes in place, but
                                  # what follows a yield is still reached from it)
STOP.discard(0x15)


def h(d, p):
    return struct.unpack_from('>H', d, p)[0]


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def is_var(v):
    return s16(v) < -0x7f00


def oplen(d, p):
    op = h(d, p)
    n, _ = OPS[op]
    if n is not None:
        return n
    if op == 0x12:
        cnt = h(d, p + 2)
        return ((2 * s16(cnt)) + 6) & 0xfffe
    return d.index(b'\0', p + 2) - p + 1     # 0x60, 0xca


class Script:
    def __init__(self, d):
        self.d = d
        self.ops = {}       # offset -> (op, length)
        self.refs = []      # (from offset, operand offset, kind, target)
        self.strings = {}   # string offset -> bytes (0xca inline and 0xcf targets)
        self.data = set()   # data table offsets
        self.errors = []
        self.trace(0)

    def trace(self, start):
        d, work = self.d, [start]
        while work:
            p = work.pop()
            while p not in self.ops:
                if p + 2 > len(d):
                    self.errors.append(f'{p:#x}: runs off the end'); break
                op = h(d, p)
                if op not in OPS:
                    self.errors.append(f'{p:#x}: unknown opcode {op:#x}'); break
                n = oplen(d, p)
                self.ops[p] = (op, n)
                if op == 0xca:
                    self.strings[p + 2] = d[p + 2:p + n - 1]
                for at, kind in OPS[op][1].items():
                    v = h(d, p + at)
                    if is_var(v):
                        continue
                    self.refs.append((p, p + at, kind, v))
                    if kind in ('jump', 'call'):
                        work.append(v)
                    elif kind == 'text':
                        e = d.index(b'\0', v); self.strings[v] = d[v:e]
                    else:
                        self.data.add(v)
                if op == 0x12:
                    for k in range(s16(h(d, p + 2))):
                        v = h(d, p + 6 + 2 * k)
                        self.refs.append((p, p + 6 + 2 * k, 'jump', v)); work.append(v)
                if op in STOP:
                    break
                p += n

    def coverage(self):
        cov = bytearray(len(self.d))
        for p, (op, n) in self.ops.items():
            cov[p:p + n] = b'\1' * n
        for s, b in self.strings.items():
            cov[s:s + len(b) + 1] = b'\1' * (len(b) + 1)
        return cov


def main():
    d = open(sys.argv[1], 'rb').read()
    s = Script(d)
    cov = s.coverage()
    gaps, i = [], 0
    while i < len(d):
        if not cov[i]:
            j = i
            while j < len(d) and not cov[j]: j += 1
            gaps.append((i, j)); i = j
        else:
            i += 1
    print(f'{len(s.ops)} ops, {len(s.strings)} strings, {len(s.data)} data tables, '
          f'{sum(cov)}/{len(d)} bytes covered, {len(gaps)} gaps, errors: {s.errors}')
    if '--dis' in sys.argv:
        for p in sorted(s.ops):
            op, n = s.ops[p]
            print(f'{p:05x}  {op:04x}  {d[p+2:p+n].hex(" ")[:90]}')
    for a, b in gaps[:20]:
        print(f'  gap {a:#x}-{b:#x}: {d[a:min(b, a+24)].hex(" ")}')


if __name__ == '__main__':
    main()
