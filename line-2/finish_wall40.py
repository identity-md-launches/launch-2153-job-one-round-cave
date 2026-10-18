"""One-shot pigment composition of the generated draft onto ancestor 39.

The installed image tool supplies the drawing; this helper preserves the actual
rock and ancestor marks by copying every pixel outside a bare-rock rectangle.
Run only on the original generated draft, before record 40 exists.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('png40', 'gathering/finish_wall.py')
png = importlib.util.module_from_spec(spec)
spec.loader.exec_module(png)
old = Path('artifacts/line-2/wall-v19.png')
out = Path('artifacts/line-2/wall-v20.png')
ancestor_sha = hashlib.sha256(old.read_bytes()).hexdigest()
assert ancestor_sha == 'd7ab661233a3828e3fc3b2001cff35d4bb08ac227bee99eb056b0e145eb9367d'
assert not Path('dist/line-2/40.json').exists(), 'do not apply twice'
w, h, ancestor = png.read_png(old)
dw, dh, draft = png.read_png(out)
draft_sha = hashlib.sha256(out.read_bytes()).hexdigest()
assert (w, h, dw, dh) == (1254, 1254, 1024, 1024)
final = ancestor[:]
rect = (1035, 310, 125, 85)
sx, sy, sw, sh = 190, 350, 670, 350
palette = {'red': (149, 49, 26), 'chalk': (207, 186, 143), 'charcoal': (42, 30, 20)}
for y in range(rect[3]):
    for x in range(rect[2]):
        selected = []
        for dy in range(sh*y//rect[3], sh*(y+1)//rect[3]):
            for dx in range(sw*x//rect[2], sw*(x+1)//rect[2]):
                xx, yy = sx+dx, sy+dy
                i = (yy*dw+xx)*3
                r, g, b = draft[i:i+3]
                if r > 1.7*g and r > 2*b and g < 125:
                    selected.append(palette['red'])
                elif r > 185 and g > 185 and b > 170 and yy > 425:
                    selected.append(palette['chalk'])
                elif 480 < xx < 530 and r < 85 and g < 85 and b < 85:
                    selected.append(palette['charcoal'])
        if selected:
            target = ((rect[1]+y)*w+rect[0]+x)*3
            samples = ((sh*(y+1)//rect[3]-sh*y//rect[3]) *
                       (sw*(x+1)//rect[2]-sw*x//rect[2]))
            alpha = min(.78, len(selected)/samples * .78)
            for c in range(3):
                pigment = sum(row[c] for row in selected)/len(selected)
                final[target+c] = round(ancestor[target+c]*(1-alpha) + pigment*alpha)
# Wear the new pigment using deterministic fine-scale gaps and the rock grain.
# This affects only the new drawing, never any inherited mark.
for y in range(rect[1], rect[1]+rect[3]):
    for x in range(rect[0], rect[0]+rect[2]):
        i = (y*w+x)*3
        noise = int.from_bytes(hashlib.sha256(f'{x},{y}'.encode()).digest()[:2], 'big') / 65535
        strength = 0 if noise < .16 else .3 + .7*noise
        for c in range(3):
            final[i+c] = round(ancestor[i+c] + (final[i+c]-ancestor[i+c])*strength)
changed = [i for i in range(w*h) if ancestor[3*i:3*i+3] != final[3*i:3*i+3]]
assert len(changed) > 1000
outside = sum(not (rect[0] <= i%w < rect[0]+rect[2] and
                   rect[1] <= i//w < rect[1]+rect[3]) for i in changed)
assert outside == 0
digest = png.write_png(out, w, h, final)
wall = Path('artifacts/line-2/wall.png')
assert wall.is_symlink() and wall.readlink() == Path('wall-v19.png')
wall.unlink()
wall.symlink_to('wall-v20.png')
rgba = bytearray()
for y in range(512):
    ya, yb = y*h//512, (y+1)*h//512
    for x in range(512):
        xa, xb = x*w//512, (x+1)*w//512
        count = (yb-ya)*(xb-xa)
        for c in range(3):
            rgba.append(round(sum(final[(yy*w+xx)*3+c]
                                  for yy in range(ya,yb) for xx in range(xa,xb))/count))
        rgba.append(255)
subprocess.run(['node', '-e',
    "const fs=require('fs');const encode=require('./line-3/tools/corpus-change-receipt/vendor/jpeg-js/lib/encoder.js');"
    "const result=encode({data:fs.readFileSync(0),width:512,height:512},78);"
    "if(result.data.length>100000)throw Error('JPEG too large');"
    "fs.writeFileSync('dist/line-2/40.jpg',result.data);"], input=rgba, check=True)
review = {
    'round': 40, 'ancestorSha256': ancestor_sha, 'generatedDraftSha256': draft_sha,
    'wallSha256': digest,
    'wall': {'path': str(out), 'format': 'PNG', 'channels': 'RGB',
             'dimensions': [w,h], 'bytes': out.stat().st_size},
    'preview': {'path': 'dist/line-2/40.jpg', 'format': 'JPEG',
                'dimensions': [512,512], 'bytes': Path('dist/line-2/40.jpg').stat().st_size,
                'sha256': hashlib.sha256(Path('dist/line-2/40.jpg').read_bytes()).hexdigest()},
    'newMarkRectangle': list(rect), 'changedPixels': len(changed),
    'changedPixelsOutsideRectangle': outside,
    'method': 'Installed image tool generated a pigment drawing. Only its pigment mask was reduced and blended with a fixed earth palette onto bare ancestor rock. All source rock and shading were discarded. No ancestor image was regenerated.',
    'visualReview': 'Pending explicit full-wall and JPEG inspection.',
    'unmetVisualRequirements': [],
    'deliveryNote': 'The explicitly required beside-record JPEG is the sole new image outside artifacts/. The generated intermediate WebP was removed; its replacement PNG draft was overwritten by the finished full wall.'
}
Path('line-2/REVIEW-40.json').write_text(json.dumps(review, indent=2)+'\n')
record = {'name': 'The Opened Seeds', 'image': 'https://api.imd.fun/artifacts/'+digest,
          'attributes': [
              {'trait_type': 'Cave', 'value': 'Crystal'},
              {'trait_type': 'Wall', 'value': 'Line 2'},
              {'trait_type': 'Number', 'value': 40},
              {'trait_type': 'Left behind', 'value': 'Field Change'},
              {'trait_type': 'Meaning', 'value': 'Two ochre seeds reveal their pale contents for a careful comparison.'},
              {'trait_type': 'One thing', 'value': 'Verify Ethereum account and storage proofs against trusted state roots'}]}
Path('dist/line-2/40.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(review, indent=2))
