#!/usr/bin/env python3
"""
Validate syntax of categories.txt and signatures.txt and detect duplicates.

Expected syntax per non-comment line:
    criteria;and-criteria|tag

Checks performed:
 - Exactly one '|' separator
 - Left side contains one or more semicolon-separated non-empty criteria
 - Right side non-empty (for both files)
 - For categories.txt: tag must exist in modules/reporting.py categories keys
 - Duplicate detection:
    * exact duplicate lines (ignoring leading/trailing whitespace)
    * duplicate left-side criteria (case-insensitive normalized)
Usage: run from project root:
    python Python/tools/validate_definitions.py
"""
from pathlib import Path
import sys
import re
import ast
from collections import defaultdict, Counter

REPORTING_PATHS = [
    Path("Python/modules/reporting.py"),
    Path("modules/reporting.py"),
    Path("Python/modules/reporting.py").resolve(),
    Path("modules/reporting.py").resolve(),
    Path("Python/modules/reporting.py"),
]


def find_reporting():
    for p in REPORTING_PATHS:
        if p.exists():
            return p
    # search upward
    here = Path.cwd()
    for parent in [here] + list(here.parents)[:5]:
        candidate = parent / "Python" / "modules" / "reporting.py"
        if candidate.exists():
            return candidate
        candidate = parent / "modules" / "reporting.py"
        if candidate.exists():
            return candidate
    return None


def extract_category_keys(reporting_path: Path):
    txt = reporting_path.read_text(encoding="utf-8")
    m = re.search(r"\bcategories\s*=\s*\[", txt)
    if not m:
        raise RuntimeError("Could not find 'categories = [' in reporting.py")
    start = m.end() - 1
    depth = 0
    end = None
    for i in range(start, len(txt)):
        ch = txt[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        raise RuntimeError("Malformed categories list in reporting.py")
    list_literal = txt[start:end]
    try:
        categories = ast.literal_eval(list_literal)
    except Exception as e:
        raise RuntimeError(f"Failed to parse categories list: {e}")
    keys = set()
    for item in categories:
        if isinstance(item, (list, tuple)) and len(item) > 0:
            k = item[0]
            if k is not None:
                keys.add(str(k))
    return keys


def normalize_left(left: str):
    # normalize criteria list for duplicate detection: lower, strip whitespace, collapse spaces, keep semicolons
    parts = [p.strip().lower() for p in left.split(";") if p.strip() != ""]
    return ";".join(parts)


def validate_file(path: Path, valid_tags=None, is_categories=False):
    errors = []
    duplicates_exact = []
    duplicates_left = []
    seen_lines = {}
    left_map = defaultdict(list)

    if not path.exists():
        errors.append((0, f"File not found: {path}"))
        return errors, duplicates_exact, duplicates_left

    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n\r")
            stripped = line.strip()
            if stripped == "" or stripped.startswith("#"):
                continue

            # Exact duplicate detection (ignore surrounding whitespace)
            key_line = stripped
            if key_line in seen_lines:
                duplicates_exact.append((lineno, seen_lines[key_line], line))
            else:
                seen_lines[key_line] = lineno

            # Syntax checks: exactly one '|'
            if line.count("|") != 1:
                errors.append((lineno, "Invalid syntax: expected exactly one '|' separator"))
                continue
            left, right = line.split("|", 1)
            if right.strip() == "":
                errors.append((lineno, "Invalid syntax: missing right-side tag/cred"))
            # left must contain at least one non-empty criteria, allow semicolons
            left_strip = left.strip()
            if left_strip == "":
                errors.append((lineno, "Invalid syntax: missing criteria on left side"))
            else:
                parts = [p.strip() for p in left_strip.split(";")]
                if not any(parts):
                    errors.append((lineno, "Invalid syntax: left side has no criteria tokens"))
            # collect left duplicates normalized
            left_norm = normalize_left(left)
            left_map[left_norm].append(lineno)

            # For categories file validate tag existence
            if is_categories and valid_tags is not None and right.strip() != "":
                tag = right.strip()
                if tag not in valid_tags:
                    errors.append((lineno, f"Unknown category tag '{tag}'"))
    # Find left-side duplicates
    for left_norm, lines in left_map.items():
        if len(lines) > 1:
            duplicates_left.append((left_norm, lines))

    return errors, duplicates_exact, duplicates_left


def find_definition_files():
    # prefer Python/ versions first
    base = Path.cwd()
    candidates = {
        "categories": [
            base / "Python" / "categories.txt",
            base / "categories.txt",
            base / "categories.txt",
        ],
        "signatures": [
            base / "Python" / "signatures.txt",
            base / "signatures.txt",
            base / "signatures.txt",
        ]
    }
    paths = {}
    for key, lst in candidates.items():
        for p in lst:
            if p.exists():
                paths[key] = p
                break
        else:
            # fallback to first candidate
            paths[key] = lst[0]
    return paths["categories"], paths["signatures"]


def main():
    reporting = find_reporting()
    if not reporting:
        print("ERROR: modules/reporting.py not found. Adjust script search paths.", file=sys.stderr)
        sys.exit(2)
    try:
        valid_tags = extract_category_keys(reporting)
    except Exception as e:
        print(f"ERROR: Failed to parse reporting.py: {e}", file=sys.stderr)
        sys.exit(2)

    cat_path, sig_path = find_definition_files()
    print(f"Using reporting.py: {reporting}")
    print(f"Valid category tags ({len(valid_tags)}): {', '.join(sorted(valid_tags))}\n")
    print(f"Validating categories file: {cat_path}")
    cat_errors, cat_dups_exact, cat_dups_left = validate_file(cat_path, valid_tags, is_categories=True)
    print(f"Validating signatures file: {sig_path}")
    sig_errors, sig_dups_exact, sig_dups_left = validate_file(sig_path, valid_tags, is_categories=False)

    problems = 0
    if cat_errors:
        print("\nErrors in categories.txt:")
        for ln, msg in cat_errors:
            problems += 1
            print(f"  {cat_path}:{ln}: {msg}")
    else:
        print("  No syntax/tag issues in categories.txt")

    if cat_dups_exact:
        print("\nExact duplicate lines in categories.txt (line, first_seen_line, content):")
        for ln, first, content in cat_dups_exact:
            problems += 1
            print(f"  {cat_path}:{ln} duplicates line at {first}: {content.strip()}")

    if cat_dups_left:
        print("\nDuplicate left-side criteria in categories.txt (normalized criteria -> lines):")
        for left_norm, lines in cat_dups_left:
            problems += 1
            print(f"  {cat_path}: lines {lines} all have left criteria: '{left_norm}'")

    if sig_errors:
        print("\nErrors in signatures.txt:")
        for ln, msg in sig_errors:
            problems += 1
            print(f"  {sig_path}:{ln}: {msg}")
    else:
        print("  No syntax issues in signatures.txt")

    if sig_dups_exact:
        print("\nExact duplicate lines in signatures.txt (line, first_seen_line, content):")
        for ln, first, content in sig_dups_exact:
            problems += 1
            print(f"  {sig_path}:{ln} duplicates line at {first}: {content.strip()}")

    if sig_dups_left:
        print("\nDuplicate left-side criteria in signatures.txt (normalized criteria -> lines):")
        for left_norm, lines in sig_dups_left:
            problems += 1
            print(f"  {sig_path}: lines {lines} all have left criteria: '{left_norm}'")

    if problems:
        print(f"\nValidation finished: {problems} problem(s) found.", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nValidation finished: no problems found.")
        sys.exit(0)


if __name__ == "__main__":
    main()