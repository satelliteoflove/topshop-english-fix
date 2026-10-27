#!/usr/bin/env python3
"""Build the disc and make the xdelta patch against the original image.

    mkpatch.py ORIGINAL.bin [--out rips/patch]

ORIGINAL.bin must be the single-track US image (md5 e886c77d61880e3ff655af46ac82c323).
Writes topshop-english.xdelta and a .cue for the patched image, and prints the patched
image's checksums.
"""
import hashlib, os, subprocess, sys, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ORIG_MD5 = 'e886c77d61880e3ff655af46ac82c323'
NAME = 'Board Game - Top Shop (English Fix)'


def sums(path):
    d = open(path, 'rb').read()
    return (hashlib.md5(d).hexdigest(), hashlib.sha1(d).hexdigest(),
            '%08x' % (zlib.crc32(d) & 0xffffffff), len(d))


def main():
    args = sys.argv[1:]
    out = os.path.join(ROOT, 'rips/patch')
    if '--out' in args:
        k = args.index('--out'); out = os.path.abspath(args[k + 1]); del args[k:k + 2]
    orig = args[0]
    if sums(orig)[0] != ORIG_MD5:
        print(f'{orig} is not the original US image (md5 {ORIG_MD5})'); return 1
    if subprocess.call([sys.executable, os.path.join(ROOT, 'scripts/build.py')]):
        return 1
    new = os.path.join(ROOT, 'rips/iso/topshop-en.bin')
    os.makedirs(out, exist_ok=True)
    patch = os.path.join(out, 'topshop-english.xdelta')
    if subprocess.call(['xdelta3', '-f', '-e', '-9', '-S', 'djw', '-s', orig, new, patch]):
        return 1
    with open(os.path.join(out, NAME + '.cue'), 'w') as f:
        f.write(f'FILE "{NAME}.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n')
    # check the patch applies and gives back the built image
    test = os.path.join(out, 'check.bin')
    if subprocess.call(['xdelta3', '-f', '-d', '-s', orig, patch, test]):
        return 1
    ok = sums(test) == sums(new)
    os.remove(test)
    if not ok:
        print('the patch does not reproduce the built image'); return 1
    md5, sha1, crc, size = sums(new)
    print(f'{patch}: {os.path.getsize(patch)} bytes')
    print(f'patched image: {size} bytes, crc32 {crc}, md5 {md5}, sha1 {sha1}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
