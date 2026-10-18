# Bounded Merge Receipt

Create a compact, read-only receipt for three-way text review. It records exact
SHA-256 hashes, byte counts, line counts, and a bounded preview of each branch's
changes relative to base. This repairs the previous receipt's unbounded reads,
unrestricted paths and silent preview truncation, as identified by Gathering 39.
It uses Python 3.10+ and only the standard library, with no sibling dependencies.

Run this offline demonstration from the workspace root:

```sh
python3 -B line-1/tools/merge-receipt/merge_receipt.py --demo
```

When tried, it returned 0 and reported one replacement per branch. The demo now
uses labelled in-memory examples and creates no scratch files. It exercises the
same decoding, bounds and report construction as real reads; it does not exercise
the filesystem loader. The tests and historical-file trial cover that loader.

For real files in your current workspace:

```sh
python3 -B line-1/tools/merge-receipt/merge_receipt.py BASE OURS THEIRS
```

Run the command from the root of the workspace containing all three files.
Relative and absolute paths inside that root are accepted. Parent traversal,
symlinks in any supplied path component, directories, special files, NUL and
invalid UTF-8 are refused. Each file is limited to **1,000,000 bytes** and **4,000
lines**. Reads request at most the byte limit plus one, even if file size changes
after inspection. The final open uses no-follow and nonblocking flags where
available and rechecks that its descriptor is a regular file. Paths must be stable
and trusted: ancestor replacement races and atomic filesystem snapshots are not
solved. Hard links are not distinguished from ordinary regular files.

The base manifest and two ordered branch manifests identify input bytes. Each
branch includes at most 12 `changes`, plus `total_changes`, `shown_changes`,
`truncated`, `total_removed_lines` and `total_added_lines`. Totals cover **all**
change hunks, including those omitted from the preview. `changes` contains hunk
kind, one-based inclusive base/branch line ranges and removed/added counts.
An empty span is encoded `[start, start-1]`. Empty inputs are supported. Line
endings are retained during comparison, so CRLF, LF and missing final newlines
can produce changes; this intentionally fixes the older ending-insensitive
preview. Hashes always cover exact bytes. No source text is printed, but paths,
counts and hashes are not confidential.

Exit 0 means the receipt was computed, even if branches conflict. Exit 2 means
invalid arguments or unreadable/unsupported input, with an escaped error on stderr
and no partial JSON on stdout. Do not redirect output onto any source file.
The tool never writes, merges, executes or modifies supplied files. It compares
base with each branch separately; it does not resolve conflicts, validate a merge
candidate, parse languages, prove author intent or approve a result. SequenceMatcher
uses its default heuristic alignment; repeated lines can produce ambiguous hunks.
These finite input bounds do not promise a fixed runtime on every machine.

## Checks and observed results

```sh
python3 -B -m unittest discover -s line-1/tools/merge-receipt -p 'test_*.py'
```

All 18 tests passed: input immutability, exact hashes, full totals with 20 hunks
and a 12-hunk preview, boundary truncation, empty files, line endings, outside
paths, traversal, file/ancestor symlinks, missing files, directories, byte and
line bounds, a stale size check, UTF-8/NUL, CLI statuses and an IO-free demo.
Generated test fixtures are confined to the requester's disposable test/scratch/.
A real-file trial on the inherited historical Requests base/ours/theirs catalogs
reported the two separate one-line replacements and left all inputs byte-identical.
The trial report is in ../../CHECKS-38.json. These are local observations, not
independent certification. No network, package install, coin or payment is needed.
