#!/usr/bin/env python3
"""Run the native SDK linker and sign linked ELF outputs before Cargo uses them."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

def expand(args, depth=0):
    if depth > 8:
        raise ValueError('linker response files nested too deeply')
    result = []
    for arg in args:
        if arg.startswith('@'):
            result.extend(expand(shlex.split(Path(arg[1:]).read_text()), depth+1))
        else:
            result.append(arg)
    return result

def main():
    args = sys.argv[1:]
    flat = expand(args)
    output = Path('a.out')
    for i, arg in enumerate(flat):
        if arg == '-o' and i+1 < len(flat):
            output = Path(flat[i+1])
        elif arg.startswith('-o') and len(arg) > 2:
            output = Path(arg[2:])
    linking = not any(x in flat for x in ['-c','-S','-E','-M','-MM','-fsyntax-only','--version','--help'])
    cc = os.environ.get('RUST_OHOS_CC', 'clang')
    signer = shutil.which('binary-sign-tool') if linking else None
    if linking and not signer:
        sys.exit('binary-sign-tool not found; check the OHOS LLVM/toolchains PATH.')
    # OHOS disallows rewriting an inode after it has been signed/executed.
    if linking and output.exists():
        output.unlink()
    # rustc passes -nodefaultlibs. Native C dependencies can still need SDK
    # helpers (for example PCRE2 JIT's __clear_cache), absent from Rust's rlib.
    if linking and '-nodefaultlibs' in flat:
        query = subprocess.run([cc, '--rtlib=compiler-rt', '-print-libgcc-file-name'],
                               capture_output=True, text=True)
        if query.returncode:
            sys.stderr.write(query.stderr)
            return query.returncode
        builtins = Path(query.stdout.strip())
        if not builtins.is_file():
            sys.exit('OHOS SDK compiler-rt builtins archive not found: ' + str(builtins))
        args = [*args, str(builtins)]
    result = subprocess.run([cc, *args])
    if result.returncode:
        return result.returncode
    if not linking or not output.is_file():
        return 0
    with output.open('rb') as f:
        header = f.read(20)
    if header[:4] != b'\x7fELF' or int.from_bytes(header[16:18], 'little') not in (2,3):
        return 0
    mode = output.stat().st_mode & 0o777
    with tempfile.TemporaryDirectory(prefix='.rust-sign-', dir=output.parent) as tmp:
        signed = Path(tmp)/'signed'
        result = subprocess.run([signer,'sign','-inFile',str(output),'-outFile',str(signed),'-selfSign','1'],capture_output=True,text=True)
        if result.returncode:
            sys.stderr.write(result.stdout + result.stderr)
            return result.returncode
        signed.chmod(mode | 0o111)
        signed.replace(output)
    return 0

if __name__ == '__main__':
    sys.exit(main())
