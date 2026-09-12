#!/usr/bin/env python3
"""Assemble and sign an offline official Rust distribution on HarmonyOS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

TOOLS = ['rustc', 'cargo', 'rustfmt', 'cargo-fmt', 'clippy-driver', 'cargo-clippy', 'rust-analyzer']

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def extract_component(archive, prefix):
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        component_file = next(m for m in members if m.name.endswith('/components'))
        components = tar.extractfile(component_file).read().decode().splitlines()
        for member in members:
            parts = Path(member.name).parts
            if len(parts) < 3 or parts[1] not in components or parts[2] == 'manifest.in':
                continue
            relative = Path(*parts[2:])
            assert not relative.is_absolute() and '..' not in relative.parts
            path = prefix / relative
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                assert not path.exists(), path
                with tar.extractfile(member) as source, path.open('wb') as output:
                    shutil.copyfileobj(source, output)
                path.chmod(member.mode)
            elif member.issym():
                assert not Path(member.linkname).is_absolute()
                assert (path.parent/member.linkname).resolve().is_relative_to(prefix.resolve())
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(member.linkname)
            else:
                raise ValueError((member.name, member.type))

def launchers(prefix, source):
    (prefix/'bin').mkdir(exist_ok=True)
    (prefix/'libexec').mkdir(exist_ok=True)
    for name in ['launch.py','linker.py']:
        shutil.copy2(source/name, prefix/'libexec'/name)
        (prefix/'libexec'/name).chmod(0o644)
    for name in TOOLS + ['rustdoc']:
        path = prefix/'bin'/name
        path.write_text('#!/usr/bin/zsh\nexec python3 "${0:A:h:h}/libexec/launch.py" '+name+' "$@"\n')
        path.chmod(0o755)
    path = prefix/'libexec/ohos-linker'
    path.write_text('#!/usr/bin/zsh\nexec python3 "${0:A:h}/linker.py" "$@"\n')
    path.chmod(0o755)

def sign(path):
    signed = path.with_name(path.name + '.ohos-signed')
    result = subprocess.run(['binary-sign-tool','sign','-inFile',str(path),'-outFile',str(signed),'-selfSign','1'],capture_output=True,text=True)
    if result.returncode:
        sys.exit(result.stdout+result.stderr)
    signed.chmod(path.stat().st_mode & 0o777 | 0o111)
    signed.replace(path)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--downloads',type=Path,required=True)
    p.add_argument('--openssl-build',type=Path,required=True)
    p.add_argument('--prefix',type=Path,required=True)
    p.add_argument('--revision',required=True)
    a = p.parse_args()
    assert sys.platform == 'ohos', 'Package and sign on HarmonyOS'
    source = Path(__file__).resolve().parent
    a.prefix.mkdir(parents=True,exist_ok=False)
    prefix = a.prefix/'toolchain'
    prefix.mkdir()
    inputs = json.loads((source/'inputs.json').read_text())
    for entry in inputs['components']:
        archive = a.downloads/entry['filename']
        assert digest(archive) == entry['sha256'], archive
        extract_component(archive,prefix)
        print('EXTRACTED',entry['component'],flush=True)
    for name in ['libssl.so.3','libcrypto.so.3']:
        shutil.copy2(a.openssl_build/'lib'/name,prefix/'lib'/name)
        (prefix/'lib'/name.removesuffix('.3')).symlink_to(name)
    for path in sorted(prefix.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open('rb') as f:
            header=f.read(20)
        if header[:4] == b'\x7fELF':
            assert header[18:20] == b'\xb7\x00',path
            # OpenSSL files have already been signed by the native build step.
            if path.name not in ['libssl.so.3','libcrypto.so.3']:
                sign(path)
            print('SIGNED',path.relative_to(prefix),flush=True)
    launchers(a.prefix,source)
    documentation=a.prefix/'share/oheco'
    documentation.mkdir(parents=True)
    for name in ['README.md','VALIDATION.md','inputs.json','dependencies.json','channel-rust-1.98.1.toml']:
        if (source/name).exists():
            shutil.copy2(source/name,documentation/name)
            (documentation/name).chmod(0o644)
    shutil.copy2(a.openssl_build/'openssl-3.5.8/LICENSE.txt',documentation/'OpenSSL-LICENSE.txt')
    (documentation/'build.json').write_text(json.dumps({'upstream_version':inputs['version'],'package_version':'1.98.1-ohos.1','adaptation_commit':a.revision,'upstream_commit':'48a229ceaefd4985c50990b14116b6d856af0985','host':os.uname()._asdict() if hasattr(os.uname(),'_asdict') else list(os.uname()),'official_components':inputs['components'],'openssl':'3.5.8 native OHOS build; system CA default patch'},indent=2)+'\n')
    print('PACKAGE_READY',a.prefix,flush=True)

if __name__ == '__main__':
    main()
