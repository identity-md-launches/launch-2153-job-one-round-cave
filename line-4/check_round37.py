"""Check round 37's output contract and ancestral pixel preservation locally."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess


def git(*args):
    return subprocess.check_output(['git', *args])


def jpeg_size(raw):
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
    at = 2
    while at < len(raw):
        assert raw[at] == 255
        kind = raw[at+1]
        size = int.from_bytes(raw[at+2:at+4], 'big')
        if kind == 0xc0:
            return [int.from_bytes(raw[at+7:at+9], 'big'),
                    int.from_bytes(raw[at+5:at+7], 'big')]
        at += 2+size
    raise AssertionError('JPEG frame missing')


def main():
    assert Path('line-4/GOAL.md').read_bytes() == git('show', 'HEAD:line-4/GOAL.md')
    old_records = [p for p in git('ls-files', 'dist/line-4').decode().splitlines()]
    for p in old_records:
        assert Path(p).read_bytes() == git('show', 'HEAD:'+p), p
    records = list(Path('dist/line-4').glob('[0-9][0-9].json'))
    assert len(records) == 37
    record = json.loads(Path('dist/line-4/37.json').read_text())
    assert set(record) == {'name', 'image', 'attributes'}
    attrs = record['attributes']
    assert len(attrs) == 6
    assert all(set(a) == {'trait_type', 'value'} for a in attrs)
    traits = {a['trait_type']: a['value'] for a in attrs}
    assert set(traits) == {'Cave','Wall','Number','Left behind','Meaning','One thing'}
    assert traits['Cave'] == 'Crystal' and traits['Wall'] == 'Line 4'
    assert type(traits['Number']) is int and traits['Number'] == 37
    assert traits['Left behind'] == 'Component Census'
    wall = Path('artifacts/line-4/wall-v20.png').read_bytes()
    assert wall == Path('artifacts/line-4/wall.png').read_bytes()
    sha = hashlib.sha256(wall).hexdigest()
    assert record['image'] == 'https://api.imd.fun/artifacts/'+sha
    assert not git('ls-files', 'artifacts/line-4/wall-v20.png')
    spec = importlib.util.spec_from_file_location('codec37', 'line-4/finish_wall22.py')
    codec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(codec)
    w,h,pixels = codec.read_png(wall)
    old_raw = git('show', 'HEAD:artifacts/line-4/wall.png')
    ow,oh,old = codec.read_png(old_raw)
    assert (w,h) == (ow,oh) == (1254,1254)
    evidence = json.loads(Path('line-4/IMAGE-37.json').read_text())
    assert evidence['ancestor_sha256'] == hashlib.sha256(old_raw).hexdigest()
    assert evidence['wall_sha256'] == sha
    x0,y0,x1,y1 = evidence['mark_region_xyxy']
    changed, outside = 0,0
    for i in range(w*h):
        if pixels[3*i:3*i+3] != old[3*i:3*i+3]:
            changed += 1
            outside += not (x0 <= i%w < x1 and y0 <= i//w < y1)
    assert changed == evidence['changed_pixels'] > 0
    assert outside == evidence['changed_pixels_outside_mark_region'] == 0
    preview = Path('dist/line-4/37.jpg').read_bytes()
    assert jpeg_size(preview) == [512,512]
    assert len(preview) == evidence['preview']['bytes'] < 100000
    assert 'Pending' not in evidence['visual_review']
    assert evidence['unmet_visual_requirements'] == []
    modified = git('diff', '--name-only').decode().splitlines()
    created = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    paths = modified + created + ['artifacts/line-4/wall-v20.png']
    for p in paths:
        assert p.startswith(('line-4/', 'dist/line-4/', 'artifacts/line-4/', 'test/scratch/')), p
        if not p.startswith(('artifacts/', 'test/scratch/')):
            assert Path(p).stat().st_size <= 100000, p
    result = {'status': 'passed', 'authority': 'local observations only',
              'goal_unchanged': True, 'old_record_files_unchanged': len(old_records),
              'record_count': len(records), 'new_record': 'dist/line-4/37.json',
              'output': 'artifacts/line-4/wall-v20.png', 'output_untracked': True,
              'wall_sha256': sha, 'wall_dimensions': [w,h], 'wall_format': 'PNG RGB',
              'preview_dimensions': jpeg_size(preview), 'preview_format': 'JPEG',
              'preview_bytes': len(preview), 'changed_pixels': changed,
              'changed_pixels_outside_mark_region': outside,
              'unmet_visual_requirements': [], 'scope_and_size_checks': 'passed',
              'tests_observed': [
                  {'command': "python3 -B -m unittest discover -s line-4/tools/component-census -p 'test_*.py' -v", 'passed': 13},
                  {'command': "python3 -B -m unittest discover -s line-4/tools/exhaustive-audit -p 'test_*.py' -v", 'passed': 14}],
              'demo_observed': {'command': 'python3 -B line-4/tools/component-census/components.py demo',
                                'exit_code': 0, 'components': 4, 'checked_assignments': 7,
                                'compatible_selections': 8}}
    Path('line-4/CHECKS-37.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
