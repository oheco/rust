#!/usr/bin/env python3
"""Archive signed native files without following or converting symlinks."""
import argparse, hashlib, json, tarfile
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--prefix',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
if a.output.exists(): p.error('refusing to overwrite an existing artifact')
def metadata(member):
    member.uid=member.gid=0
    member.uname=member.gname='root'
    return member
with tarfile.open(a.output,'w:gz',compresslevel=6,format=tarfile.PAX_FORMAT,dereference=False) as tar:
    tar.add(a.prefix,arcname='rust-1.98.1-ohos.1',filter=metadata)
with a.output.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
a.output.with_name(a.output.name+'.sha256').write_text(sha+'  '+a.output.name+'\n')
print(json.dumps({'filename':a.output.name,'size':a.output.stat().st_size,'sha256':sha}),flush=True)
