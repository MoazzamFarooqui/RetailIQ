#!/usr/bin/env python3
"""
Regenerate RetailIQ favicon raster assets from the black brand mark.

The mark (identical to client/public/favicon.svg) is:
  - a 64x64 rounded rect (rx=14) filled #0c1917
  - three vertical bars with round caps (white, stroke-width 9, stroke-linecap round):
        M16 44 V20
        M32 44 V12
        M48 44 V28
  - a filled white dot centered at (32, 44) radius 6

Renders each size with 4x supersampling for crisp edges, matching SVG coords
via pillow's 0..(size) pixel space.
"""

from PIL import Image, ImageDraw
from pathlib import Path

PUBLIC = Path(r"C:\Users\USER\Desktop\RetailIQ\client\public")
SS = 4  # supersample factor


def draw_mark(size_px: int) -> Image.Image:
    """Render the brand mark at size_px * SS, downsampled to size_px."""
    s = size_px * SS
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Scale from the 64x64 SVG viewBox into the pixel canvas.
    def sc(x):
        return x * s / 64.0

    # Background rounded square (rx=14 in a 64 box).
    d.rounded_rectangle(
        (0, 0, s - 1, s - 1), radius=sc(14), fill=(12, 25, 23, 255)
    )

    # Bars. In SVG, a V command with stroke-linecap=round draws a uniform-width
    # segment ending in a half-circle of radius w/2 centered on the endpoint.
    # Pillow has no round caps, so draw the full-width line between the endpoints
    # and add a disk of radius r = w/2 centered on each endpoint.
    w = sc(9)
    r = w / 2.0
    bars = [((16, 44), (16, 20)), ((32, 44), (32, 12)), ((48, 44), (48, 28))]
    for (x, y1), (x2, y2) in bars:
        cxp = sc(x)
        top, bottom = sc(min(y1, y2)), sc(max(y1, y2))
        d.line(
            [(cxp, top), (cxp, bottom)],
            fill=(255, 255, 255, 255),
            width=int(round(w)),
        )
        d.ellipse(
            [(cxp - r, top - r), (cxp + r, top + r)], fill=(255, 255, 255, 255)
        )
        d.ellipse(
            [(cxp - r, bottom - r), (cxp + r, bottom + r)],
            fill=(255, 255, 255, 255),
        )

    if SS > 1:
        img = img.resize((size_px, size_px), Image.LANCZOS)
    return img


def save_ico(path: Path, sizes=(16, 32, 48)) -> None:
    frames = [draw_mark(sz) for sz in sizes]
    frames[0].save(
        path,
        format="ICO",
        sizes=[(sz, sz) for sz in sizes],
        append_images=frames[1:],
    )


def main():
    targets = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "favicon-48x48.png": 48,
        "apple-touch-icon.png": 180,
        "icon-192.png": 192,
        "icon-512.png": 512,
    }
    for name, size in targets.items():
        draw_mark(size).save(PUBLIC / name, format="PNG")
        print(f"wrote {name} ({size}x{size})")
    save_ico(PUBLIC / "favicon.ico")
    print("wrote favicon.ico (16/32/48)")


if __name__ == "__main__":
    main()

