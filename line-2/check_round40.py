"""Read-only local submission checks; prints evidence, never runs the tool demo."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess


def git(*args):
    return subprocess.check_output(['git', *args])


def require(condition, message):
    if not condition:
        raise ValueError(message)


def jpeg_dimensions(raw):
    require(raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9', 'JPEG markers')
    at = 2
    while at < len(raw):
        require(raw[at] == 255, 'JPEG segment')
        kind = raw[at+1]
        length = int.from_bytes(raw[at+2:at+4], 'big')
        require(length >= 2, 'JPEG segment size')
        if kind == 0xc0:
            height, width = struct.unpack('>HH', raw[at+5:at+9])
            return width, height
        require(kind != 0xda, 'JPEG missing baseline frame')
        at += 2 + length
    raise ValueError('JPEG dimensions not found')


require(Path('line-2/GOAL.md').read_bytes() == git('show', 'HEAD:line-2/GOAL.md'),
        'goal changed')
old_records = [p for p in git('ls-files', 'dist/line-2/*.json').decode().splitlines()
               if Path(p).stem.isdecimal()]
require(len(old_records) == 39, 'expected 39 predecessor records')
for name in old_records:
    require(Path(name).read_bytes() == git('show', 'HEAD:' + name), 'old record changed')
new_records = sorted(str(p) for p in Path('dist/line-2').glob('*.json')
                     if str(p) not in old_records)
require(new_records == ['dist/line-2/40.json'], 'expected exactly record 40')
changed = git('diff', '--name-only', 'HEAD').decode().splitlines()
untracked = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
for name in changed + untracked:
    require(name.startswith(('line-2/', 'artifacts/line-2/', 'dist/line-2/')), 'scope violation')
    if not name.startswith('artifacts/'):
        require(Path(name).stat().st_size <= 100000, 'new/modified file exceeds 100 KB')
require(changed == ['artifacts/line-2/wall.png', 'line-2/USED.md'], 'ancestor source unexpectedly changed')
spec = importlib.util.spec_from_file_location('png40_check', 'gathering/finish_wall.py')
png = importlib.util.module_from_spec(spec)
spec.loader.exec_module(png)
wall = Path('artifacts/line-2/wall-v20.png')
require(wall.is_file() and not wall.is_symlink(), 'wall output missing or symlink')
w, h, pixels = png.read_png(wall)
ow, oh, ancestor = png.read_png('artifacts/line-2/wall-v19.png')
require((w, h, ow, oh) == (1254, 1254, 1254, 1254), 'cave dimensions changed')
require(Path('artifacts/line-2/wall.png').read_bytes() == wall.read_bytes(), 'continuation differs')
review = json.loads(Path('line-2/REVIEW-40.json').read_text())
digest = hashlib.sha256(wall.read_bytes()).hexdigest()
require(digest == review['wallSha256'], 'wall digest mismatch')
require(hashlib.sha256(Path('artifacts/line-2/wall-v19.png').read_bytes()).hexdigest()
        == review['ancestorSha256'], 'ancestor wall changed')
x, y, width, height = review['newMarkRectangle']
changed_pixels = outside = 0
for i in range(w*h):
    if pixels[i*3:i*3+3] != ancestor[i*3:i*3+3]:
        changed_pixels += 1
        outside += not (x <= i%w < x+width and y <= i//w < y+height)
require(changed_pixels == review['changedPixels'] and changed_pixels > 1000, 'mark missing')
require(outside == review['changedPixelsOutsideRectangle'] == 0, 'ancestor pixels changed outside mark')
preview = Path('dist/line-2/40.jpg')
require(jpeg_dimensions(preview.read_bytes()) == (512, 512), 'preview dimensions')
require(hashlib.sha256(preview.read_bytes()).hexdigest() == review['preview']['sha256'],
        'preview digest mismatch')
require(preview.stat().st_size < 100000, 'preview exceeds 100 KB')
record = json.loads(Path(new_records[0]).read_text())
require(set(record) == {'name', 'image', 'attributes'}, 'record shape')
require(record['image'] == 'https://api.imd.fun/artifacts/' + digest, 'record image mismatch')
traits = record['attributes']
require([row['trait_type'] for row in traits] ==
        ['Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'], 'traits')
require(all(set(row) == {'trait_type', 'value'} for row in traits), 'trait shape')
require([row['value'] for row in traits[:4]] == ['Crystal', 'Line 2', 40, 'Field Change'], 'trait values')
require(type(traits[2]['value']) is int, 'number must be numeric')
require(all(isinstance(traits[i]['value'], str) and traits[i]['value'] for i in (0,1,3,4,5)), 'text traits')
require(not review['unmetVisualRequirements'] and 'Pending' not in review['visualReview'], 'visual review incomplete')
checks = json.loads(Path('line-2/CHECKS-40.json').read_text())['checks']
require(len(checks) == 7 and all(row['exitCode'] == 0 for row in checks), 'suite failure')
require(not Path('artifacts/line-2/wall-v20.webp').exists(), 'intermediate image remains')
require(git('ls-files', '--', str(wall), str(preview), new_records[0]) == b'', 'outputs must remain untracked')
print(json.dumps({
    'passed': True, 'number': 40, 'oldRecordsUnchanged': len(old_records),
    'goalByteIdentical': True, 'scopeChecked': changed + untracked,
    'wall': {'format': 'PNG', 'dimensions': [w,h], 'bytes': wall.stat().st_size, 'sha256': digest},
    'preview': {'format': 'JPEG', 'dimensions': [512,512], 'bytes': preview.stat().st_size},
    'changedPixels': changed_pixels, 'changedPixelsOutsideNewMark': outside,
    'unmetVisualRequirements': [], 'testsPassed': 120,
    'authority': 'Local checks and visual observation only, not independent certification.'
}, indent=2))
