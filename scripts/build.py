#!/usr/bin/env python3
"""Build the patched disc from the original files and our edits.

    build.py [--out rips/iso/topshop-en]     writes NAME.bin/.cue, prints its md5

Edits live in translations/SOURCE.json (SOURCE = EXE, EVE_002, CNT00, ...), each a list of
  {"id": "CNT00:02d9", "text": "You're just a kid!", "src": "1a2b3c4d"}
id and the original text come from scripts/dumptext.py (rips/text/). src is the first 8 hex
digits of the sha1 of the original text: the build refuses an edit whose original has
changed, without the repo having to quote the game's script.

How text goes back in:
- Executable: in place, when the new string (with its NUL) fits the room the original had.
  Otherwise it goes in the pool at 0x801f0000 (above the game's heap, which ends at
  0x801f0000, and below the stack) and every reference is repointed (scripts/exerefs.py:
  lui/addiu pairs and pointer-table words). The original stays put, so a reference the
  scanner missed shows the old text rather than garbage. The pool rides at the end of the
  executable (its load size grows to cover it); the entry point becomes a stub there that
  copies the pool up and jumps to the game's own entry, 0x8008dc04, which then clears
  that area as bss.
- Script, same length: in place.
- Script, inline (op 0xca) otherwise: the op becomes `0x0010 goto END`, and END (appended
  to the script) holds `0x00ca new text` and `0x0010 goto` the op after the original. No
  existing byte moves, so no jump or table offset needs fixing. The old text stays behind
  as dead bytes.
- Script, ref (printed by op 0xcf): the new string is appended and every 0xcf that names the
  old one is repointed.
- Script, loose (no traced code reaches it): in place only, NUL-padded.

Graphics edits are listed in graphics/graphics.json, each
  {"archive": "EVE_084", "entry": 2, "record": 4, "png": "EVE_084_e2_r4.png", "src": "a36ba20a"}
The PNG is palettized with the game's own indices, the size of the record's pixel data
(a 16-bit-wide VRAM record of w words holds 2w 8-bit pixels). The build decompresses the
entry, overwrites the record's pixels, and LZSS-compresses it again. src is the first 8 hex
digits of the sha1 of the original pixels.

Files keep their place on the disc while they stay within their sector count; if one grows
past it, every later file shifts and the executable's file tables (CD positions at
0x800a5750, sector counts at 0x800a65d8) are rewritten from the new layout.
"""
import glob, hashlib, json, os, re, shutil, struct, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
import evscript, dumptext, lzss

CLEAN = os.path.join(ROOT, 'rips/clean')
DISC = os.path.join(CLEAN, 'topshop')
STAGE = os.path.join(ROOT, 'rips/build')
TRANS = os.path.join(ROOT, 'translations')
GFX = os.path.join(ROOT, 'graphics')
MKPSXISO = os.environ.get('MKPSXISO', os.path.expanduser('~/tools/mkpsxiso'))
EXE_NAME = 'SLUS_013.33'
EXE_BASE = 0x80010000 - 0x800
LBA_TABLE, SIZE_TABLE = 0x800a5750, 0x800a65d8
SECTOR = 2048


def src_hash(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:8]


def encode(text):
    return text.encode('shift_jis')


class BuildError(Exception):
    pass


def load_edits():
    edits = {}
    for path in sorted(glob.glob(os.path.join(TRANS, '*.json'))):
        src = os.path.basename(path)[:-5]
        edits[src] = json.load(open(path, encoding='utf-8'))
    return edits


def check_src(e, orig):
    if orig is None:
        raise BuildError(f'{e["id"]}: no such string in the dump')
    if e.get('src') != src_hash(orig['text']):
        raise BuildError(f'{e["id"]}: src {e.get("src")} doesn\'t match the original '
                         f'({src_hash(orig["text"])}); the dump or the id has changed')


POOL, POOL_END = 0x801f0000, 0x801fa000
GAME_ENTRY = 0x8008dc04


