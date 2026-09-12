# Rust 1.98.1 official OHOS toolchain integration

This branch retains the upstream Rust repository and packages the official
`aarch64-unknown-linux-ohos` host tools for oheco. It does not claim a native
bootstrap of the Rust compiler or LLVM. Baseline: upstream tag `1.98.1`, commit
`48a229ceaefd4985c50990b14116b6d856af0985`; package version `1.98.1-ohos.1`.

## Install and use

```zsh
oo update
oo install python3
oo install ohos-sdk-native
oo install ohos-sdk-toolchains
oo install rust
rustc --version
cargo new hello --vcs none
cd hello
cargo run
cargo test --all-targets
cargo fmt
cargo clippy
```

Python 3.11 or newer and `/usr/bin/zsh` run the relocatable adapters. Compiling
requires the OHOS SDK's `clang`, `clang++`, `llvm-ar`, linker, sysroot and
`binary-sign-tool` in PATH. oheco does not automatically install these external
dependencies. OpenSSL 3.5.8 is built natively and included in this package;
Cargo also uses the host's `libz.so` and `libc.so`.

The default Rust linker adapter invokes SDK Clang and signs linked executables,
Cargo build scripts and proc-macro shared libraries before they are executed or
loaded. It removes the previous output inode before rebuilding signed files.
The adapter understands response files and paths containing spaces. Explicit
Rust linker settings and `RUSTC`, `RUSTDOC`, `CC`, `CXX`, `AR` and target-specific
tool settings remain effective. `RUST_OHOS_CC` selects a different native Clang
executable for the adapter; a user-supplied linker must handle its own signing.
Only the native OHOS target is bundled and automatically configured.

`TMPDIR` is honored. Without it, the launcher uses the terminal application's
private writable `/data/storage/el2/base/haps/entry/files/.cache/rust-ohos/tmp`
when available, otherwise `$HOME/.cache/rust-ohos/tmp`. Projects that need Unix
sockets or strict POSIX permissions should also use application-private storage.
The launchers do not modify global Cargo or rustup configuration.
On the tested filesystem, incremental compilation warns that hard links are
unavailable and successfully falls back to copies. Set `CARGO_INCREMENTAL=0`
when you prefer rebuilding without that cache/warning.

For the current development host, registry operations can use the Linux proxy:

```zsh
export HTTPS_PROXY=socks5h://172.16.105.2:10808
export HTTP_PROXY="$HTTPS_PROXY"
cargo fetch
cargo build --offline --locked
```

Cargo validates TLS using OpenSSL and the system CA bundle
`/etc/ssl/certs/cacert.pem`; standard Cargo/OpenSSL CA overrides remain available.
The proxy address is environment-specific and is not embedded in the launchers.

## Included and unavailable components

Included: rustc, Cargo, the native standard library, rustfmt/cargo-fmt,
Clippy/cargo-clippy, rust-analyzer and its proc-macro server, and Rust library
sources. The official archives and their SHA-256 values are locked in
`inputs.json`; the original channel manifest is retained alongside it.

The official Rust 1.98.1 OHOS rustc component omits the `rustdoc` binary. Therefore
`cargo doc` and doctests are unavailable in this release. An internal diagnostic
launcher explains that limitation instead of finding another toolchain's
rustdoc. `cargo test --all-targets` runs ordinary unit/integration tests without
doctests. Debugger integration, rustup management, cross-target builds, Miri,
and a native Rust/LLVM source bootstrap have not been validated. Upstream
rust-gdb/rust-lldb helper files are retained internally but are not exposed as
oheco commands; their external debugger and shell dependencies are not bundled.

## Reproduce the package

Prepare Python 3.11+, curl with proxy support, the native OHOS SDK, signing tool,
and native GNU Make 4.4.1. The current host's Make was built natively from
`https://ftp.gnu.org/gnu/make/make-4.4.1.tar.gz`, SHA-256
`dd16fb1d67bfab79a72f5e8390735c49e3e8e70b4945a15ab1f81ddb78658fb3`.
It is a build prerequisite and is not redistributed in this runtime package.
The pinned native Perl build-tool archive is downloaded by `fetch.py` and is
likewise only used for building OpenSSL.

Download preparation can run on Linux or OHOS. All later steps run on the
native OHOS host, with fresh absolute paths. Replace the example proxy for the
host where preparation runs:

```zsh
python3 ohos/fetch.py --downloads /path/to/downloads --proxy socks5h://127.0.0.1:10808
# From here onward: native HarmonyOS terminal; no network is used for building.
python3 ohos/build-openssl.py --downloads /path/to/downloads \
  --build /private/rust-openssl --make /absolute/path/to/make
python3 ohos/package.py --downloads /path/to/downloads \
  --openssl-build /private/rust-openssl --prefix /private/rust-package \
  --revision ADAPTATION_COMMIT
python3 ohos/acceptance.py --prefix /private/rust-package --work /private/rust-tests
python3 ohos/archive.py --prefix /private/rust-package \
  --output /path/to/rust-1.98.1-ohos.1-arm64.tar.gz
```

Add `--network` to acceptance only when explicitly testing the registry through
your configured proxy; the subsequent crate build is offline and locked.
The scripts refuse to reuse package/test/OpenSSL build directories. Preserve
logs and the source revision when publishing. The archive retains signed ELF
bytes, executable permissions, toolchain layout, relative symlinks and licenses.

## Provenance and licenses

Official Rust binaries and library sources are reused verbatim except for OHOS
code-signing data. Their own license/COPYRIGHT files remain under
`toolchain/share/doc` and library source directories. Rust is primarily
MIT/Apache-2.0 and includes other notices documented by upstream.

OpenSSL 3.5.8 (Apache-2.0) is built from checksum-locked upstream source using
native Clang, with shared libraries, built-in providers, no loadable modules,
and no upstream test suite. Its only source modification sets the built-in CA
file to HarmonyOS's system bundle. The original license is included under
`share/oheco/OpenSSL-LICENSE.txt`. See `dependencies.json` for source URLs,
checksums and the Perl build-tool provenance. The acceptance tests exercise
Cargo's actual HTTPS path; they do not represent the full OpenSSL test suite.
