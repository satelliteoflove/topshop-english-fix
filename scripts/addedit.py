#!/usr/bin/env python3
"""Add or replace one edit in translations/SOURCE.json, stamped with the hash of the original
(from rips/text/SOURCE.json).

    addedit.py SOURCE ID NEWTEXT
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(ROOT); sys.path.insert(0, 'scripts')
from build import src_hash
src, i, new = sys.argv[1:4]
orig = {e['id']: e['text'] for e in json.load(open(f'rips/text/{src}.json'))}[i]
p = f'translations/{src}.json'
edits = json.load(open(p)) if os.path.exists(p) else []
edits = [e for e in edits if e['id'] != i] + [dict(id=i, text=new, src=src_hash(orig))]
edits.sort(key=lambda e: e['id'])
json.dump(edits, open(p, 'w'), ensure_ascii=False, indent=1)
