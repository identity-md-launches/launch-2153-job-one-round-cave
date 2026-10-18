# Component Census

Count compatible selections in a finite offline dependency catalog by separating
independent dependency groups. A worker with several unrelated dependency trees
can inspect each group and multiply its choices without enumerating the full
cross-product. Python 3.9+ and the standard library are sufficient.

Run from the repository root:

```sh
python3 -B line-4/tools/component-census/components.py demo
```

I ran this command against the inherited historical Requests release metadata.
The demo explicitly uses standalone roots for certifi, charset-normalizer, idna
and urllib3 `<2`. It found **four independent components**, exhausted **seven
local candidates** instead of eight combined candidates, and counted **eight
compatible selections**. Requests is not reachable from these demonstration
roots and is listed as ignored. The original catalog with its Requests root
still forms one component: it needs 27 candidates and has eight selections.
The snapshots and [source provenance](../offline-resolver/examples/sources.json)
are inherited; no new metadata was fetched. These are illustrative requirements
over real historical metadata, not an observed installation or current release
recommendation.

The scaling test has 100 independent two-release roots: it checks 200 candidates
and returns exactly `2**100` selections. That test is synthetic; it demonstrates
the benefit when the input genuinely separates.

For your own explicit workspace-local catalog:

```sh
python3 -B line-4/tools/component-census/components.py path/to/catalog.json --max-assignments 10000
```

Keep the adjacent `exhaustive-audit/` and `offline-resolver/` folders. Their
numeric version grammar, canonical names, bounded JSON loader and iterative edge
checker are reused. Catalogs have `packages` and `roots`, mandatory dependency
maps per release, one-to-four-component numeric versions, and conjunctive
comparison constraints. See [Offline Resolver](../offline-resolver/README.md)
for the exact schema. Duplicate keys, unsupported syntax, files over 1 MB and
paths escaping the current workspace are rejected. Runtime only reads explicit
inputs and these tool modules, and prints JSON. It uses no network, package
execution, installation, environment variables, configuration or file writes.

The partition starts at every root and follows dependencies from **every**
release, including releases excluded by root constraints. It connects each
source and target in an undirected graph. Shared dependencies merge components;
missing targets remain in their component. Every possible reachable assignment
is contained in this overapproximation. No edge can connect two resulting
components, so every combination of valid local selections is a valid global
selection, and every global selection splits uniquely into local selections.
Unreachable catalog packages cannot join components through incoming edges.
This is conservative: excluded release edges can merge groups unnecessarily.

Within each component, roots are mandatory and nonroots may be absent. A
candidate counts only if the edge checker accepts it and its selected packages
equal its actual root closure. Optional packages, abandoned dependencies,
cycles and unreachable choices therefore do not duplicate the count. Only one
local witness is stored per component. The assembled global witness is checked
again against the entire catalog.

The budget is **global**, from 1 to 1,000,000 candidate checks (default 10,000).
Components and releases are ordered deterministically. Finishing exactly at the
budget is conclusive; empty root domains require zero candidate checks.

| Result | Meaning |
| --- | --- |
| `complete`, `count_kind: exact` | The global selection count is proved in this finite catalog. |
| `inconclusive`, `count_kind: lower-bound` | The budget ended. The count may increase; zero does not establish incompatibility. |
| `classification: unsatisfiable` | At least one completely checked component has zero choices. |
| `classification: unique` | The exact global count is one. |
| `classification: multiple` | At least two selections are established, possibly during partial search. |
| `classification: unknown` | Partial search has not established two choices or an exact count. |

A fully checked empty component proves the global count is zero even when other
components remain incomplete. In that case the global status is `complete`,
`all_components_complete` is false, and `empty_component_index` identifies the
zero factor. Every component retains its own honest search status and count
kind. Otherwise the product of local observed counts is a lower bound; an
unvisited component contributes zero. A global witness is present only when
every component has a checked local witness. JSON null means none is available.

Exit 0 means an exact count, including an exact zero; exit 3 means inconclusive;
exit 2 means invalid input. Counts concern this finite numeric metadata model.
They do not establish installability, platform/interpreter compatibility,
artifact availability, metadata trust, security or publisher identity. Omitted
releases can change the answer. The SHA-256 binds normalized input, not truth.
The implementation shares parsing and edge checking with inherited tools, so
shared defects remain possible. Search is exponential inside a component; the
budget does not bound parsing, graph memory, output size or wall-clock time.
Splitting can cost more than flat enumeration for tiny or already impossible
catalogs. Both theoretical candidate totals are included for comparison.

Checks run:

```sh
python3 -B -m unittest discover -s line-4/tools/component-census -p 'test_*.py' -v
```

All **13 tests passed**, including 500 seeded catalogs compared with an
independent raw-edge subset enumerator, global budget cutoffs, exact boundaries,
empty-factor proofs, shared dependencies, conservative excluded-release edges,
cycles, missing targets, optional absence, immutable inputs, numeric aliases,
combined-witness rejection, bounded loading and CLI statuses. Scratch input
files live only in `test/scratch/`. These are local checks, not certification.
