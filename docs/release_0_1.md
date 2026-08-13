# `official/unicode` 0.1 release history

## `0.1.1`

`0.1.1` is the packaging-corrected successor to `0.1.0`. It makes no public
API, Unicode data, generated-table, or corpus change. Its release archive adds
the Apache-2.0 and Unicode-3.0 license texts, the pinned Unicode 17.0.0 source
data, and the deterministic generator required by package qualification.

The maintenance gate is:

1. qualify the exact archive with the locked Toka `v1.0.0-rc.4` SDK on Linux
   x64 and macOS arm64;
2. prove regeneration is clean against `data/17.0.0/SOURCES.lock.json`;
3. prove the archive member allowlist is exact and contains no AppleDouble,
   symbolic-link, absolute-path, or parent-traversal entry;
4. publish an annotated `v0.1.1` tag and immutable GitHub Release archive;
5. retain `0.1.0` in the catalog, add `0.1.1`, and verify a fresh exact-version
   online and archive-only offline consumer replay.

## `0.1.0`

`0.1.0` is the immutable first standalone release of the deterministic Unicode
17.0.0 UAX #29 revision 47 extended-grapheme segmenter. Its source, tag,
release archive, and catalog record remain historical evidence and are never
rewritten. `0.1.1` supersedes it only for new locks because the original
archive omitted license, source-data, and generator files and carried macOS
AppleDouble metadata.