def patch_exe(exe, edits, dump):
    """Patch strings in place where they fit; return the pool bytes for the rest."""
    from exerefs import Refs
    by_id = {e['id']: e for e in dump}
    refs = None
    pool = bytearray()
    for e in edits:
        orig = by_id.get(e['id']); check_src(e, orig)
        a = int(e['id'].split(':')[1], 16)
        new = encode(e['text'])
        if len(new) + 1 <= orig['room']:
            o = a - EXE_BASE
            exe[o:o + orig['room']] = new + b'\0' * (orig['room'] - len(new))
            continue
        refs = refs or Refs(bytes(open(os.path.join(DISC, EXE_NAME), 'rb').read()))
        sites = refs.find(a)
        if not sites:
            raise BuildError(f'{e["id"]}: too long for its {orig["room"]} bytes, and nothing '
                             f'points at it directly (reached by index?), so it can\'t move')
        at = POOL + len(pool)
        pool += new + b'\0' + b'\0' * ((-len(new) - 1) % 4)
        if at + len(new) >= POOL_END:
            raise BuildError('the executable text pool is full')
        for kind, site, lui in sites:
            o = site - EXE_BASE
            if kind == 'word':
                struct.pack_into('<I', exe, o, at); continue
            w = struct.unpack_from('<I', exe, o)[0]
            lo = at & 0xffff
            hi = (at >> 16) + (1 if kind != 'ori' and lo & 0x8000 else 0)
            struct.pack_into('<I', exe, o, (w & 0xffff0000) | lo)
            lo_ = lui - EXE_BASE
            struct.pack_into('<I', exe, lo_, (struct.unpack_from('<I', exe, lo_)[0] & 0xffff0000) | hi)
    return bytes(pool)


def attach_pool(exe, pool):
    """Append the stub and pool to the executable and point the entry at the stub."""
    t_addr, t_size = struct.unpack_from('<II', exe, 0x18)
    stub_at = t_addr + t_size
    src = stub_at + 0x40
    end = src + len(pool)
    def lui(r, v): return 0x3c000000 | r << 16 | (v >> 16) + (1 if v & 0x8000 else 0)
    def addiu(rt, rs, v): return 0x24000000 | rs << 21 | rt << 16 | (v & 0xffff)
    T0, T1, T2, T3 = 8, 9, 10, 11
    code = [lui(T0, src), addiu(T0, T0, src), lui(T1, POOL), addiu(T1, T1, POOL),
            lui(T2, end), addiu(T2, T2, end),
            0x8d000000 | T0 << 21 | T3 << 16,                 # loop: lw t3, 0(t0)
            addiu(T0, T0, 4),
            0xad000000 | T1 << 21 | T3 << 16,                 # sw t3, 0(t1)
            0x14000000 | T0 << 21 | T2 << 16 | (-4 & 0xffff), # bne t0, t2, loop
            addiu(T1, T1, 4),
            0x08000000 | (GAME_ENTRY >> 2) & 0x3ffffff,       # j game entry
            0]
    blob = b''.join(struct.pack('<I', c) for c in code)
    blob += b'\0' * (0x40 - len(blob)) + pool
    blob += b'\0' * ((-len(blob)) % 0x800)
    exe += blob
    struct.pack_into('<I', exe, 0x10, stub_at)                # pc0
    struct.pack_into('<I', exe, 0x1c, t_size + len(blob))     # t_size


def patch_script(name, d, edits, dump):
    """Return the patched script bytes (entry 0)."""
    by_id = {e['id']: e for e in dump}
    s = evscript.Script(bytes(d))
    d = bytearray(d)

    def append(b):
        at = len(d)
        if at + len(b) >= 0x7f00:
            raise BuildError(f'{name}: script would pass 0x7f00 bytes; offsets above that read as variables')
        d.extend(b)
        return at

    for e in edits:
        orig = by_id.get(e['id']); check_src(e, orig)
        off = int(e['id'].split(':')[1], 16)
        old, new = encode(orig['text']), encode(e['text'])
        if len(new) == len(old):
            d[off:off + len(old)] = new
            continue
        how = orig['how']
        if how == 'inline':
            op = off - 2
            after = op + 2 + len(old) + 1
            end = append(b'\x00\xca' + new + b'\0' + b'\x00\x10' + struct.pack('>H', after))
            d[op:op + 4] = b'\x00\x10' + struct.pack('>H', end)
        elif how == 'ref':
            at = append(new + b'\0')
            refs = [r for r in s.refs if r[2] == 'text' and r[3] == off]
            if not refs:
                raise BuildError(f'{e["id"]}: no 0xcf names this string')
            for _, operand, _, _ in refs:
                d[operand:operand + 2] = struct.pack('>H', at)
        else:
            if len(new) > len(old):
                raise BuildError(f'{e["id"]}: loose string (no traced code) can only shrink in place')
            d[off:off + len(old) + 1] = new + b'\0' * (len(old) + 1 - len(new))
    errors = evscript.Script(bytes(d)).errors
    before = set(s.errors)
    if set(errors) - before:
        raise BuildError(f'{name}: the patched script no longer traces: {set(errors) - before}')
    return bytes(d)


