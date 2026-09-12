#!/usr/bin/env python3
"""Exercise the installed toolchain in a fresh private directory."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--prefix',type=Path,required=True)
p.add_argument('--work',type=Path,required=True)
p.add_argument('--network',action='store_true')
a=p.parse_args()
assert sys.platform=='ohos'
a.work.mkdir(parents=True,exist_ok=False)
env=os.environ.copy()
env['PATH']=str(a.prefix/'bin')+os.pathsep+env['PATH']
env['CARGO_HOME']=str(a.work/'cargo-home')
env['TMPDIR']=str(a.work/'tmp')
Path(env['TMPDIR']).mkdir()
records=[]
def run(args, cwd=None, ok=True, contains=None, timeout=300):
    r=subprocess.run(args,cwd=cwd or a.work,env=env,capture_output=True,text=True,timeout=timeout)
    records.append({'command':args,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
    print(json.dumps(records[-1]),flush=True)
    assert (r.returncode==0)==ok, args
    if contains: assert contains in r.stdout+r.stderr, args
    return r

def put(name,text):
    path=a.work/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text)

for name in ['rustc','cargo','rustfmt','cargo-fmt','clippy-driver','cargo-clippy','rust-analyzer']:
    run([name,'--version'])
run(['rustc','-vV'],contains='host: aarch64-unknown-linux-ohos')
put('standalone.rs', '''use std::{thread,fs,io::{Read,Write},net::{TcpListener,TcpStream},os::unix::net::UnixStream};
fn main() {
 let thread=thread::spawn(|| 42); assert_eq!(thread.join().unwrap(),42);
 fs::write("file with spaces", b"native").unwrap(); assert_eq!(fs::read("file with spaces").unwrap(),b"native");
 let listener=TcpListener::bind("127.0.0.1:0").unwrap(); let addr=listener.local_addr().unwrap();
 let worker=thread::spawn(move||{let(mut s,_)=listener.accept().unwrap();s.write_all(b"ok").unwrap();});
 let mut s=TcpStream::connect(addr).unwrap();let mut data=[0;2];s.read_exact(&mut data).unwrap();assert_eq!(&data,b"ok");worker.join().unwrap();
 let (mut a,mut b)=UnixStream::pair().unwrap();a.write_all(b"hi").unwrap();b.read_exact(&mut data).unwrap();assert_eq!(&data,b"hi");
 println!("NATIVE_STD_OK");
}
''')
run(['rustc','standalone.rs','-o','signed executable'])
run([str(a.work/'signed executable')],contains='NATIVE_STD_OK')
run(['rustc','standalone.rs','--target','aarch64-unknown-linux-ohos','-o','target executable'])
run([str(a.work/'target executable')],contains='NATIVE_STD_OK')
run(['rustc','standalone.rs','-C','linker=/nonexistent/explicit-user-linker'],ok=False,contains='explicit-user-linker')
put('response.c','int main(void) { return 0; }\n')
put('link.rsp','"response.c" -o "response executable"\n')
run([str(a.prefix/'libexec/ohos-linker'),'@link.rsp'])
run([str(a.work/'response executable')])
put('invalid.rs','fn main() { let value: i32 = "wrong"; }')
run(['rustc','invalid.rs'],ok=False,contains='mismatched types')
run(['cargo','new','--vcs','none','app'])
put('app/Cargo.toml','''[package]
name = "native_acceptance"
version = "0.1.0"
edition = "2024"
build = "build.rs"
[dependencies]
answer_macro = { path = "../answer_macro" }
''')
put('answer_macro/Cargo.toml','''[package]
name = "answer_macro"
version = "0.1.0"
edition = "2024"
[lib]
proc-macro = true
''')
put('answer_macro/src/lib.rs','''extern crate proc_macro;
#[proc_macro]
pub fn answer(_: proc_macro::TokenStream) -> proc_macro::TokenStream { "42".parse().unwrap() }
''')
put('app/native.c','int native_value(void) { char code[4]={0}; __builtin___clear_cache(code, code+sizeof(code)); return 42; }\n')
put('app/build.rs','''use std::{env,path::PathBuf,process::Command};
fn main() {
 let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());
 assert!(Command::new("clang").args(["-c","native.c","-o"]).arg(out.join("native.o")).status().unwrap().success());
 assert!(Command::new("llvm-ar").arg("rcs").arg(out.join("libnative.a")).arg(out.join("native.o")).status().unwrap().success());
 println!("cargo:rustc-link-search=native={}",out.display());
 println!("cargo:rustc-link-lib=static=native");
 println!("cargo:rerun-if-changed=native.c");
}
''')
put('app/src/main.rs','''unsafe extern "C" { fn native_value() -> i32; }
fn main() { assert_eq!(answer_macro::answer!(), unsafe { native_value() }); println!("CARGO_NATIVE_OK"); }
#[test]
fn ffi_and_macro() { assert_eq!(answer_macro::answer!(), unsafe { native_value() }); }
''')
app=a.work/'app'
run(['cargo','fmt'],app)
run(['cargo','fmt','--check'],app)
run(['cargo','run','--offline'],app,contains='CARGO_NATIVE_OK')
run(['cargo','test','--offline','--all-targets'],app,contains='1 passed')
run(['cargo','clippy','--offline','--all-targets','--','-D','warnings'],app)
# Rebuild an already signed build script, executable and proc-macro library.
for name in ['app/build.rs','answer_macro/src/lib.rs','app/src/main.rs']:
    path=a.work/name
    path.write_text(path.read_text()+'\n// force a native incremental rebuild\n')
run(['cargo','run','--offline'],app,contains='CARGO_NATIVE_OK')
run(['cargo','doc','--offline','--no-deps'],app,ok=False,contains='does not include rustdoc')
run(['rust-analyzer','diagnostics','.'],app,contains='diagnostic scan complete',timeout=300)
if a.network:
    run(['cargo','new','--vcs','none','registry_app'])
    path=a.work/'registry_app/Cargo.toml'
    path.write_text(path.read_text()+'itoa = "=1.0.15"\n')
    put('registry_app/src/main.rs','fn main() { let mut b=itoa::Buffer::new(); assert_eq!(b.format(42),"42"); println!("REGISTRY_OFFLINE_OK"); }\n')
    run(['cargo','fetch'],a.work/'registry_app',timeout=300)
    run(['cargo','run','--offline','--locked'],a.work/'registry_app',contains='REGISTRY_OFFLINE_OK')
(a.work/'results.json').write_text(json.dumps(records,indent=2)+'\n')
print('NATIVE_ACCEPTANCE_OK',len(records),flush=True)
