#!/usr/bin/env python3
"""Generate pinned Unicode 17.0.0 grapheme data and corpus fixtures.

This program never downloads data.  It verifies the vendored source files
against SOURCES.lock.json, then deterministically emits the Toka property
tables and UAX #29 corpus fixture used by the package qualification.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys


PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data" / "17.0.0"
LOCK = DATA / "SOURCES.lock.json"
GRAPHEME_TABLES = PACKAGE / "lib" / "official" / "unicode" / "generated" / "grapheme_tables.tk"
PROPERTY_TABLES = PACKAGE / "lib" / "official" / "unicode" / "generated" / "property_tables.tk"
CORPUS = PACKAGE / "tests" / "grapheme_break_corpus.tk"


GCB_CODES = {
    "Other": "GCB_OTHER",
    "CR": "GCB_CR",
    "LF": "GCB_LF",
    "Control": "GCB_CONTROL",
    "Extend": "GCB_EXTEND",
    "ZWJ": "GCB_ZWJ",
    "Regional_Indicator": "GCB_REGIONAL_INDICATOR",
    "Prepend": "GCB_PREPEND",
    "SpacingMark": "GCB_SPACING_MARK",
    "L": "GCB_L",
    "V": "GCB_V",
    "T": "GCB_T",
    "LV": "GCB_LV",
    "LVT": "GCB_LVT",
}

INCB_CODES = {
    "None": "INCB_NONE",
    "Consonant": "INCB_CONSONANT",
    "Extend": "INCB_EXTEND",
    "Linker": "INCB_LINKER",
}

GENERAL_CATEGORY_CODES = {
    "Cn": "GENERAL_CATEGORY_UNASSIGNED",
    "Lu": "GENERAL_CATEGORY_UPPERCASE_LETTER",
    "Ll": "GENERAL_CATEGORY_LOWERCASE_LETTER",
    "Lt": "GENERAL_CATEGORY_TITLECASE_LETTER",
    "Lm": "GENERAL_CATEGORY_MODIFIER_LETTER",
    "Lo": "GENERAL_CATEGORY_OTHER_LETTER",
    "Mn": "GENERAL_CATEGORY_NONSPACING_MARK",
    "Mc": "GENERAL_CATEGORY_SPACING_MARK",
    "Me": "GENERAL_CATEGORY_ENCLOSING_MARK",
    "Nd": "GENERAL_CATEGORY_DECIMAL_NUMBER",
    "Nl": "GENERAL_CATEGORY_LETTER_NUMBER",
    "No": "GENERAL_CATEGORY_OTHER_NUMBER",
    "Pc": "GENERAL_CATEGORY_CONNECTOR_PUNCTUATION",
    "Pd": "GENERAL_CATEGORY_DASH_PUNCTUATION",
    "Ps": "GENERAL_CATEGORY_OPEN_PUNCTUATION",
    "Pe": "GENERAL_CATEGORY_CLOSE_PUNCTUATION",
    "Pi": "GENERAL_CATEGORY_INITIAL_PUNCTUATION",
    "Pf": "GENERAL_CATEGORY_FINAL_PUNCTUATION",
    "Po": "GENERAL_CATEGORY_OTHER_PUNCTUATION",
    "Sm": "GENERAL_CATEGORY_MATH_SYMBOL",
    "Sc": "GENERAL_CATEGORY_CURRENCY_SYMBOL",
    "Sk": "GENERAL_CATEGORY_MODIFIER_SYMBOL",
    "So": "GENERAL_CATEGORY_OTHER_SYMBOL",
    "Zs": "GENERAL_CATEGORY_SPACE_SEPARATOR",
    "Zl": "GENERAL_CATEGORY_LINE_SEPARATOR",
    "Zp": "GENERAL_CATEGORY_PARAGRAPH_SEPARATOR",
    "Cc": "GENERAL_CATEGORY_CONTROL",
    "Cf": "GENERAL_CATEGORY_FORMAT",
    "Cs": "GENERAL_CATEGORY_SURROGATE",
    "Co": "GENERAL_CATEGORY_PRIVATE_USE",
}

BINARY_PROPERTIES = (
    ("DerivedCoreProperties.txt", "Alphabetic", "is_alphabetic"),
    ("DerivedCoreProperties.txt", "Lowercase", "is_lowercase"),
    ("DerivedCoreProperties.txt", "Uppercase", "is_uppercase"),
    ("PropList.txt", "White_Space", "is_white_space"),
    ("DerivedCoreProperties.txt", "XID_Start", "is_xid_start"),
    ("DerivedCoreProperties.txt", "XID_Continue", "is_xid_continue"),
)


@dataclass(frozen=True)
class Range:
    start: int
    end: int
    kind: str


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_lock() -> dict[str, object]:
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    if lock.get("unicode_version") != "17.0.0":
        raise ValueError("SOURCES.lock.json must pin Unicode 17.0.0")
    return lock


def verify_sources(lock: dict[str, object]) -> None:
    source_lock = lock.get("sources")
    if not isinstance(source_lock, dict):
        raise ValueError("SOURCES.lock.json is missing sources")
    for name, metadata in source_lock.items():
        if not isinstance(name, str) or not isinstance(metadata, dict):
            raise ValueError("SOURCES.lock.json has an invalid source entry")
        expected = metadata.get("sha256")
        path = DATA / name
        if not isinstance(expected, str) or not path.is_file():
            raise ValueError("missing lock entry or source file: %s" % name)
        actual = digest(path)
        if actual != expected:
            raise ValueError("checksum mismatch for %s: expected %s, got %s" % (name, expected, actual))


def parse_range(value: str) -> tuple[int, int]:
    if ".." in value:
        start, end = value.split("..", 1)
        return int(start, 16), int(end, 16)
    point = int(value, 16)
    return point, point


def data_fields(path: Path):
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        fields = [field.strip() for field in line.split(";")]
        if len(fields) >= 2:
            yield fields


def merge_ranges(ranges: list[Range]) -> list[Range]:
    ordered = sorted(ranges, key=lambda item: (item.start, item.end, item.kind))
    merged: list[Range] = []
    for item in ordered:
        if merged and item.kind == merged[-1].kind and item.start <= merged[-1].end + 1:
            previous = merged[-1]
            merged[-1] = Range(previous.start, max(previous.end, item.end), previous.kind)
        else:
            merged.append(item)
    for previous, current in zip(merged, merged[1:]):
        if current.start <= previous.end:
            raise ValueError("overlapping property ranges: %r and %r" % (previous, current))
    return merged


def read_gcb() -> list[Range]:
    ranges: list[Range] = []
    for fields in data_fields(DATA / "GraphemeBreakProperty.txt"):
        property_name = fields[1]
        if property_name not in GCB_CODES:
            raise ValueError("unknown Grapheme_Cluster_Break value: %s" % property_name)
        start, end = parse_range(fields[0])
        ranges.append(Range(start, end, GCB_CODES[property_name]))
    return merge_ranges(ranges)


def read_incb() -> list[Range]:
    ranges: list[Range] = []
    for fields in data_fields(DATA / "DerivedCoreProperties.txt"):
        if len(fields) != 3 or fields[1] != "InCB":
            continue
        property_name = fields[2]
        if property_name not in INCB_CODES or property_name == "None":
            raise ValueError("unknown Indic_Conjunct_Break value: %s" % property_name)
        start, end = parse_range(fields[0])
        ranges.append(Range(start, end, INCB_CODES[property_name]))
    return merge_ranges(ranges)


def read_extended_pictographic() -> list[Range]:
    ranges: list[Range] = []
    for fields in data_fields(DATA / "emoji-data.txt"):
        if fields[1] != "Extended_Pictographic":
            continue
        start, end = parse_range(fields[0])
        ranges.append(Range(start, end, "1"))
    return merge_ranges(ranges)


def read_general_categories() -> list[Range]:
    ranges: list[Range] = []
    pending_start: int | None = None
    pending_category: str | None = None
    for fields in data_fields(DATA / "UnicodeData.txt"):
        if len(fields) < 3:
            raise ValueError("malformed UnicodeData.txt row")
        point = int(fields[0], 16)
        name = fields[1]
        category = fields[2]
        if category not in GENERAL_CATEGORY_CODES:
            raise ValueError("unknown General_Category value: %s" % category)
        if name.endswith(", First>"):
            if pending_start is not None:
                raise ValueError("nested UnicodeData range starting at U+%04X" % point)
            pending_start = point
            pending_category = category
        elif name.endswith(", Last>"):
            if pending_start is None or pending_category != category:
                raise ValueError("mismatched UnicodeData range ending at U+%04X" % point)
            ranges.append(Range(pending_start, point, GENERAL_CATEGORY_CODES[category]))
            pending_start = None
            pending_category = None
        else:
            ranges.append(Range(point, point, GENERAL_CATEGORY_CODES[category]))
    if pending_start is not None:
        raise ValueError("unterminated UnicodeData range starting at U+%04X" % pending_start)
    return merge_ranges(ranges)


def read_scripts() -> list[Range]:
    ranges: list[Range] = []
    for fields in data_fields(DATA / "Scripts.txt"):
        start, end = parse_range(fields[0])
        ranges.append(Range(start, end, fields[1]))
    return merge_ranges(ranges)


def read_binary_property(filename: str, property_name: str) -> list[Range]:
    ranges: list[Range] = []
    for fields in data_fields(DATA / filename):
        if fields[1] != property_name:
            continue
        start, end = parse_range(fields[0])
        ranges.append(Range(start, end, "1"))
    if not ranges:
        raise ValueError("missing binary property %s in %s" % (property_name, filename))
    return merge_ranges(ranges)


def render_ranges(name: str, shape: str, ranges: list[Range]) -> str:
    rows = ",\n".join(
        "    %s(start = 0x%X:u32, end = 0x%X:u32, kind = %s)" %
        (shape, item.start, item.end, item.kind)
        for item in ranges
    )
    return (
        "const %s_COUNT: usize = %d:usize\n" % (name, len(ranges)) +
        "const %s: [%s; %d] = [\n%s\n]\n" % (name, shape, len(ranges), rows)
    )


def render_tables(gcb: list[Range], incb: list[Range], pictographic: list[Range]) -> str:
    return """// Generated by official/unicode/tools/generate_tables.py. DO NOT EDIT.
