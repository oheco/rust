#!/usr/bin/env python3
"""Build pinned Cargo TLS libraries offline, on the native OHOS host."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

p = argparse.ArgumentParser()
p.add_argument('--downloads', type=Path, required=True)
p.add_argument('--build', type=Path, required=True)
p.add_argument('--make', required=True)
a = p.parse_args()
assert sys.platform == 'ohos', 'Run on HarmonyOS'
a.build.mkdir(parents=True, exist_ok=False)
env = os.environ.copy()
env['TMPDIR'] = str(a.build / 'tmp')
Path(env['TMPDIR']).mkdir()
for filename, checksum in [
 ('openssl-3.5.8.tar.gz', 'a8f84a39918ec6415ce765d9b429d313ba97b8143169c172e734b9514464f5b2'),
 ('perl-5.44.0-ohos-arm64.tar.gz', '053e5252d736fa55a98a09e5124ead6391103717eb3bd465c1da882705a9cfef')]:
 archive = a.downloads / filename
 with archive.open('rb') as f:
  assert hashlib.file_digest(f, 'sha256').hexdigest() == checksum, filename
 with tarfile.open(archive) as t:
  t.extractall(a.build, filter='data')
perl = a.build / 'perl-5.44.0-ohos-arm64'
env['PERL5LIB'] = f'{perl}/lib/5.44.0:{perl}/lib/5.44.0/aarch64-linux'
env['PATH'] = f'{perl}/bin:{Path(a.make).parent}:{env["PATH"]}'
env.update(CC='clang', AR='llvm-ar', RANLIB='llvm-ranlib', CFLAGS='-O2 -fPIC -D__MUSL__')
src = a.build / 'openssl-3.5.8'
f = src / 'crypto/x509/x509_def.c'
s = f.read_text()
assert s.count('return X509_CERT_FILE;') == 1
f.write_text(s.replace('return X509_CERT_FILE;', 'return "/etc/ssl/certs/cacert.pem";'))
for cmd in [
 [str(perl/'bin/perl'), 'Configure', 'linux-aarch64', 'shared', 'no-module', 'no-tests', '--prefix='+str(a.build/'install'), '--openssldir=/etc/ssl', '--libdir=lib'],
 [a.make, '-j4', 'build_libs']]:
 print('+', cmd, flush=True)
 subprocess.run(cmd, cwd=src, env=env, check=True)
out = a.build / 'lib'
out.mkdir()
for name in ['libssl.so.3','libcrypto.so.3']:
 subprocess.run(['binary-sign-tool','sign','-inFile',str(src/name),'-outFile',str(out/name),'-selfSign','1'],check=True)
 (out/name).chmod(0o755)
 (out/name.removesuffix('.3')).symlink_to(name)
print('OPENSSL_NATIVE_BUILD_OK', out, flush=True)
