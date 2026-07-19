"""Turn a prepped portrait into a self-animating ASCII SVG.

    python scripts/make_ascii_svg.py data/portrait-prepped.png assets/bhanu-ascii.svg

Each row is clipped by a rect that animates from zero width to full width,
staggered top to bottom, so the portrait wipes in once and then freezes.
GitHub strips JavaScript and external CSS from READMEs, so all motion has to
live inside the SVG as SMIL.
"""

import os
import sys
import pathlib
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image

# Ramp runs sparse -> dense. The card background is dark and the glyphs are
# light, so character density reads as BRIGHTNESS: dense glyphs emit more light.
# That means bright parts of the photo take the dense end, not the sparse end.
RAMP = " .':;+=*csS#%@"
COLS = 58
SUBJECT_FLOOR = 0.16    # dimmest character the subject is allowed to use
GAMMA = 1.25            # >1 pushes dark mass down so the lit face carries the image
CARD_W = 400        # 400 + 460 (info card) = 860, matching the heatmap width
CHAR_ASPECT = 0.52              # monospace glyph width / height
BG = "#0d1117"
FG = "#d7e0ea"
ACCENT = "#39d353"
ROW_STAGGER = 0.026             # seconds between row reveals
ROW_DURATION = 0.42


def to_rows(img_path, cols=COLS):
    src = Image.open(img_path)
    rows = max(1, int(round(cols * (src.height / src.width) * CHAR_ASPECT)))
    small = src.resize((cols, rows), Image.LANCZOS)

    px = np.asarray(small.convert("L"), dtype=np.float32) / 255.0
    if "A" in small.getbands():
        mask = np.asarray(small.getchannel("A"), dtype=np.float32) / 255.0 > 0.45
    else:
        mask = px < 0.93          # no alpha: assume near-white is background

    if mask.sum() < 16:
        mask = np.ones_like(px, dtype=bool)

    # Normalise over the SUBJECT only. Including the blank background would peg
    # the top percentile at pure white and flatten every tone in the face.
    subj = px[mask]
    lo, hi = np.percentile(subj, 4), np.percentile(subj, 96)
    norm = np.clip((px - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    norm = norm ** GAMMA

    # Floor the subject above blank. Without this the darkest subject tones
    # (hair, suit) map to spaces and dissolve into the background, which erases
    # the silhouette and leaves only the lit patches floating.
    norm = SUBJECT_FLOOR + (1.0 - SUBJECT_FLOOR) * norm

    idx = (norm * (len(RAMP) - 1)).round().astype(int)
    idx[~mask] = 0                # background is the only true blank
    return ["".join(RAMP[i] for i in row) for row in idx]


def build_svg(rows, cols=COLS, width=CARD_W, static=False):
    char_w = width / cols
    font_size = char_w / 0.6          # monospace advance is ~0.6em
    line_h = char_w / CHAR_ASPECT     # keeps the glyph cell square-ish
    pad = 14
    height = len(rows) * line_h + pad * 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" '
        f'height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'role="img" aria-label="ASCII portrait of Bhanu Prasad Reddy">',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        f'<rect x="0.5" y="0.5" width="{width-1:.0f}" height="{height-1:.0f}" rx="10" '
        f'fill="none" stroke="{ACCENT}" stroke-opacity="0.18"/>',
    ]

    if not static:
        out.append("<defs>")
        for i in range(len(rows)):
            y = pad + i * line_h - line_h
            out.append(
                f'<clipPath id="r{i}"><rect x="0" y="{y:.2f}" width="0" height="{line_h*1.6:.2f}">'
                f'<animate attributeName="width" from="0" to="{width:.0f}" '
                f'dur="{ROW_DURATION}s" begin="{i*ROW_STAGGER:.3f}s" fill="freeze"/>'
                f"</rect></clipPath>"
            )
        out.append("</defs>")

    out.append(
        f'<g font-family="SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace" '
        f'font-size="{font_size:.2f}" fill="{FG}" xml:space="preserve">'
    )
    for i, row in enumerate(rows):
        clip = "" if static else f' clip-path="url(#r{i})"'
        y = pad + (i + 1) * line_h
        out.append(f'<text x="0" y="{y:.2f}"{clip}>{escape(row)}</text>')
    out.append("</g></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/portrait-prepped.png")
    dst = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "assets/bhanu-ascii.svg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    rows = to_rows(src)
    dst.write_text(build_svg(rows, static=bool(os.environ.get("STATIC"))), encoding="utf-8")
    print(f"wrote {dst} ({len(rows)} rows x {COLS} cols)")
