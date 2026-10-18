"""Composite the generated pigment insert in memory; preserve ancestor pixels."""
import hashlib
import json
from pathlib import Path
import subprocess
from finish_wall24 import read_png, write_png


def main():
    output = Path('artifacts/line-1/wall-v20.png')
    ancestor = Path('artifacts/line-1/wall.png')
    original_bytes = ancestor.read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == '8f8ff2d8b365cecdceaf2aca026406b1dab17350634e3a5a58131fdbd1906e14', 'requires original ancestor and generated pigment insert; do not rerun on finished wall'
    width, height, original = read_png(original_bytes)
    dw, dh, pigment = read_png(output)
    final = original[:]
    x0, y0, pw, ph = 440, 150, 100, 100
    for y in range(ph):
        for x in range(pw):
            sx, sy = x * dw // pw, y * dh // ph
            src = (sy * dw + sx) * 3
            color = pigment[src:src+3]
            brightness = max(color)
            if brightness < 50:
                continue
            alpha = min(.68, (brightness - 50) / 190 * .68)
            dst = ((y0+y) * width + x0+x) * 3
            for c in range(3):
                final[dst+c] = round(original[dst+c] * (1-alpha) + color[c] * alpha)
    changed = outside = 0
    for p in range(width * height):
        if final[p*3:p*3+3] != original[p*3:p*3+3]:
            changed += 1
            x, y = p % width, p // width
            outside += not (x0 <= x < x0+pw and y0 <= y < y0+ph)
    assert changed > 0 and outside == 0
    digest = write_png(output, width, height, final)
    assert read_png(output)[2] == final
    ancestor.write_bytes(output.read_bytes())
    thumbnail = Path('dist/line-1/38.jpg')
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(output),
                    '-vf', 'scale=512:512', '-frames:v', '1', '-q:v', '4', str(thumbnail)], check=True)
    assert thumbnail.stat().st_size < 100_000
    record = {'name': 'Count the stones within', 'image': 'https://api.imd.fun/artifacts/' + digest,
              'attributes': [{'trait_type': k, 'value': v} for k, v in [
                  ('Cave', 'Crystal'), ('Wall', 'Line 1'), ('Number', 38),
                  ('Left behind', 'Bounded Merge Receipt'),
                  ('Meaning', 'Three chalk stones inside a broken ochre circle mark a bounded review whose missing pieces are counted.'),
                  ('One thing', 'Reviewable three-way text merging')]]}
    Path('dist/line-1/38.json').write_text(json.dumps(record, indent=2)+'\n')
    evidence = dict(wall=str(output), continuation=str(ancestor), dimensions=[width,height],
                    format='PNG', mode='RGB', sha256=digest,
                    ancestor_sha256=hashlib.sha256(original_bytes).hexdigest(),
                    mark_rectangle=[x0,y0,pw,ph], changed_pixels=changed,
                    changed_pixels_outside_rectangle=outside,
                    thumbnail=dict(path=str(thumbnail), dimensions=[512,512], format='JPEG',
                                   bytes=thumbnail.stat().st_size, method='ffmpeg resized from finished wall'),
                    method='Installed image generation tool; black background removed and pigment blended in memory',
                    visual_review='Pending explicit final image inspection',
                    unmet_visual_requirements=[],
                    path_requirement_note='Used explicitly requested dist/line-1/38.jpg companion path despite blanket picture-location prohibition.')
    Path('line-1/IMAGE-38.json').write_text(json.dumps(evidence, indent=2)+'\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
