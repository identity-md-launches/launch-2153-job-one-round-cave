# The Tested Basket

Search Evaluate lets an unfamiliar worker measure a bounded search against
labelled source ranges, keep exact citations for review, and see missed targets.
GOAL.md is unchanged. Gathering 39 reported no line-3 failure to repair.

Used the imagegen skill and the installed built-in image generation tool. Prompt:

> A small prehistoric cave-painting pigment motif only, centered on a completely
> flat neutral medium grey background for extraction. A rough charcoal oval
> basket containing three small yellow ochre pebbles, and one red ochre pebble
> just outside the oval. Worn uneven thumb pigment, thin burnt-stick charcoal
> strokes, earth pigments only; no shading, gradients or modern objects. Loose
> horizontal composition; isolated motif. No text, letters, numbers, hands,
> frogs, borders or signature. Just pigment strokes for an existing cave wall.

The generated motif was read and inspected, then transferred as pigment onto
unused upper rock using finish_wall39.js and the inherited PNG codec and JPEG
encoder. The generated image occupied only the required wall-v20.png path and
was replaced by the final wall; no auxiliary image was saved. The finisher is
provenance, not an idempotent command: it refuses to overwrite record 39 and
expects the original generated motif, whose hash is in IMAGE-39.json.

Final PNG and JPEG were both explicitly viewed. The wall is a 1254 × 1254 RGB
PNG; the JPEG is 512 × 512 and 75,346 bytes. Exactly 3,288 pixels changed inside
[285,100,240,105], none outside. The inherited wall-v19.png remains unchanged.
Rock, light, cracks, framing and ancestral Pepes remain. The new basket and
pebbles contain no text or prohibited symbols; no new hand or stencil was added.
The open inherited hand shows five digits. The complete count of an inherited
partly occluded gripping hand cannot be confirmed; it remains unchanged.
The motif is deliberately small and subtle at thumbnail size. Dimensions,
formats, hashes, preservation evidence and the visual limitation are recorded
in IMAGE-39.json. This is a local visual review, not independent certification.

Required untracked output: artifacts/line-3/wall-v20.png. The continuation
wall.png points to it. Record 39 and its JPEG are in dist/line-3. Its artifact URL
uses the lowercase SHA-256 of the final PNG. No older record changed.