def load_graphics():
    p = os.path.join(GFX, 'graphics.json')
    by_archive = {}
    for g in json.load(open(p)) if os.path.exists(p) else []:
        by_archive.setdefault(g['archive'], []).append(g)
    return by_archive


def patch_graphics(path, gs):
    """Return {entry index: new stored bytes} for the graphics edits of one archive."""
    from PIL import Image
    b = open(path, 'rb').read()
    offs = struct.unpack_from(f'<{struct.unpack_from("<I", b, 0)[0] + 1}I', b, 4)
    out = {}
    for k in sorted({g['entry'] for g in gs}):
        e = bytearray(lzss.decompress(b, offs[k]))
        recs, p = [], 0
        while p + 20 <= len(e):
            n, x, y, w, h = struct.unpack_from('<IHHHH', e, p + 8)
            recs.append((p + 20, w * 2, h))
            p += 8 + n
        for g in (g for g in gs if g['entry'] == k):
            po, w, h = recs[g['record']]
            if hashlib.sha1(e[po:po + w * h]).hexdigest()[:8] != g['src']:
                raise BuildError(f'{g["png"]}: the original pixels have changed')
            im = Image.open(os.path.join(GFX, g['png']))
            if im.mode != 'P' or im.size != (w, h):
                raise BuildError(f'{g["png"]}: want a {w}x{h} palettized PNG')
            e[po:po + w * h] = im.tobytes()
        block = lzss.compress(bytes(e))
        if lzss.decompress(block) != bytes(e):
            raise BuildError(f'{os.path.basename(path)} entry {k}: LZSS round trip failed')
        out[k] = block
    return out


def rebuild_archive(path, entry0, replace=None):
    """Repack a .J with a new entry 0 (None keeps it) and any other entries replaced. Checked
    to give back the original byte for byte for every EVE, CNT and CAL archive; TALK.J pads
    differently and isn't handled."""
    if os.path.basename(path) == 'TALK.J':
        raise BuildError('TALK.J repacking is not supported')
    b = open(path, 'rb').read()
    n = struct.unpack_from('<I', b, 0)[0]
    offs = struct.unpack_from(f'<{n + 1}I', b, 4)
    replace = replace or {}
    entries = [entry0 if entry0 is not None else b[offs[0]:offs[1]]]
    entries += [replace.get(i, b[offs[i]:offs[i + 1]]) for i in range(1, n)]
    head = 4 + 4 * (n + 1)
    out, pos = bytearray(), head
    new_offs = []
    for e in entries:
        new_offs.append(pos)
        out += e
        pad = (-len(out)) % 4     # the originals keep entries word-aligned
        out += b'\0' * pad
        pos += len(e) + pad
    new_offs.append(pos)
    return struct.pack(f'<{n + 2}I', n, *new_offs) + bytes(out)


