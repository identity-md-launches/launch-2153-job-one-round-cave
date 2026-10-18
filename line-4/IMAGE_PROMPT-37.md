# Round 37 wall edit

Built-in `image_gen.imagegen`, edit mode. The sole reference and edit target was
the inherited `artifacts/line-4/wall.png`, 1254 × 1254 RGB PNG, SHA-256
`38bcbc0c2c62781a574e454f491b5aea0a4d00f6aa993b862a557765dbce71c9`.

Prompt:

> Use case: precise-object-edit. Edit this ancestral prehistoric cave painting.
> Preserve the complete 1254x1254 square wall, rock texture, cracks, warm torch
> lighting, framing, every existing mark and especially the existing Pepe frog
> unchanged. Add only a very small earth-pigment motif on the unused rock in the
> lower-left area centered at pixel (270,790), entirely inside x=208..330,
> y=740..825. The new motif is two separate small worn charcoal open cradles,
> each cradling two little red ochre pebbles. They symbolize independent groups
> of compatible choices. Handmade burnt-stick lines, uneven worn pigment, bare
> rock showing through, match ancestral marks. Do not alter anything outside
> this tiny addition. No extra frog, no new hands or handprints, no letters,
> numbers, captions, signatures, logos, watermarks, borders, frames, photographs,
> 3D, political or hateful symbols. Keep original square dimensions.

The image tool placed the motif lower than the requested coordinates, on unused
rock. That placement was accepted after inspection. The finishing helper retains
only its red and charcoal pigment inside `[158,964,321,1049]`, restoring every
other pixel directly from the ancestor. The generated image was transferred from
the tool's returned bytes into the required output, without reading its external
cache. No extra image was saved in the workspace. The final PNG, continuation
wall and required 512-pixel JPEG are the only images written.

Review step: inspect both finished PNG and JPEG and record dimensions, formats,
preservation evidence, hand counts and any unmet visual requirements in
`IMAGE-37.json` before finishing.
