#!/usr/bin/env python3
"""Dump every piece of text from the original disc into rips/text/, one JSON file per
source (SLUS_013.33, and one per script archive: EVE_xxx, CNTxx, CAL_xx, TALK).

Each entry:
  id        SOURCE:hexoffset (executable: RAM address; scripts: offset in entry 0)
  text      the string as the game has it, decoded as Shift-JIS (control codes kept)
  room      executable only: bytes available in place (string + NUL + zero padding)
  how       scripts only: 'inline' (op 0xca), 'ref' (printed by 0xcf), 'loose' (no
            traced code reaches it; found by scanning)
  jp        true if the text has Japanese in it (beyond the 【】 speaker brackets)
  grows     scripts only: id of the previous line this one repeats and extends (the
            box redraws the whole message as it builds)

The dump quotes the game's script, so it stays out of the repo (rips/ is ignored).

    dumptext.py            writes rips/text/*.json and prints a summary
"""
import glob, json, os, re, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
import lzss, evscript

DISC = os.path.join(ROOT, 'rips/clean/topshop')
OUT = os.path.join(ROOT, 'rips/text')
EXE_BASE = 0x80010000 - 0x800
# where the executable keeps game text: .rdata before the game code, and the data after the
# PsyQ library (the library's own strings are dropped below)
EXE_RANGES = [(0x80010000, 0x80019aec), (0x800a1000, 0x800b2800)]
DEBUG = re.compile(r'%[dxs0-9]|%0|: %|exec |phase|DrawBuf|^~c|Bit Depth|^task_|twsave|waku|'
                   r'Library Programs|PS-X|Sony Computer|SLOT ST|com p use|save p :|Exec Logo')


def decode(b):
    return b.decode('shift_jis', 'replace')


def is_jp(t):
    return bool(re.search(r'[぀-ヿ一-鿿０-ｚ]', t.replace('【', '').replace('】', '')))


def script_of(path):
    """Entry 0 of a .J archive. Entries are stored either raw or as LZSS blocks; a block
    starts with its own size, which fits inside the entry's slot."""
    b = open(path, 'rb').read()
    lo, hi = struct.unpack_from('<2I', b, 4)
    size = struct.unpack_from('<I', b, lo)[0]
    if 4 < size <= hi - lo and hi - lo - size < 4:
        return lzss.decompress(b, lo)
    return b[lo:hi]


def exe_strings():
    d = open(os.path.join(DISC, 'SLUS_013.33'), 'rb').read()
    out = []
    for lo, hi in EXE_RANGES:
        blob = d[lo - EXE_BASE:hi - EXE_BASE]
        for m in re.finditer(rb'[\x20-\x7e\x81-\x9f\xe0-\xfc][\x20-\x7e\x40-\xfc]+\x00', blob):
            s = m.group()[:-1]
            t = decode(s)
            if '�' in t or not re.search(r'[A-Za-z]{2}|[぀-ヿ]', t) or DEBUG.search(t):
                continue
            # skip byte soup: mostly letters, spaces and punctuation
            if sum(c.isalpha() or c in " .,!?'%-&()/:" for c in t) < 0.8 * len(t):
                continue
            a = lo + m.start()
            end = m.end()
            while end < len(blob) and blob[end] == 0:
                end += 1
            out.append(dict(id=f'EXE:{a:08x}', text=t, room=end - m.start(), jp=is_jp(t)))
    return out


def script_strings(name, d):
    s = evscript.Script(d)
    found = {off: ('ref' if (d[off - 2:off] != b'\x00\xca' if off >= 2 else True) else 'inline', b)
             for off, b in s.strings.items()}
    # strings no traced code reaches (TALK's tables, dead code): scan for text-shaped runs
    for m in re.finditer(rb'(?:\x81\x79|%[A-Z])[\x20-\x7e\x81-\xfc][\x20-\x7e\x40-\xfc]*?\x00', d):
        if not any(o <= m.start() < o + len(b) + 1 for o, (_, b) in found.items()):
            found[m.start()] = ('loose', m.group()[:-1])
    out, prev = [], None
    for off in sorted(found):
        how, b = found[off]
        t = decode(b)
        e = dict(id=f'{name}:{off:04x}', text=t, how=how, jp=is_jp(t))
        if prev and len(t) > len(prev['text']) and t.startswith(prev['text']):
            e['grows'] = prev['id']
        out.append(e); prev = e
    return out, s.errors


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = []
    ex = exe_strings()
    json.dump(ex, open(os.path.join(OUT, 'EXE.json'), 'w'), ensure_ascii=False, indent=1)
    summary.append(('EXE', len(ex), sum(e['jp'] for e in ex)))
    for path in sorted(glob.glob(os.path.join(DISC, 'A', '*.J'))):
        name = os.path.basename(path)[:-2]
        if not re.match(r'(EVE_|CNT|CAL_|TALK)', name):
            continue
        entries, errors = script_strings(name, script_of(path))
        if errors:
            print(name, 'trace errors:', errors)
        if entries:
            json.dump(entries, open(os.path.join(OUT, name + '.json'), 'w'), ensure_ascii=False, indent=1)
            summary.append((name, len(entries), sum(e['jp'] for e in entries)))
    groups = {}
    for n, c, j in summary:
        g = re.sub(r'\d+', '#', n)
        a = groups.setdefault(g, [0, 0, 0]); a[0] += 1; a[1] += c; a[2] += j
    for g, (files, c, j) in groups.items():
        print(f'{g:8} {files:3} files {c:5} strings  {j:4} Japanese')


if __name__ == '__main__':
    main()
