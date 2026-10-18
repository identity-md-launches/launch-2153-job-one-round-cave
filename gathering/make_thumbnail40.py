"""Resize the finished painting to the required 512 pixel JPEG with Blender."""
from pathlib import Path
import bpy

image = bpy.data.images.load(str(Path('artifacts/gathering/wall-v20.png').resolve()))
assert tuple(image.size) == (1254, 1254)
image.scale(512, 512)
image.file_format = 'JPEG'
image.filepath_raw = str(Path('dist/gathering/40.jpg').resolve())
image.save()
assert Path('dist/gathering/40.jpg').stat().st_size < 100000
print('Saved dist/gathering/40.jpg (512 x 512 JPEG)')
