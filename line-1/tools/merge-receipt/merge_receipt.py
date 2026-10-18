#!/usr/bin/env python3
"""Emit a bounded, read-only receipt for three-way text review."""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

LIMIT = 1_000_000
MAX_LINES = 4_000
PREVIEW = 12


def snapshot_data(data, label):
    if len(data) > LIMIT:
        raise ValueError("input exceeds 1,000,000 bytes")
    text = data.decode("utf-8")
    if "\0" in text:
        raise ValueError("NUL is not supported")
    lines = text.splitlines(keepends=True)
    if len(lines) > MAX_LINES:
        raise ValueError("input exceeds 4,000 lines")
    return {
        "path": str(label), "bytes": len(data), "lines": len(lines),
        "sha256": hashlib.sha256(data).hexdigest(), "lines_data": lines,
    }


def workspace_path(path):
    root = Path.cwd().resolve()
    supplied = Path(path)
    if ".." in supplied.parts:
        raise ValueError("parent traversal is not supported")
    candidate = supplied if supplied.is_absolute() else root / supplied
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        raise ValueError("input must be inside the current workspace") from None
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlinks are not supported")
    return candidate


def snapshot(path):
    candidate = workspace_path(path)
    # Reject special files before open; nonblocking/no-follow also protect the
    # final component on platforms offering those flags. Ancestor races remain
    # outside this stable-workspace reader's contract.
    if not stat.S_ISREG(candidate.stat().st_mode):
        raise ValueError("input must be a regular file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(candidate, flags)
    with os.fdopen(fd, "rb") as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("input must be a regular file")
        if info.st_size > LIMIT:
            raise ValueError("input exceeds 1,000,000 bytes")
        data = handle.read(LIMIT + 1)
    return snapshot_data(data, path)


def changes(base, branch):
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, base, branch).get_opcodes():
        if tag != "equal":
            rows.append({"kind": tag, "base": [i1 + 1, i2], "branch": [j1 + 1, j2],
                         "removed": i2 - i1, "added": j2 - j1})
    return rows


def from_snapshots(items):
    if len(items) != 3:
        raise ValueError("exactly three snapshots are required")
    def manifest(item):
        return {k: v for k, v in item.items() if k != "lines_data"}
    result = {"base": manifest(items[0]), "branches": []}
    for item in items[1:]:
        rows = changes(items[0]["lines_data"], item["lines_data"])
        result["branches"].append({
            **manifest(item), "changes": rows[:PREVIEW],
            "total_changes": len(rows), "shown_changes": min(len(rows), PREVIEW),
            "truncated": len(rows) > PREVIEW,
            "total_removed_lines": sum(row["removed"] for row in rows),
            "total_added_lines": sum(row["added"] for row in rows),
        })
    return result


def receipt(paths):
    paths = list(paths)
    if len(paths) != 3:
        raise ValueError("exactly three input paths are required")
    return from_snapshots([snapshot(p) for p in paths])


def demo():
    # No scratch files or external inputs: use the same decoding and reporting
    # functions as real reads, with explicitly labelled synthetic inputs.
    samples = (("demo:base", b"one\ntwo\nthree\n"),
               ("demo:ours", b"one\ntwo ours\nthree\n"),
               ("demo:theirs", b"one\ntwo\nthree theirs\n"))
    return from_snapshots([snapshot_data(data, label) for label, data in samples])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="workspace files BASE OURS THEIRS")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    if args.demo and args.paths:
        parser.error("--demo cannot be combined with input paths")
    if not args.demo and len(args.paths) != 3:
        parser.error("provide BASE OURS THEIRS, or use --demo")
    try:
        result = demo() if args.demo else receipt(args.paths)
    except (OSError, ValueError) as error:
        print("merge-receipt: " + ascii(str(error)), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
