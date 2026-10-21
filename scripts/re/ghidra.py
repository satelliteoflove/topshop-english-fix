#!/usr/bin/env python3
"""Drive headless Ghidra over Top Shop's executable (SLUS_013.33). Adapted from the
Dimguil project's driver; Top Shop has no code overlays, so there's one program.

    ghidra.py build          import, analyze, seed orphans, label, apply symbols, export (~3 min)
    ghidra.py refresh        apply symbols and re-export (use after editing CSVs)
    ghidra.py check          validate scripts/re/symbols/*.csv
    ghidra.py where ADDR     which function holds ADDR

Symbols live in scripts/re/symbols/*.csv. Columns: address,name,kind,confidence,source,note,type
  kind        function | label | global | table | field (documentation only, not applied)
  confidence  confirmed | inferred
Output: rips/re/decomp/MAIN/<addr>_<name>.c and index.json.
"""
import csv, glob, json, os, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
EXE = os.path.join(ROOT, 'rips/clean/topshop/SLUS_013.33')
RE = os.path.join(ROOT, 'rips/re')
SYMS = os.path.join(ROOT, 'scripts/re/symbols')
SCRIPTS = os.path.join(ROOT, 'scripts/re/ghidra_scripts')
TYPES = os.path.join(ROOT, 'scripts/re/types.h')
GHIDRA = os.path.expanduser('~/tools/ghidra/ghidra_12.1.4_PUBLIC/support/analyzeHeadless')
JDK = os.path.expanduser('~/tools/jdk/jdk-21.0.12.1+1')
PROGRAM = 'SLUS_013.33'
TEXT_START, TEXT_END = 0x80010000, 0x800b2800
GAME_END = 0x8008dbfc     # game code ends here; PsyQ library code (__main onward) follows
FIELDS = ['address', 'name', 'kind', 'confidence', 'source', 'note']
KINDS = {'function', 'label', 'global', 'table', 'field'}


def env():
    e = dict(os.environ)
    e['JAVA_HOME'] = JDK
    e['PATH'] = os.path.join(JDK, 'bin') + ':' + e['PATH']
    e.setdefault('GHIDRA_HEADLESS_MAXMEM', '3G')
    return e


def load_symbols():
    rows = []
    for path in sorted(glob.glob(os.path.join(SYMS, '*.csv'))):
        with open(path, encoding='utf-8', newline='') as f:
            for i, r in enumerate(csv.DictReader(f), 2):
                r['_file'] = f'{os.path.basename(path)}:{i}'
                rows.append(r)
    return rows


def check(quiet=False):
    rows, problems, seen = load_symbols(), [], {}
    for r in rows:
        where = r['_file']
        if None in r or any(r.get(k) is None for k in FIELDS):
            problems.append(f'{where}: wrong number of columns'); continue
        if r['kind'] not in KINDS:
            problems.append(f'{where}: unknown kind {r["kind"]}')
        if r['confidence'] not in ('confirmed', 'inferred'):
            problems.append(f'{where}: confidence must be confirmed or inferred')
        if r['kind'] == 'field':
            continue
        try:
            a = int(r['address'], 16)
        except ValueError:
            problems.append(f'{where}: bad address {r["address"]}'); continue
        if not r['name'].replace('_', '').isalnum() or r['name'][0].isdigit():
            problems.append(f'{where}: name must be an identifier: {r["name"]}')
        if a in seen and seen[a]['name'] != r['name']:
            problems.append(f'{where}: {r["address"]} is {r["name"]} here but {seen[a]["name"]} in {seen[a]["_file"]}')
        seen.setdefault(a, r)
    if not quiet:
        print('\n'.join(problems) or f'{len(rows)} symbols, no problems')
    return problems


def tsv():
    lines = []
    for r in load_symbols():
        if r['kind'] == 'field':
            continue
        note = ' '.join(x for x in (f'[{r["confidence"]}]', r['note'],
                                    f'({r["source"]})' if r['source'] else '') if x)
        note = note.replace('\t', ' ').replace('\n', '\\n')
        lines.append(f'{int(r["address"], 16):08x}\t{r["name"]}\t{r["kind"]}\t{note}\t{r.get("type") or ""}')
    path = os.path.join(RE, 'MAIN', 'symbols.tsv')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    return path


def headless(args, log):
    os.makedirs(os.path.join(RE, 'logs'), exist_ok=True)
    proj = os.path.join(RE, 'ghidra', 'MAIN')
    os.makedirs(proj, exist_ok=True)
    t = time.time()
    with open(os.path.join(RE, 'logs', log), 'w') as out:
        rc = subprocess.call([GHIDRA, proj, 'topshop_MAIN'] + args, stdout=out,
                             stderr=subprocess.STDOUT, env=env())
    text = open(os.path.join(RE, 'logs', log), encoding='utf-8', errors='replace').read().split('\n')
    lines = [l.split('> ', 1)[1].split(' (GhidraScript)')[0] for l in text if '.java> ' in l]
    errors = sum(1 for l in text if 'SCRIPT ERROR' in l)
    if errors and rc == 0:
        rc = 1   # headless Ghidra exits 0 even when a script throws
    status = 'ok' if rc == 0 else f'FAILED (exit {rc}, {errors} script errors; see rips/re/logs/{log})'
    print(f'MAIN: {status} in {time.time() - t:.0f}s; ' + '; '.join(lines), flush=True)
    return rc


def post_args():
    out = os.path.join(RE, 'decomp', 'MAIN')
    lib = os.path.join(RE, 'MAIN', 'library.csv')
    return ['-postScript', 'ApplySymbols.java', tsv(), TYPES,
            '-postScript', 'ExportModule.java', out, 'MAIN', lib, hex(GAME_END)]


def build():
    args = ['-import', EXE, '-overwrite', '-scriptPath', SCRIPTS, '-analysisTimeoutPerFile', '1800',
            '-postScript', 'SeedOrphans.java', hex(TEXT_START), hex(GAME_END),
            '-postScript', 'RecordLibrary.java', os.path.join(RE, 'MAIN', 'library.csv'), hex(GAME_END)]
    return headless(args + post_args(), 'build_MAIN.log')


def refresh():
    args = ['-process', PROGRAM, '-noanalysis', '-scriptPath', SCRIPTS] + post_args()
    return headless(args, 'refresh_MAIN.log')


def where(addr):
    a = int(addr, 16)
    p = os.path.join(RE, 'decomp', 'MAIN', 'index.json')
    for f in json.load(open(p))['functions']:
        if int(f['addr'], 16) <= a <= int(f['end'], 16):
            off = f' +0x{a - int(f["addr"], 16):x}' if a != int(f['addr'], 16) else ''
            print(f'{f["name"]}{off}  rips/re/decomp/MAIN/{f["addr"]}_{f["name"]}.c')


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); return 1
    cmd = args[0]
    if cmd in ('build', 'refresh'):
        if check(quiet=True):
            print('symbol problems; run ghidra.py check'); return 1
        return build() if cmd == 'build' else refresh()
    if cmd == 'check':
        return 1 if check() else 0
    if cmd == 'where':
        where(args[1]); return 0
    print(__doc__); return 1


if __name__ == '__main__':
    sys.exit(main())
