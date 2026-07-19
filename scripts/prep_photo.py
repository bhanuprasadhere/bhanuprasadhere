"""Prep a headshot for ASCII conversion.

    python scripts/prep_photo.py <input.jpg> [output.png]

Cuts the background out, boosts local contrast, composites onto white.
Background removal uses rembg when it is installed; otherwise it falls back
to OpenCV GrabCut seeded from the centre of the frame, which is good enough
for a centred headshot and needs no extra dependency.
"""

import sys
import pathlib

import cv2
import numpy as np

TARGET_LONG_EDGE = 900


def _alpha_rembg(bgr):
    # rembg can import cleanly and still fail at call time when no onnxruntime
    # backend is installed, so the whole path is guarded, not just the import.
    try:
        from rembg import remove
        rgba = remove(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        return np.asarray(rgba)[:, :, 3]
    except Exception as exc:
        print(f"rembg unavailable ({type(exc).__name__}); falling back to GrabCut")
        return None


def _alpha_grabcut(bgr):
    # ponytail: GrabCut seeded with a centred rectangle. Fine for a headshot;
    # swap in rembg (pip install rembg) if the subject is off-centre or busy.
    h, w = bgr.shape[:2]
    rect = (int(w * 0.08), int(h * 0.04), int(w * 0.84), int(h * 0.94))
    mask = np.zeros((h, w), np.uint8)
    cv2.grabCut(bgr, mask, rect, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), 6, cv2.GC_INIT_WITH_RECT)
    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    return cv2.GaussianBlur(fg, (7, 7), 0)


SHOULDER_KEEP = 0.45   # how much below the neck to keep, as a fraction of head height


def crop_to_head(bgra):
    """Crop to head-and-shoulders using the cut-out silhouette.

    ASCII resolution is scarce: at 80 columns a full-torso frame spends most of
    its rows on a suit jacket and leaves the face too coarse to read.

    OpenCV 5 removed the Haar cascade API, so instead of pulling an ONNX face
    model this reads the shape we already have. In a head-and-shoulders cutout
    the silhouette width narrows at the neck and widens again at the shoulders,
    so the neck is the minimum row width between the head and the shoulder
    flare. ponytail: geometric heuristic, no face model. Swap in
    cv2.FaceDetectorYN if a photo ever defeats it.
    """
    alpha = bgra[:, :, 3]
    widths = (alpha > 16).sum(axis=1).astype(np.float32)
    if widths.max() < 8:
        return bgra

    solid = np.where(widths > widths.max() * 0.06)[0]
    if len(solid) < 20:
        return bgra
    top, bot = int(solid[0]), int(solid[-1])
    span = bot - top

    # Look for the neck in the upper-middle band; below that is torso.
    lo, hi = top + int(span * 0.18), top + int(span * 0.62)
    if hi - lo < 5:
        return bgra
    neck = lo + int(np.argmin(widths[lo:hi]))

    head_h = neck - top
    y0 = max(0, top - int(head_h * 0.12))
    y1 = min(bgra.shape[0], neck + int(head_h * SHOULDER_KEEP))

    # Width from the upper head only - lower rows already contain shoulders.
    band = alpha[top:top + int(head_h * 0.6)] > 16
    cols = np.where(band.any(axis=0))[0]
    if len(cols) < 4:
        return bgra[y0:y1]
    cx = (cols[0] + cols[-1]) / 2
    half = (cols[-1] - cols[0]) * 0.92
    x0 = int(max(0, cx - half))
    x1 = int(min(bgra.shape[1], cx + half))

    print(f"head rows {top}-{neck} (neck at {neck}) -> crop ({x0},{y0})-({x1},{y1})")
    return bgra[y0:y1, x0:x1]


def prep(src, dst):
    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    if bgr is None:
        raise SystemExit(f"cannot read image: {src}")

    scale = TARGET_LONG_EDGE / max(bgr.shape[:2])
    if scale < 1:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    alpha = _alpha_rembg(bgr)
    if alpha is None:
        alpha = _alpha_grabcut(bgr)
    alpha = cv2.resize(alpha, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR)

    # Local contrast so mid-tones survive the brightness->character quantisation.
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    # Mild clip limit only. Aggressive CLAHE equalises every local region to
    # similar contrast, which flattens the global light/dark structure that the
    # ASCII ramp depends on and turns the portrait into uniform texture.
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(lab[:, :, 0])
    bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Composite onto white for the colour channels, but KEEP the alpha channel:
    # the ASCII step needs to know which pixels are background so it can leave
    # them blank instead of painting them as solid characters.
    a = (alpha.astype(np.float32) / 255.0)[:, :, None]
    flat = (bgr.astype(np.float32) * a + 255.0 * (1 - a)).astype(np.uint8)
    bgra = np.dstack([flat, alpha])

    ys, xs = np.where(alpha > 16)
    if len(ys) > 40:
        pad = 12
        bgra = bgra[max(0, ys.min() - pad):ys.max() + pad,
                    max(0, xs.min() - pad):xs.max() + pad]

    bgra = crop_to_head(bgra)

    cv2.imwrite(str(dst), bgra)
    print(f"wrote {dst} ({bgra.shape[1]}x{bgra.shape[0]}, alpha preserved)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path("data/portrait-prepped.png")
    dst.parent.mkdir(parents=True, exist_ok=True)
    prep(src, dst)
