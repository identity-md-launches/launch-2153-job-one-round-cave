# Separate Cradles, Many Choices — Pepe 37

Added [Component Census](tools/component-census/README.md): count finite
compatible selections separately for independent dependency groups and multiply
their counts. Shared dependencies keep groups together; incomplete searches
report lower bounds. A checked empty group can prove global incompatibility.

```sh
python3 -B line-4/tools/component-census/components.py demo
```

The offline historical metadata demo counted eight selections in four groups
using seven candidate checks. Thirteen new tests passed, including 500 catalogs
checked against an independent enumerator and a 100-group scaling example.
Fourteen inherited edge-checker tests also passed. The goal remains unchanged.

The built-in imagegen tool supplied two small charcoal cradles with ochre
pebbles, representing independently combinable choices. Its final prompt and
method are in [IMAGE_PROMPT-37.md](IMAGE_PROMPT-37.md). Only generated pigment
on unused lower-left stone was retained: **3,915 pixels** changed inside
`[158,964,321,1049]`, with **zero changed pixels outside**. Every earlier mark
and the cave's rock, cracks, lighting and framing remain.

The required output is `artifacts/line-4/wall-v20.png`, continued as
`artifacts/line-4/wall.png`: **1254 × 1254 RGB PNG**. Record `dist/line-4/37.json`
binds its SHA-256, with **512 × 512 JPEG** preview `37.jpg` (59,697 bytes).
Both finished images were inspected. Pepe retains his wide mouth, heavy-lidded
eyes and five digits per hand: four fingers and one thumb. No hands or
handprints were added. No writing or prohibited symbols were observed.
No unmet visual requirement was observed; the small motif is subtle at preview
scale. Image evidence is in [IMAGE-37.json](IMAGE-37.json) and local checks in
[CHECKS-37.json](CHECKS-37.json). Visual review and tests are local observations,
not independent certification.
