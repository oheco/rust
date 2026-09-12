#!/usr/bin/env python3
"""Prepare checksum-locked inputs through an explicitly selected proxy."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--downloads',type=Path,required=True)
p.add_argument('--proxy',default=os.environ.get('HTTPS_PROXY'))
a=p.parse_args()
if not a.proxy: p.error('set --proxy or HTTPS_PROXY; direct downloads are not used')
a.downloads.mkdir(parents=True,exist_ok=True)
source=Path(__file__).resolve().parent
entries=json.loads((source/'inputs.json').read_text())['components']+json.loads((source/'dependencies.json').read_text())
for entry in entries:
    path=a.downloads/entry['filename']
    def valid():
        if not path.is_file(): return False
        with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()==entry['sha256']
    if not valid():
        partial=path.with_name(path.name+'.partial')
        subprocess.run(['curl','--fail','--location','--retry','3','--proxy',a.proxy,'--output',str(partial),entry['url']],check=True)
        with partial.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==entry['sha256'], entry['filename']
        partial.replace(path)
    print('VERIFIED',path.name,flush=True)