// Source: Unicode 17.0.0, UAX #29 revision 47.

import core/types::{Char32, usize}

pub const GCB_OTHER: i32 = 0:i32
pub const GCB_CR: i32 = 1:i32
pub const GCB_LF: i32 = 2:i32
pub const GCB_CONTROL: i32 = 3:i32
pub const GCB_EXTEND: i32 = 4:i32
pub const GCB_ZWJ: i32 = 5:i32
pub const GCB_REGIONAL_INDICATOR: i32 = 6:i32
pub const GCB_PREPEND: i32 = 7:i32
pub const GCB_SPACING_MARK: i32 = 8:i32
pub const GCB_L: i32 = 9:i32
pub const GCB_V: i32 = 10:i32
pub const GCB_T: i32 = 11:i32
pub const GCB_LV: i32 = 12:i32
pub const GCB_LVT: i32 = 13:i32

pub const INCB_NONE: i32 = 0:i32
pub const INCB_CONSONANT: i32 = 1:i32
pub const INCB_EXTEND: i32 = 2:i32
pub const INCB_LINKER: i32 = 3:i32

shape GcbRange(start: Char32, end: Char32, kind: i32)
shape IncbRange(start: Char32, end: Char32, kind: i32)
shape CodepointRange(start: Char32, end: Char32, kind: i32)

