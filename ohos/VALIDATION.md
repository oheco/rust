# Native validation record

Environment: the available HarmonyOS PC ARM64 terminal host, 2026-09-12;
LLVM/Clang 15.0.4 from the native SDK; native Python 3.14.7;
`aarch64-unknown-linux-ohos` official Rust 1.98.1, commit
`48a229ceaefd4985c50990b14116b6d856af0985`.

## Verified before packaging

- All seven component archives match the SHA-256 values in the official manifest.
- OpenSSL 3.5.8 was built from a fresh source directory on the native host using
  native Perl 5.44.0, GNU Make 4.4.1 and SDK Clang. Both shared libraries and all
  official ELF executables/libraries were signed with `binary-sign-tool`.
- rustc, Cargo, rustfmt, cargo-fmt, Clippy, cargo-clippy and rust-analyzer start.
- Explicit native targets, paths with spaces, linker response files, and
  preservation of an explicit failing user linker are covered.
- A native Rust program builds, signs automatically and runs; it exercises
  threads, files, TCP loopback and Unix socket pairs. Invalid Rust returns an error.
- An isolated Cargo binary project builds and runs using a native C static
  library from build.rs (including compiler-rt `__clear_cache`) and a separate
  Rust procedural macro. Unit tests and
  strict Clippy pass. rustfmt formats the project and its check succeeds.
- Rebuilding already signed build scripts, executables and proc-macro libraries
  succeeds. The tested filesystem refuses incremental-cache hard links; rustc
  reports this and successfully falls back to copying.
- rust-analyzer completes diagnostics of that project with the bundled Rust
  library source and proc-macro support.
- Cargo downloads `itoa = 1.0.15` from crates.io through the configured SOCKS5
  proxy while verifying TLS with the system CA bundle. The resulting locked
  crate build and run then succeed offline. Launchers set `SSL_CERT_FILE` only
  when the caller has not supplied it; no TLS verification is bypassed.
- The toolchain launcher directory and generated executable paths contain spaces.

A supplementary native offline release build of ripgrep 15.0.0 with PCRE2 also
passes its search/Unicode/JSON/ignore/error acceptance. That fixture uses the
oheco ripgrep source baseline `3c3b26c95a53cb97f1966c300ebfb867d56ea62b` with
five omitted vendored files restored from the local dependency sources and
verified against their `.cargo-checksum.json` entries. The source-completion
manifest is included in the release verification logs; this test does not
replace the existing ripgrep release.

The final signed archive is additionally unpacked and tested from a new location.
Release verification attachments record that run, artifact SHA-256, adaptation
commit, and the subsequent installation/use/removal through the published oheco
index. This avoids changing an already validated tag to add post-release results.

## Scope and known limits

This integrates official OHOS host binaries. Rust, Cargo, rustfmt, Clippy,
rust-analyzer and LLVM were not bootstrapped from source on this host. OpenSSL
and the representative Rust/C acceptance programs were built natively.

The official OHOS component does not contain rustdoc. `cargo doc` fails with an
explicit diagnostic; doctests are not available. Ordinary unit/integration tests
use `cargo test --all-targets`. The complete upstream Rust, Cargo and OpenSSL
suites were not run. Other HarmonyOS devices/releases, debugger integrations,
cross-compilation, Miri and rustup were not validated.
