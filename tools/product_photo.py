"""Turn a field photo into a catalogue shot like the 4 m³ container ones.

Needs its own environment (not in requirements.txt, the site doesn't use it):
    pip install "rembg[cpu]" opencv-python-headless pillow numpy

python tools/product_photo.py JOBS.json OUT_DIR [only/this.jpg ...]

Each job: {"src": path, "out": "slug/name.jpg", "rotate": optional degrees (overrides auto),
           "crop": optional [l, t, r, b] fractions applied before anything else}

Steps: crop -> straighten (auto from near-vertical edges of the product) -> cut the product
out (BiRefNet) -> lay it on pure white, centred with even margins -> 2000x1500 JPEG.
"""
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from rembg import new_session, remove

W, H = 2000, 1500
MARGIN = 0.07          # free space around the product, as a share of the canvas
MAX_TILT = 8.0         # never "correct" more than this; bigger tilts are the scene, not the camera

session = new_session('birefnet-general')


def tilt_angle(rgb, mask):
    """Angle (deg, counter-clockwise positive) that makes the product's vertical edges vertical."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 60, 160)
    # Only edges on the product itself, so trees and buildings don't vote.
    m = cv2.dilate((mask > 128).astype(np.uint8), np.ones((9, 9), np.uint8))
    edges = edges * m
    h = gray.shape[0]
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=60,
                            minLineLength=int(h * 0.08), maxLineGap=int(h * 0.01))
    if lines is None:
        return 0.0
    angles, weights = [], []
    for x1, y1, x2, y2 in np.asarray(lines).reshape(-1, 4):
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        a = math.degrees(math.atan2(dx, dy))  # 0 = perfectly vertical
        if a > 90:
            a -= 180
        if a < -90:
            a += 180
        if abs(a) <= 12:
            angles.append(a)
            weights.append(length)
    if len(angles) < 3:
        return 0.0
    order = np.argsort(angles)
    a = np.array(angles)[order]
    w = np.array(weights)[order]
    median = a[np.searchsorted(np.cumsum(w), w.sum() / 2)]
    return float(median) if 0.4 <= abs(median) <= MAX_TILT else 0.0


def remove_logo(img):
    """Paint out the green round RILA-SNM watermark that some Facebook photos carry."""
    a = np.asarray(img).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = ((g > r + 50) & (g > b + 30) & (g > 120)).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(green, 8)
    if n < 2:
        return img
    biggest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = stats[biggest, :4]
    # The badge is a disc: cover its bounding circle generously, white ring included.
    cx, cy, rad = x + w / 2, y + h / 2, max(w, h) * 0.62
    mask = np.zeros(green.shape, np.uint8)
    cv2.circle(mask, (int(cx), int(cy)), int(rad), 255, -1)
    out = cv2.inpaint(np.asarray(img)[..., ::-1].copy(), mask, 9, cv2.INPAINT_TELEA)
    return Image.fromarray(out[..., ::-1])


def cutout(img):
    rgba = remove(img, session=session, post_process_mask=True)
    return rgba.split()[-1]


def run(job, out_dir):
    img = ImageOps.exif_transpose(Image.open(job['src'])).convert('RGB')
    if job.get('crop'):
        l, t, r, b = job['crop']
        img = img.crop((int(l * img.width), int(t * img.height), int(r * img.width), int(b * img.height)))
    badge = job.get('badge')  # [cx, cy, r, horizon]: a watermark disc, and where the product's top edge runs through it
    if badge:
        cx, cy, rad, horizon = badge
        disc = np.zeros((img.height, img.width), np.uint8)
        cv2.circle(disc, (cx, cy), rad, 255, -1)
        if job.get('badge_rect'):  # parts of the badge sticking out of the circle
            x0, y0, x1, y1 = job['badge_rect']
            disc[y0:y1, x0:x1] = 255
        src = np.asarray(img)[..., ::-1].copy()
        # The badge above the edge is thrown away anyway; grey it out first so the
        # fill below can't drag its green down onto the product.
        sample = src[horizon + rad + 10:horizon + rad + 40, cx - 40:cx + 40].reshape(-1, 3)
        top = disc.copy()
        top[horizon:] = 0
        src[top > 0] = np.median(sample, axis=0)
        fill = disc.copy()
        fill[:horizon] = 0
        fill = cv2.dilate(fill, np.ones((7, 7), np.uint8))
        src = cv2.inpaint(src, fill, 15, cv2.INPAINT_TELEA)
        img = Image.fromarray(src[..., ::-1])
    elif job.get('logo'):
        img = remove_logo(img)

    alpha = cutout(img)
    if badge:
        # Above the product's edge the badge sat on the background: make sure it goes.
        a = np.asarray(alpha).copy()
        above = disc.copy()
        above[horizon:] = 0
        a[above > 0] = 0
        alpha = Image.fromarray(a)
    angle = job.get('rotate')
    if angle is None:
        angle = tilt_angle(np.asarray(img), np.asarray(alpha))
    if angle:
        # Rotate photo and mask together; PIL rotates counter-clockwise for positive angles.
        img = img.rotate(-angle, Image.BICUBIC, expand=True, fillcolor=(255, 255, 255))
        alpha = alpha.rotate(-angle, Image.BICUBIC, expand=True, fillcolor=0)

    # Clean the mask edge: drop faint haze, soften the step by a pixel.
    a = np.asarray(alpha).astype(np.float32)
    a = np.clip((a - 20) * (255 / 215), 0, 255).astype(np.uint8)
    # Drop specks: anything much smaller than the largest piece (group shots keep every item).
    n, labels, stats, _ = cv2.connectedComponentsWithStats((a > 40).astype(np.uint8), 8)
    if n > 2:
        areas = stats[1:, cv2.CC_STAT_AREA]
        small = np.where(areas < areas.max() * 0.01)[0] + 1
        a[np.isin(labels, small)] = 0
    alpha = Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.6))

    bbox = alpha.point(lambda v: 255 if v > 40 else 0).getbbox()
    if not bbox:
        raise RuntimeError('nothing left after cut-out')
    product = img.crop(bbox)
    pmask = alpha.crop(bbox)

    box_w, box_h = W * (1 - 2 * MARGIN), H * (1 - 2 * MARGIN)
    scale = min(box_w / product.width, box_h / product.height)
    size = (max(1, round(product.width * scale)), max(1, round(product.height * scale)))
    product = product.resize(size, Image.LANCZOS)
    pmask = pmask.resize(size, Image.LANCZOS)

    canvas = Image.new('RGB', (W, H), 'white')
    # Sit the product slightly low of centre, as a studio shot on a sweep would.
    x = (W - size[0]) // 2
    y = (H - size[1]) // 2 + int(H * 0.01)
    canvas.paste(product, (x, y), pmask)

    out = Path(out_dir) / job['out']
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, 'JPEG', quality=90, optimize=True, progressive=True)
    print(f"{job['out']}: tilt {angle:+.1f} deg, product {size[0]}x{size[1]}")


if __name__ == '__main__':
    jobs = json.loads(Path(sys.argv[1]).read_text('utf-8'))
    only = set(sys.argv[3:])
    for job in jobs:
        if only and job['out'] not in only:
            continue
        if not only and (Path(sys.argv[2]) / job['out']).exists():
            continue
        run(job, sys.argv[2])