""" + render_ranges("GCB_RANGES", "GcbRange", gcb) + "\n" + render_ranges("INCB_RANGES", "IncbRange", incb) + "\n" + render_ranges("EXTENDED_PICTOGRAPHIC_RANGES", "CodepointRange", pictographic) + """
pub fn grapheme_break_property(cp: Char32) -> i32 {
    auto low# = 0:usize
    auto high# = GCB_RANGES_COUNT:usize
    loop low < high {
        auto middle = low + ((high - low) / 2:usize)
        auto range = GCB_RANGES[middle]
        if cp < range.start {
            high = middle
        } else if cp > range.end {
            low = middle + 1:usize
        } else {
            return range.kind
        }
    }
    return GCB_OTHER
}

pub fn indic_conjunct_break_property(cp: Char32) -> i32 {
    auto low# = 0:usize
    auto high# = INCB_RANGES_COUNT:usize
    loop low < high {
        auto middle = low + ((high - low) / 2:usize)
        auto range = INCB_RANGES[middle]
        if cp < range.start {
            high = middle
        } else if cp > range.end {
            low = middle + 1:usize
        } else {
            return range.kind
        }
    }
    return INCB_NONE
}

pub fn is_extended_pictographic(cp: Char32) -> bool {
    auto low# = 0:usize
    auto high# = EXTENDED_PICTOGRAPHIC_RANGES_COUNT:usize
    loop low < high {
        auto middle = low + ((high - low) / 2:usize)
        auto range = EXTENDED_PICTOGRAPHIC_RANGES[middle]
        if cp < range.start {
            high = middle
        } else if cp > range.end {
            low = middle + 1:usize
        } else {
            return true
        }
    }
    return false
}
"""


def script_constant(name: str) -> str:
    return "SCRIPT_" + name.upper().replace("-", "_")


def render_lookup(function_name: str, ranges_name: str, default: str) -> str:
    return """pub fn %s(cp: Char32) -> i32 {
    auto low# = 0:usize
    auto high# = %s_COUNT:usize
    loop low < high {
        auto middle = low + ((high - low) / 2:usize)
        auto range = %s[middle]
        if cp < range.start {
            high = middle
        } else if cp > range.end {
            low = middle + 1:usize
        } else {
            return range.kind
        }
    }
    return %s
}
""" % (function_name, ranges_name, ranges_name, default)


def render_binary_lookup(function_name: str, ranges_name: str) -> str:
    return """pub fn %s(cp: Char32) -> bool {
    auto low# = 0:usize
    auto high# = %s_COUNT:usize
    loop low < high {
        auto middle = low + ((high - low) / 2:usize)
        auto range = %s[middle]
        if cp < range.start {
            high = middle
        } else if cp > range.end {
            low = middle + 1:usize
        } else {
            return true
        }
    }
    return false
}
""" % (function_name, ranges_name, ranges_name)


def render_property_tables(
    categories: list[Range], scripts: list[Range], binary_properties: list[tuple[str, list[Range]]],
) -> str:
    script_names = ["Unknown"] + sorted({item.kind for item in scripts})
    script_codes = {name: script_constant(name) for name in script_names}
    script_ranges = [Range(item.start, item.end, script_codes[item.kind]) for item in scripts]
    category_constants = "".join(
        "pub const %s: i32 = %d:i32\n" % (name, index)
        for index, name in enumerate(GENERAL_CATEGORY_CODES.values())
    )
    script_constants = "".join(
        "pub const %s: i32 = %d:i32\n" % (script_codes[name], index)
        for index, name in enumerate(script_names)
    )
    output = [
        "// Generated by official/unicode/tools/generate_tables.py. DO NOT EDIT.",
        "// Source: Unicode 17.0.0 UnicodeData.txt, Scripts.txt, DerivedCoreProperties.txt, and PropList.txt.",
        "",
        "import core/types::{Char32, usize}",
        "",
        category_constants.rstrip(),
        "",
        script_constants.rstrip(),
        "",
        "shape PropertyRange(start: Char32, end: Char32, kind: i32)",
        "",
        render_ranges("GENERAL_CATEGORY_RANGES", "PropertyRange", categories).rstrip(),
        "",
        render_ranges("SCRIPT_RANGES", "PropertyRange", script_ranges).rstrip(),
    ]
    for function_name, ranges in binary_properties:
        ranges_name = function_name.upper() + "_RANGES"
        output.extend(["", render_ranges(ranges_name, "PropertyRange", ranges).rstrip()])
    output.extend([
        "",
        render_lookup("general_category", "GENERAL_CATEGORY_RANGES", "GENERAL_CATEGORY_UNASSIGNED").rstrip(),
        "",
        render_lookup("script", "SCRIPT_RANGES", "SCRIPT_UNKNOWN").rstrip(),
    ])
    for function_name, _ in binary_properties:
        output.extend(["", render_binary_lookup(function_name, function_name.upper() + "_RANGES").rstrip()])
    return "\n".join(output) + "\n"


def utf8_len(codepoint: int) -> int:
    if codepoint <= 0x7F:
        return 1
    if codepoint <= 0x7FF:
        return 2
    if codepoint <= 0xFFFF:
        return 3
    return 4


def read_corpus() -> list[tuple[list[int], list[int], list[int]]]:
    cases: list[tuple[list[int], list[int], list[int]]] = []
    for raw in (DATA / "GraphemeBreakTest.txt").read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        scalars: list[int] = []
        boundaries: list[int] = []
        non_boundaries: list[int] = []
        for token in line.split():
            if token == "÷":
                boundaries.append(len(scalars))
            elif token == "×":
                non_boundaries.append(len(scalars))
            else:
                scalars.append(int(token, 16))
        if not boundaries or boundaries[0] != 0 or boundaries[-1] != len(scalars):
            raise ValueError("malformed GraphemeBreakTest case: %s" % raw)
        cases.append((scalars, boundaries, non_boundaries))
    if not cases:
        raise ValueError("GraphemeBreakTest.txt contains no cases")
    return cases


def byte_offsets(scalars: list[int]) -> list[int]:
    offsets = [0]
    for scalar in scalars:
        offsets.append(offsets[-1] + utf8_len(scalar))
    return offsets


def render_case(case_id: int, scalars: list[int], boundaries: list[int], non_boundaries: list[int]) -> str:
    offsets = byte_offsets(scalars)
    body = ["fn corpus_case_%d() -> bool {" % case_id, "    auto text# = string::from(\"\")"]
    for scalar in scalars:
        body.append("    text#.push_codepoint(0x%X:Char32)" % scalar)
    body.extend([
        "    auto count_result = grapheme_count(text.as_str())",
        "    if count_result.is_err() { return false }",
        "    if count_result.unwrap() != %d:usize { return false }" % (len(boundaries) - 1),
    ])
    for index, scalar_index in enumerate(boundaries):
        body.extend([
            "    auto offset_result_%d = grapheme_byte_offset(text.as_str(), %d:usize)" % (index, index),
            "    if offset_result_%d.is_err() { return false }" % index,
            "    auto offset_%d = offset_result_%d.unwrap()" % (index, index),
            "    match cede offset_%d {" % index,
            "        auto Option<usize>::Some('value) => { if 'value != %d:usize { return false } }" % offsets[scalar_index],
            "        Option<usize>::None => return false",
            "    }",
            "    auto index_result_%d = grapheme_index_at_byte_offset(text.as_str(), %d:usize)" % (index, offsets[scalar_index]),
            "    if index_result_%d.is_err() { return false }" % index,
            "    auto recovered_%d = index_result_%d.unwrap()" % (index, index),
            "    match cede recovered_%d {" % index,
            "        auto Option<usize>::Some('value) => { if 'value != %d:usize { return false } }" % index,
            "        Option<usize>::None => return false",
            "    }",
        ])
    for index, scalar_index in enumerate(non_boundaries):
        offset = offsets[scalar_index]
        body.extend([
            "    auto non_boundary_result_%d = grapheme_index_at_byte_offset(text.as_str(), %d:usize)" % (index, offset),
            "    if non_boundary_result_%d.is_err() { return false }" % index,
            "    if non_boundary_result_%d.unwrap().is_some() { return false }" % index,
        ])
    body.extend(["    return true", "}", ""])
    return "\n".join(body)


def render_corpus(cases: list[tuple[list[int], list[int], list[int]]]) -> str:
    output = [
        "// Generated by official/unicode/tools/generate_tables.py. DO NOT EDIT.",
        "// Source: Unicode 17.0.0 GraphemeBreakTest.txt.",
        "",
        "import official/unicode::{grapheme_count, grapheme_byte_offset, grapheme_index_at_byte_offset}",
        "import core/string::{string}",
        "import core/types::{Char32}",
        "",
    ]
    for case_id, (scalars, boundaries, non_boundaries) in enumerate(cases):
        output.append(render_case(case_id, scalars, boundaries, non_boundaries))
    output.append("fn main() -> i32 {")
    for case_id in range(len(cases)):
        output.append("    if !corpus_case_%d() { return %d }" % (case_id, case_id + 1))
    output.extend(["    return 0", "}", ""])
    return "\n".join(output)


def write_or_check(path: Path, content: str, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != content:
            raise ValueError("generated output is stale: %s" % path.relative_to(PACKAGE))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify sources and generated output without writing")
    arguments = parser.parse_args()
    try:
        lock = load_lock()
        verify_sources(lock)
        write_or_check(
            GRAPHEME_TABLES,
            render_tables(read_gcb(), read_incb(), read_extended_pictographic()),
            arguments.check,
        )
        binary_properties = [
            (function_name, read_binary_property(filename, property_name))
            for filename, property_name, function_name in BINARY_PROPERTIES
        ]
        write_or_check(
            PROPERTY_TABLES,
            render_property_tables(read_general_categories(), read_scripts(), binary_properties),
            arguments.check,
        )
        write_or_check(CORPUS, render_corpus(read_corpus()), arguments.check)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print("FAIL: %s" % error, file=sys.stderr)
        return 1
    print("unicode-17.0.0 tables and corpus are %s" % ("current" if arguments.check else "generated"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
