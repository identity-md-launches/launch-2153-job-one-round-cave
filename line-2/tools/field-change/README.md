# Field Change

Compare named packed storage fields between **two proven Ethereum states**,
with both endpoint headers linked to **one caller-supplied trusted tip hash**.
It reports signed field deltas, changes confined to unnamed bits, storage
existence, account code-hash changes, and changes to the overall storage
commitment. This helps a worker distinguish an unchanged sampled field from
an unchanged contract state.

From the repository root, Python 3.9+ and only the standard library:

```sh
python3 -B line-2/tools/field-change/field_change.py demo
```

## What happened when tried

The offline demo verified the inherited **real historical ZTO/IMD Uniswap v4
pool** proofs at Ethereum mainnet blocks **26,212,390** and **26,212,393**,
connected by three parent links spanning 36 seconds. All five named fields
were unchanged: `sqrtPriceX96 = 20794297345123442418062648917057`, `tick = 111407`,
both directional protocol fees zero, and `lpFee = 12500`. No unnamed bits
changed. PoolManager's overall storage root changed, so other state may have
changed despite the sampled word being equal. Its account code hash stayed
equal. These are historical raw-state observations, not a current price or
swap quote. The stored checkpoint came from RPC; it is **not independently
consensus-authenticated**. No live network request is needed.

Historical sources are https://ethereum-rpc.publicnode.com (first proof and
headers) and https://eth.drpc.org (tip proof), as recorded by the unchanged
ancestor tools. No new capture, installation, dependency, coin or account is
needed. `line-2/TRIAL-40.json` contains the actual demo output.

## Use your own evidence

Supply a supported `header-chain/1` file (oldest header first), two
`state-witness/1` proofs, the contract address and a reviewed
[`storage-fields/1` layout](../storage-fields/README.md). That layout must
request exactly the storage slots proven by **both** witnesses. It supports
1–64 words and 1–32 nonoverlapping fields per word; offsets count from the
least significant bit. Signedness is explicit. Names must be globally unique.
`requireUnusedZero: true` rejects nonzero unnamed bits at either endpoint;
`false` reports their values and XOR without interpreting them.

Review the layout for **both** endpoint contract versions, then retain its
fingerprint separately:

```sh
python3 -B line-2/tools/field-change/field_change.py fingerprint \
  line-2/tools/storage-fields/pool-layout.json
```

For the inherited pool layout it prints
`6d3bbc017f81f66d785f895fe1cffaa65c9ec4351f8043fb92b93e3ed331fd0a`.
The normalized layout is serialized as ASCII JSON with sorted object keys and
no spaces, then SHA-256 hashed, using the same normalization as Storage
Fields. Slot spelling and field order normalize; names, offsets, widths,
signedness and unused-bit requirements remain committed. A fingerprint does
not establish the correctness of a layout.

The full historical comparison, with explicit trust inputs:

```sh
python3 -B line-2/tools/field-change/field_change.py compare \
  line-2/tools/header-chain/examples/zto-header-chain.json \
  line-2/tools/state-witness/examples/zto-pool-mainnet.json \
  line-2/tools/ancestry-diff/examples/pool-tip.json \
  line-2/tools/storage-fields/pool-layout.json \
  --tip-hash 0xead51f4e385140de3b2010a5b4c96106e8bf27fdb836246e57e18ad5df545a33 \
  --address 0x000000000004444c5dc75cB358380D2e3dE08A90 \
  --layout-sha256 0x6d3bbc017f81f66d785f895fe1cffaa65c9ec4351f8043fb92b93e3ed331fd0a
```

For your own decision, independently authenticate the actual tip hash and
chain, and supply your separately reviewed fingerprint and requested address.
The tool never adopts those expectations from witness labels. A changed layout
fails before proof checking. All parent links and both complete proofs must
verify before any fields are decoded or any success output is printed.
Accounts must exist at both endpoints. A proven absent storage word in an
existing account decodes to zero and retains `exists: false`.

Output is `field-change/1` JSON. Each slot has endpoint raw words, existence,
unnamed bits, and named fields with endpoint raw bits, signed/unsigned decimal
values, a change flag and a signed decimal delta. Deltas use unbounded integer
subtraction, never uint256 wrapping. The summary lists changed names and slots
with unnamed-bit changes. Overall storage commitment and code-hash change
flags are separate from sampled-word and named-field change flags. Account
native balances are **PoolManager-wide ETH wei**, never this pool's ZTO balance.

Exit **0** means the requested checks succeeded; **1** prints error JSON to
stderr with no success output; argparse syntax errors exit **2**. Fingerprint
mode is explicitly `verified: false`; it checks no state proof. File reads
are bounded (chain 256 KiB / 64 headers, each proof 1 MB, layout 64 KiB), use
strict JSON and reject paths/symlinks resolving outside the current working
directory. They are not atomic filesystem snapshots. Keep the current working
directory at the intended workspace root.

## Checks and boundaries

```sh
python3 -B -m unittest discover -s line-2/tools/field-change -p 'test_*.py' -v
```

All **21 focused tests passed**. They cover real pool evidence and multiple
real ZTO slots, actual valid but explicitly synthetic trie proofs for signed
boundaries and changed fields, 256-bit signed deltas, unnamed-bit changes,
zero-slot absence, absent accounts, code-hash changes, both endpoints' unused
bits, input immutability, altered layout pins/ancestry/proofs/address/slots,
metadata isolation, strict bounded workspace loading and atomic CLI rejection.
Synthetic proofs are only test scaffolding, never demo observations.

Ancestry Diff, Header Chain, State Diff, Header Anchor, Storage Fields and State
Witness are reused unchanged. Keep those sibling folders beside this one.
No new cryptography is implemented. Only supported header/proof schemas work.

A proof commits raw bits; field semantics and layout remain caller assumptions.
Code-hash changes are reported, not rejected, since the comparison still proves
the raw words. Review both versions; even an unchanged proxy's code hash does
not prove unchanged implementation or layout. Equal endpoints can hide
intermediate changes. A changed storage root does not enumerate unrequested
slots. This checks no consensus, finality, execution validity, token semantics,
events, transfers, profit or present freshness. It reads no clock, environment,
keys or wallets, writes no files, makes no network calls, and never signs,
sends, pays, posts or deploys.
