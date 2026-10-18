"""Keep only round 37's image-generated pigment on unused ancestral rock."""
import hashlib
import importlib.util
import json
from pathlib import Path


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    codec = module('png37', 'finish_wall22.py')
    jpeg = module('jpeg37', 'preview_jpeg27.py')
    ancestor = Path('artifacts/line-4/wall.png')
    output = Path('artifacts/line-4/wall-v20.png')
    records = Path('dist/line-4')
    old_hash = hashlib.sha256(ancestor.read_bytes()).hexdigest()
    assert old_hash == '38bcbc0c2c62781a574e454f491b5aea0a4d00f6aa993b862a557765dbce71c9'
    assert len(list(records.glob('[0-9][0-9].json'))) == 36
    assert json.loads((records/'36.json').read_text())['image'].endswith(old_hash)
    w, h, original = codec.read_png(ancestor)
    gw, gh, generated = codec.read_png(output)
    assert (w, h) == (gw, gh) == (1254, 1254)
    generated_sha = hashlib.sha256(output.read_bytes()).hexdigest()
    final = original[:]
    bounds = (158, 964, 321, 1049)
    for y in range(bounds[1], bounds[3]):
        for x in range(bounds[0], bounds[2]):
            at = 3*(y*w+x)
            r, g, b = generated[at:at+3]
            stones = any(((x-cx)/rx)**2 + ((y-cy)/ry)**2 < 1
                         for cx, cy, rx, ry in [(191,984,13,13), (217,981,14,14),
                                               (258,1018,14,14), (284,1014,15,15)])
            red = stones and r > g*1.4 and r > b*1.8 and r > 60
            arc = any(.42 < ((x-cx)/rx)**2 + ((y-cy)/ry)**2 < 1.35 and y > cy-2
                      for cx, cy, rx, ry in [(204,980,42,27), (271,1013,44,29)])
            charcoal = arc and r < 100 and g < 75 and b < 55
            if red or charcoal:
                final[at:at+3] = generated[at:at+3]
    changed = [i for i in range(w*h) if final[3*i:3*i+3] != original[3*i:3*i+3]]
    assert changed
    assert all(bounds[0] <= i%w < bounds[2] and bounds[1] <= i//w < bounds[3]
               for i in changed)
    sha = codec.write_png(output, w, h, final)
    assert codec.read_png(output)[2] == final
    ancestor.write_bytes(output.read_bytes())
    preview = jpeg.encode(jpeg.resize(final, w, h), 512, 512, quality=40)
    assert len(preview) < 100000
    (records/'37.jpg').write_bytes(preview)
    record = {'name': 'Separate Cradles, Many Choices',
              'image': 'https://api.imd.fun/artifacts/' + sha,
              'attributes': [
                  {'trait_type': 'Cave', 'value': 'Crystal'},
                  {'trait_type': 'Wall', 'value': 'Line 4'},
                  {'trait_type': 'Number', 'value': 37},
                  {'trait_type': 'Left behind', 'value': 'Component Census'},
                  {'trait_type': 'Meaning', 'value': 'Separate cradles hold choices that can be combined without conflict.'},
                  {'trait_type': 'One thing', 'value': 'Finite offline dependency resolution'}]}
    (records/'37.json').write_text(json.dumps(record, indent=2)+'\n')
    evidence = {'ancestor_sha256': old_hash, 'generated_sha256': generated_sha,
                'wall_sha256': sha, 'dimensions': [w,h], 'format': 'PNG', 'mode': 'RGB',
                'changed_pixels': len(changed), 'mark_region_xyxy': bounds,
                'changed_pixels_outside_mark_region': 0,
                'method': 'Retained only generated red-ochre stones and charcoal cradle arcs on unused lower-left rock; all other ancestral pixels identical.',
                'preview': {'path': 'dist/line-4/37.jpg', 'dimensions': [512,512],
                            'format': 'JPEG', 'bytes': len(preview)},
                'visual_review': 'Pending final PNG and JPEG inspection.',
                'unmet_visual_requirements': [],
                'limitations': 'Small motif is subtle at thumbnail scale; visual review is local, not independent certification.'}
    Path('line-4/IMAGE-37.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
