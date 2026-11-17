"""Smaller WebP copies of uploaded photos, made on first use and kept on disk.

The originals are up to 2000 px wide; a product card shows them at ~320 px.
Copies live under MEDIA_ROOT/thumbs/<width>/<original path>.webp, so whatever
serves /media/ serves them too, and deleting the folder only costs a rebuild.
"""
import logging
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

THUMBS_DIR = 'thumbs'
QUALITY = 82


def thumbnail_url(name, width):
    """URL of a `width`-px-wide WebP copy of the media file `name`, or None if it can't be made."""
    media_root = Path(settings.MEDIA_ROOT)
    source = media_root / name
    relative = Path(THUMBS_DIR) / str(width) / f'{name}.webp'
    target = media_root / relative
    try:
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            target.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as image:
                image = ImageOps.exif_transpose(image)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
                image.thumbnail((width, width * 4), Image.LANCZOS)
                # Write beside the target and swap in, so a half-written file is never served.
                partial = target.with_name(target.name + '.part')
                image.save(partial, 'WEBP', quality=QUALITY, method=5)
                partial.replace(target)
    except (OSError, ValueError):
        logger.warning('No thumbnail for %s at %s px', name, width, exc_info=True)
        return None
    return settings.MEDIA_URL + relative.as_posix()


def srcset(name, original_width, widths):
    """`srcset` value: the WebP copies narrower than the original, then the original itself."""
    candidates = []
    for width in sorted(widths):
        if original_width and width >= original_width:
            break
        url = thumbnail_url(name, width)
        if url:
            candidates.append(f'{url} {width}w')
    if not candidates or not original_width:
        return ''
    candidates.append(f'{settings.MEDIA_URL}{name} {original_width}w')
    return ', '.join(candidates)
