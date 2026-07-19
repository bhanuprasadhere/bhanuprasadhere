"""Render data/contributions.json as a self-animating heatmap SVG.

    python scripts/render_heatmap_svg.py assets/contrib-heatmap.svg

Cells fade in on a diagonal sweep (top-left to bottom-right), once, then
freeze. Width is pinned to 860 so the portrait (370) and info card (490)
line up underneath it.
"""

import json
import os
import pathlib
import sys
from datetime import date

WIDTH = 860
PAD = 14
GUTTER = 30          # left day-label column
TOP = 26             # month-label strip
FOOTER = 22
WEEKS = 53
GAP_RATIO = 0.22

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
BG = "#0d1117"
DIM = "#8b949e"
ACCENT = "#39d353"
FONT = "SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace"

DIAG_STEP = 0.012    # seconds per diagonal band
FADE = 0.35
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def level_for(day):
    """Prefer GitHub's own level; fall back to bucketing the raw count."""
    lvl = day.get("level")
    if lvl is None:
        c = day["count"]
        lvl = 0 if c == 0 else 1 if c < 3 else 2 if c < 6 else 3 if c < 10 else 4
    # Level 5 is our own "exceptional day" band, above GitHub's 0-4.
    if lvl >= 4 and day["count"] >= 12:
        lvl = 5
    return min(lvl, len(PALETTE) - 1)


def build_svg(data, static=False):
    days = data["days"]
    pitch = (WIDTH - GUTTER - PAD * 2) / WEEKS
    cell = pitch * (1 - GAP_RATIO)
    grid_h = pitch * 7
    height = TOP + grid_h + FOOTER + PAD

    first = date.fromisoformat(days[0]["date"])
    offset = (first.weekday() + 1) % 7      # GitHub weeks start on Sunday

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height:.0f}" '
        f'viewBox="0 0 {WIDTH} {height:.0f}" role="img" '
        f'aria-label="GitHub contribution heatmap: {data["total"]} contributions in the last year">',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        f'<rect x="0.5" y="0.5" width="{WIDTH-1}" height="{height-1:.0f}" rx="10" '
        f'fill="none" stroke="{ACCENT}" stroke-opacity="0.18"/>',
        f'<g font-family="{FONT}" font-size="9.5" fill="{DIM}">',
    ]

    # month labels
    seen = set()
    for i, day in enumerate(days):
        col = (i + offset) // 7
        d = date.fromisoformat(day["date"])
        if d.day <= 7 and d.month not in seen and col < WEEKS:
            seen.add(d.month)
            x = PAD + GUTTER + col * pitch
            out.append(f'<text x="{x:.1f}" y="{TOP-8:.0f}">{MONTHS[d.month-1]}</text>')

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = TOP + row * pitch + cell * 0.8
        out.append(f'<text x="{PAD}" y="{y:.1f}">{label}</text>')

    out.append("</g><g>")
    for i, day in enumerate(days):
        col = (i + offset) // 7
        row = (i + offset) % 7
        if col >= WEEKS:
            continue
        x = PAD + GUTTER + col * pitch
        y = TOP + row * pitch
        fill = PALETTE[level_for(day)]
        rect = (f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell:.2f}" height="{cell:.2f}" '
                f'rx="2" fill="{fill}"')
        if static:
            out.append(rect + "/>")
        else:
            begin = (col + row) * DIAG_STEP
            out.append(
                rect + ' opacity="0">'
                f'<animate attributeName="opacity" from="0" to="1" dur="{FADE}s" '
                f'begin="{begin:.3f}s" fill="freeze"/></rect>'
            )
    out.append("</g>")

    # footer: total on the left, legend on the right
    fy = TOP + grid_h + 16
    out.append(
        f'<g font-family="{FONT}" font-size="10.5">'
        f'<text x="{PAD+GUTTER}" y="{fy:.0f}" fill="{DIM}">'
        f'<tspan fill="{ACCENT}" font-weight="bold">{data["total"]}</tspan>'
        f' contributions in the last year</text>'
    )
    lx = WIDTH - PAD - 12 - len(PALETTE) * 14
    out.append(f'<text x="{lx-30:.0f}" y="{fy:.0f}" fill="{DIM}">less</text>')
    for n, c in enumerate(PALETTE):
        out.append(f'<rect x="{lx + n*14:.0f}" y="{fy-9:.0f}" width="10" height="10" rx="2" fill="{c}"/>')
    out.append(f'<text x="{lx + len(PALETTE)*14 + 2:.0f}" y="{fy:.0f}" fill="{DIM}">more</text></g>')

    out.append("</svg>")
    return "\n".join(out)


def demo():
    """Self-check: geometry stays inside the canvas and every cell is placed."""
    days = [{"date": d, "count": 0, "level": 0} for d in
            (date.fromordinal(date(2025, 1, 5).toordinal() + n).isoformat() for n in range(371))]
    svg = build_svg({"days": days, "total": 0}, static=True)
    assert svg.count("<rect") == 371 + 2 + len(PALETTE), svg.count("<rect")
    pitch = (WIDTH - GUTTER - PAD * 2) / WEEKS
    assert PAD + GUTTER + (WEEKS - 1) * pitch + pitch <= WIDTH, "grid overflows canvas"
    assert '"860"' in svg
    print("demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
        raise SystemExit(0)
    data = json.loads(pathlib.Path("data/contributions.json").read_text(encoding="utf-8"))
    dst = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "assets/contrib-heatmap.svg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(build_svg(data, static=bool(os.environ.get("STATIC"))), encoding="utf-8")
    print(f"wrote {dst} ({len(data['days'])} days)")
