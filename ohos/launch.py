#!/usr/bin/env python3
"""Relocatable launchers; keep user configuration local to each invocation."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
name, *args = sys.argv[1:]
if name == 'rustdoc':
    sys.exit('Rust 1.98.1 official OHOS distribution does not include rustdoc; cargo doc and doctests are unavailable.')
if not os.environ.get('TMPDIR'):
    private = Path('/data/storage/el2/base/haps/entry/files')
    tmp = (private if private.is_dir() and os.access(private, os.W_OK) else Path.home()) / '.cache/rust-ohos/tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ['TMPDIR'] = str(tmp)
os.environ['PATH'] = str(root / 'bin') + os.pathsep + os.environ.get('PATH', '')
if name in ('cargo', 'cargo-clippy', 'cargo-fmt', 'rust-analyzer'):
    os.environ.setdefault('SSL_CERT_FILE', '/etc/ssl/certs/cacert.pem')
    os.environ.setdefault('RUSTC', str(root / 'bin/rustc'))
    os.environ.setdefault('RUSTDOC', str(root / 'bin/rustdoc'))
    os.environ.setdefault('CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER', str(root / 'libexec/ohos-linker'))
    for variable, program in [('CC', 'clang'), ('CXX', 'clang++'), ('AR', 'llvm-ar')]:
        if variable not in os.environ and variable+'_'+ 'aarch64-unknown-linux-ohos' not in os.environ:
            os.environ.setdefault(variable+'_aarch64_unknown_linux_ohos', program)
if name in ('rustc', 'clippy-driver'):
    target = None
    linker = False
    for i, arg in enumerate(args):
        if arg == '--target' and i+1 < len(args):
            target = args[i+1]
        elif arg.startswith('--target='):
            target = arg.split('=', 1)[1]
        if arg.startswith('-Clinker=') or arg.startswith('--codegen=linker='):
            linker = True
        if arg in ('-C','--codegen') and i+1 < len(args) and args[i+1].startswith('linker='):
            linker = True
    if target in (None, 'aarch64-unknown-linux-ohos') and not linker:
        args += ['-C', 'linker=' + str(root / 'libexec/ohos-linker')]
program = root / 'toolchain/bin' / name
os.execv(program, [str(program), *args])
