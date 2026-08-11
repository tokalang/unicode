# `official/unicode` v2 development

Status: **`0.2.0-dev.0`**. `0.1.0` is published; this branch develops the
property API needed by the next regex release.

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

v2 adds `O(log ranges)` code-point queries generated from pinned Unicode 17.0.0
data. `general_category` and `script` return exported integer constants; the
binary queries cover `Alphabetic`, `Lowercase`, `Uppercase`, `White_Space`,
`XID_Start`, and `XID_Continue`.

```toka
import official/unicode::{
    GENERAL_CATEGORY_UPPERCASE_LETTER,
    SCRIPT_GREEK,
    general_category,
    is_white_space,
    script
}

assert(general_category('A' as Char32) == GENERAL_CATEGORY_UPPERCASE_LETTER)
assert(script(0x3BB:Char32) == SCRIPT_GREEK)
assert(is_white_space(0x2003:Char32))
```

Property-name parsing, normalization, and case folding remain out of scope;
regex will map its supported `\\p{...}` spellings to these primitives.

## Reproducibility and qualification

The generator never downloads data. It verifies the vendored checksums in
`data/17.0.0/SOURCES.lock.json`, then deterministically regenerates the tables
and corpus fixture.

From this package root:

```text
python3 tools/generate_tables.py --check
python3 tests/qualify_package.py
```

The qualification runs focused API tests, the complete UAX #29 corpus, and a
locked offline consumer using `import official/unicode`.

The implementation code is Apache-2.0; vendored Unicode data is covered by
the Unicode License v3. See the headers and upstream terms accompanying the
vendored data.

This repository is the canonical source for the first standalone release. The
source is frozen for the immutable `0.1.0` release; it is not yet a registry
release. The exact release evidence required to promote it is in
[the 0.1 release gate](docs/release_0_1.md).
