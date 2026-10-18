# Search Evaluate

Measure whether ranked offline searches retrieve passages you expected to find.
Provide a small set of query judgments: each target names a source and an exact
inclusive line range. The report keeps verified hits, found and missed targets,
per-query metrics and macro averages. Python 3.9+ standard library only; no
installation. Keep the adjacent Search Batch, Evidence Search and Corpus
Freshness folders. No network, environment lookup or file writes at runtime.

From the repository root, one command shows it working:

```sh
python3 -B line-3/tools/search-evaluate/evaluate.py demo
```

When tried, the inherited historical ZTO decimals target (`zto.md:6-6`) and
ZTO/IMD pool tick-spacing target (`pool.md:6-6`) were both found at rank one.
An intentionally unrelated `glacial orchid` query missed a labelled IMD passage.
All three macro metrics were 2/3. The deliberately bad query demonstrates a
failed retrieval, not missing token metadata. These sources retain the ancestor's
historical RPC and assignment-reference qualifications; this is no new chain
observation or current price. Nine focused tests passed.

For your own collection, save this UTF-8 JSON inside the workspace:

```json
{
  "format": "evidence-search-judgments/v1",
  "queries": [{
    "id": "decimals",
    "query": "ZTO token decimals",
    "limit": 3,
    "require_all": true,
    "targets": [{"path": "zto.md", "line_start": 6, "line_end": 6}]
  }]
}
```

Then run `python3 -B line-3/tools/search-evaluate/evaluate.py run YOUR_CORPUS YOUR_JUDGMENTS.json`.
Use Evidence Search's corpus rules: UTF-8 `.md`, `.txt`, `.rst` documents within
the current workspace. Paths are relative to the corpus; no hidden components,
traversal or symlink inputs. A missing source or nonexistent target line is an
input error, not a retrieval miss. Targets should be minimal sufficient ranges;
a target spanning more than one result window may never be found.

A hit finds a target only when its path matches and it **contains the entire
labelled range**. Merely overlapping a label does not count. Targets can overlap;
identical labels within one query are rejected. A hit containing several targets
counts once toward precision. Metrics are:

- `target_recall`: found targets divided by supplied targets.
- `labelled_hit_precision`: returned hits containing at least one target divided
  by actual returned hit count (not the requested limit); zero for no hits.
- `reciprocal_rank`: reciprocal of the first hit's rank that contains a target,
  or zero if none. Macro values are unweighted query averages.

Unlabelled hits are not established irrelevant. Metrics describe only the
caller's labels and the bounded top results; they do not judge factual truth,
semantic relevance or completeness. Bad or stale judgments produce misleading
metrics. Source hashes and exact excerpts support review of each result.
The report's corpus hash binds sorted paths and source hashes, not authorship.
All queries use the same indexed snapshot. Every selected source is reread,
and a final full-corpus freshness audit rejects observed edits/additions/removals.
Keep the corpus static: these reads are not an atomic filesystem snapshot.

Limits: 64 KiB judgment input, 1–32 queries, 128 total targets, 1–50 hits per
query, and 4096 query characters. Other corpus and passage limits come from
Evidence Search. Duplicate JSON keys, nonfinite numbers, invalid types, duplicate
IDs and invalid target ranges fail closed. JSON reports go to stdout; exit 0
means evaluation completed, including misses. Exit 2 means invalid input or
I/O/freshness failure, with JSON on stderr and no partial stdout report. Misses
are intentionally separate from execution failure so callers can set their own
review threshold.

Run tests with `python3 -B line-3/tools/search-evaluate/test_evaluate.py -v`.
They cover rank/limit effects, precision deduplication, containment vs overlap,
real historical sources, missing/symlink sources, invalid plans, CRLF citations,
inert document instructions, determinism, input immutability and stale-corpus
rejection. Test fixtures are created only in disposable `test/scratch/`.
