# `official/unicode` v1

Version: **`0.1.2` release candidate**.

`0.1.2` updates the package for Toka `1.0.0-rc.9` ownership semantics while
preserving the `0.1.1` API and Unicode 17.0.0 data set. `0.1.1` was a
packaging-only maintenance release. It keeps the `0.1.0`
Unicode 17.0.0 API, data, generated tables, and corpus unchanged while adding
complete license and reproducibility material to the release archive.

`official/unicode` provides deterministic, pure-Toka extended-grapheme
segmentation. Its package identity and public import path are
`official/unicode`; its manifest short name is `unicode`.

## Scope

v1 implements the extended grapheme-cluster rules of Unicode 17.0.0, Unicode
Standard Annex #29 revision 47. It vendors the exact UCD source files,
checksums, generated property tables, and complete `GraphemeBreakTest.txt`
corpus. It does not use ICU, CoreFoundation, or the host operating system's
Unicode data, so a locked offline consumer receives the same result on every
supported target.

```toka
import official/unicode::{grapheme_count, grapheme_slice}

auto count = grapheme_count("ÄB").unwrap()
assert(count == 2:usize)

auto first = grapheme_slice("ÄB", 0:usize, 1:usize).unwrap()
assert(first.is_some())
assert(first.unwrap().equals("Ä"))
```

The public API validates its entire input before returning a result:

```toka
pub fn grapheme_count(text: str) -> Result<usize, UnicodeError>
pub fn grapheme_byte_offset(text: str, grapheme_index: usize) -> Result<Option<usize>, UnicodeError>
pub fn grapheme_index_at_byte_offset(text: str, byte_offset: usize) -> Result<Option<usize>, UnicodeError>
pub fn grapheme_slice(text: str, start: usize, end: usize) -> Result<Option<str>, UnicodeError>
```

`UnicodeError` means malformed UTF-8. A successful `Option::None` means a
valid request that has no answer: an out-of-range index, a non-boundary byte
offset, or `start > end`. `grapheme_slice` returns `Some("")` for equal valid
boundaries. All offsets are UTF-8 byte offsets, all indexes are extended
grapheme indexes, and `grapheme_slice` is a zero-copy `str` view.

Each operation scans in `O(input_bytes)` time with bounded state and does not
allocate. v1 intentionally excludes normalization, case folding, collation,
word/sentence/line breaking, bidi layout, font shaping, and IME policy.

## Reproducibility and qualification

The generator never downloads data. It verifies the vendored checksums in
`data/17.0.0/SOURCES.lock.json`, then deterministically regenerates the tables
and corpus fixture.

From this package root:

```text
python3 tools/generate_tables.py --check
TOKA=/path/to/toka TOKAC=/path/to/tokac TOKA_LIB=/path/to/lib \
  python3 tests/qualify_package.py
python3 tools/build_release.py --output /tmp/unicode-0.1.2.tar.gz
```

The qualification runs focused API tests, the complete UAX #29 corpus, and a
locked offline consumer using `import official/unicode`.

The implementation code is covered by the [Apache License 2.0](LICENSE).
Vendored Unicode data and its generated derivatives are covered by the
[Unicode License v3](LICENSE-UNICODE); the source files retain their upstream
headers as additional provenance.

This repository is the canonical source for standalone Unicode package
releases. The immutable `0.1.0` release remains available for existing locks;
new RC9 consumers should select `0.1.2`, whose archive includes the pinned source
data, generator, qualification suite, and both license texts. Release history
and maintenance evidence are recorded in
[the 0.1 release history](https://github.com/tokalang/unicode/blob/main/docs/release_0_1.md).