def bcd(v):
    return (v // 10) << 4 | v % 10


def msf(lba):
    lba += 150
    return bytes([bcd(lba // 4500), bcd(lba // 75 % 60), bcd(lba % 75)])


def layout(xml_text, staged):
    """Place every file after one that grew past its sector count later by the growth.
    Returns the new XML, {name: (lba, sectors)} and the total growth in sectors."""
    shift, table = 0, {}

    def place(m):
        nonlocal shift
        tag = m.group(0)
        offs = int(re.search(r'offs="(\d+)"', tag).group(1))
        new_tag = re.sub(r'offs="\d+"', f'offs="{offs + shift}"', tag)
        f = re.match(r'<file name="([^"]+)" source="([^"]+)"', tag)
        if f:
            name, source = f.groups()
            orig = -(-os.path.getsize(os.path.join(CLEAN, source)) // SECTOR)
            path = staged.get(name)
            sectors = -(-os.path.getsize(path) // SECTOR) if path else orig
            table[name] = (offs + shift, sectors)
            if path:
                new_tag = new_tag.replace(f'source="{source}"', f'source="{os.path.relpath(path, CLEAN)}"')
            if sectors != orig and name.endswith('.XA'):
                raise BuildError('an XA file changed size; untested')
            shift += sectors - orig
        return new_tag

    out = re.sub(r'<(?:file|dummy) [^>]*?offs="\d+"[^>]*/>', place, xml_text)
    return out, table, shift


def main():
    args = sys.argv[1:]
    out = os.path.join(ROOT, 'rips/iso/topshop-en')
    if '--out' in args:
        out = os.path.abspath(args[args.index('--out') + 1])
    if not os.path.exists(os.path.join(ROOT, 'rips/text/EXE.json')):
        dumptext.main()
    shutil.rmtree(STAGE, ignore_errors=True)
    os.makedirs(os.path.join(STAGE, 'A'))
    edits = load_edits()
    graphics = load_graphics()
    for a in graphics:
        edits.setdefault(a, [])
    staged = {}
    exe = bytearray(open(os.path.join(DISC, EXE_NAME), 'rb').read())
    try:
        for src, es in sorted(edits.items()):
            if not es and src not in graphics:
                continue
            dump = json.load(open(os.path.join(ROOT, 'rips/text', src + '.json'), encoding='utf-8')) if es else None
            if src == 'EXE':
                pool = patch_exe(exe, es, dump)
                if pool:
                    attach_pool(exe, pool)
                    print(f'EXE: {len(es)} edits, {len(pool)} bytes in the pool')
                continue
            path = os.path.join(DISC, 'A', src + '.J')
            new0 = patch_script(src, dumptext.script_of(path), es, dump) if es else None
            gs = graphics.get(src, [])
            blob = rebuild_archive(path, new0, patch_graphics(path, gs) if gs else None)
            dst = os.path.join(STAGE, 'A', src + '.J')
            open(dst, 'wb').write(blob)
            staged[src + '.J'] = dst
            old_s, new_s = -(-os.path.getsize(path) // SECTOR), -(-len(blob) // SECTOR)
            print(f'{src}: {len(es)} edits' + (f', {len(gs)} graphics' if gs else '')
                  + f', {os.path.getsize(path)} -> {len(blob)} bytes'
                  + (f' ({old_s} -> {new_s} sectors)' if new_s != old_s else ''))
        exe_path = os.path.join(STAGE, EXE_NAME)
        open(exe_path, 'wb').write(exe)        # sized now; the file tables are patched below
        staged[EXE_NAME] = exe_path
        xml = open(os.path.join(CLEAN, 'topshop.xml')).read()
        xml, table, shift = layout(xml, staged)
    except BuildError as e:
        print('BUILD FAILED:', e); return 1
    # file tables: rewrite every entry from the new layout (a no-op when nothing moved)
    names = {}
    for n, (lba, _) in layout(open(os.path.join(CLEAN, 'topshop.xml')).read(), {})[1].items():
        names[lba] = n
    i = 0
    while True:
        o = LBA_TABLE - EXE_BASE + 4 * i
        e = exe[o:o + 4]
        lba = (e[0] >> 4) * 10 + (e[0] & 15)
        lba = lba * 4500 + ((e[1] >> 4) * 10 + (e[1] & 15)) * 75 + (e[2] >> 4) * 10 + (e[2] & 15) - 150
        name = names.get(lba)
        if not name:
            break
        nl, ns = table[name]
        exe[o:o + 3] = msf(nl)
        struct.pack_into('<I', exe, SIZE_TABLE - EXE_BASE + 4 * i, ns)
        i += 1
    open(exe_path, 'wb').write(exe)
    xml_path = os.path.join(CLEAN, 'build.xml')   # beside the original: paths resolve from here
    open(xml_path, 'w').write(xml)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # mkpsxiso resolves sources relative to the working directory
    rc = subprocess.call([MKPSXISO, '-y', '-q', '-o', out + '.bin', '-c', out + '.cue', xml_path], cwd=CLEAN)
    if rc:
        print('mkpsxiso failed'); return rc
    md5 = hashlib.md5(open(out + '.bin', 'rb').read()).hexdigest()
    print(f'{i} file table entries checked; disc grew {shift} sectors; {out}.bin md5 {md5}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
