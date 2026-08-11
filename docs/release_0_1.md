# `official/unicode` 0.1 release gate

`0.1.0` is the frozen first standalone release: deterministic Unicode 17.0.0
extended-grapheme segmentation with pinned source data, generated tables, and
the complete UAX #29 revision 47 corpus. No public API is added after this
gate without starting a new development version.

Before publishing:

1. Run `TOKA_ROOT=/path/to/toka python3 tests/qualify_package.py` from a clean
   checkout on Linux x64 and macOS arm64. Record the exact source commit.
2. Verify `python3 tools/generate_tables.py --check` proves that the checked-in
   tables and corpus are reproducible from `data/17.0.0/SOURCES.lock.json`.
3. Create annotated tag `v0.1.0` at the qualified main commit and attach the
   deterministic `unicode-0.1.0.tar.gz` archive to its GitHub Release.
4. Calculate the archive SHA-256 and submit a reviewed static catalog PR for
   `pkg.tokalang.dev`. The entry must retain all older versions and name the
   exact tag, asset URL, and immutable digest.
5. In a fresh consumer using the default registry, resolve exact `0.1.0`, then
   prove `TOKA_OFFLINE=1 toka fetch/build/run` replays the lock unchanged.

Publication needs source-repository and catalog authority. `toka publish`
creates the archive; it does not replace the tagged-release plus reviewed
catalog workflow.
