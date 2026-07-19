"""Render the neofetch-style info card as a self-animating SVG.

    python scripts/make_info_card.py assets/info-card.svg
    STATIC=1 python scripts/make_info_card.py assets/info-card-static.svg

Edit ROWS below to change what the card says. Every claim here has to be
backed by cv.md -- this is a public hiring surface, not a wish list.
"""

import os
import sys
import pathlib
from xml.sax.saxutils import escape

TITLE_USER = "bhanu"
TITLE_HOST = "github"

ROWS = [
    ("Education", "Integrated M.Tech CSE · VIT · 2021–2026"),
    ("Role",      "Software Development Intern · Hyderabad"),
    ("Also",      "Core Java Developer Intern · Virtusa (remote)"),
    ("Focus",     "Backend & full stack · .NET · JVM"),
    ("Languages", "C# · Java · Python · SQL"),
    ("Backend",   "ASP.NET Core (.NET 10) · Spring Boot · REST"),
    ("Frontend",  "React 18 · HTML · CSS"),
    ("Data",      "SQL Server · MySQL · MongoDB"),
    ("Cloud",     "Azure · Azure DevOps · AWS · Docker"),
    ("AI / LLM",  "LangChain · offline LLMs · Azure AI-900"),
    ("Shipped",   "COI validation: 30 min → 2 min per document"),
    ("Building",  "Natural Language → SQL on offline LLMs"),
    ("Contact",   "bhanuprasas007@gmail.com"),
    ("Web",       "bhanuprasadhere.github.io"),
]

PALETTE = ["#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0",
           "#58a6ff", "#a371f7", "#d7e0ea"]

CARD_W = 460        # 400 (portrait) + 460 = 860, matching the heatmap width
PAD = 18
ROW_H = 21.5
KEY_X = PAD
VAL_X = PAD + 86
FONT = "SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace"
BG = "#0d1117"
KEY_C = "#39d353"
VAL_C = "#c9d1d9"
DIM_C = "#8b949e"
ACCENT = "#39d353"

STAGGER = 0.07
DURATION = 0.45


def build_svg(static=False):
    header_h = PAD + 34
    swatch_h = 30
    height = header_h + len(ROWS) * ROW_H + swatch_h + PAD

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{height:.0f}" '
        f'viewBox="0 0 {CARD_W} {height:.0f}" role="img" '
        f'aria-label="Profile summary card for Bhanu Prasad Reddy">',
        f'<rect width="100%" height="100%" rx="10" fill="{BG}"/>',
        f'<rect x="0.5" y="0.5" width="{CARD_W-1}" height="{height-1:.0f}" rx="10" '
        f'fill="none" stroke="{ACCENT}" stroke-opacity="0.18"/>',
        f'<g font-family="{FONT}" font-size="12.5">',
    ]

    def anim(i):
        if static:
            return "", ""
        begin = f"{i * STAGGER:.3f}s"
        a = (f'<animate attributeName="opacity" from="0" to="1" dur="{DURATION}s" '
             f'begin="{begin}" fill="freeze"/>'
             f'<animateTransform attributeName="transform" type="translate" '
             f'from="-8 0" to="0 0" dur="{DURATION}s" begin="{begin}" fill="freeze"/>')
        return ' opacity="0"', a

    # header: bhanu@github + rule
    op, a = anim(0)
    out.append(
        f'<g{op}>{a}'
        f'<text x="{KEY_X}" y="{PAD+14}" font-size="14.5" font-weight="bold" fill="{KEY_C}">'
        f'{TITLE_USER}<tspan fill="{DIM_C}">@</tspan>'
        f'<tspan fill="{KEY_C}">{TITLE_HOST}</tspan></text>'
        f'<text x="{KEY_X}" y="{PAD+29}" fill="{DIM_C}">{"─" * 46}</text>'
        f"</g>"
    )

    for i, (key, val) in enumerate(ROWS):
        op, a = anim(i + 1)
        y = header_h + (i + 1) * ROW_H - 6
        out.append(
            f'<g{op}>{a}'
            f'<text x="{KEY_X}" y="{y:.1f}" fill="{KEY_C}">{escape(key)}</text>'
            f'<text x="{VAL_X}" y="{y:.1f}" fill="{VAL_C}">{escape(val)}</text>'
            f"</g>"
        )

    # neofetch-style colour swatch
    op, a = anim(len(ROWS) + 1)
    sw_y = header_h + len(ROWS) * ROW_H + 8
    blocks = "".join(
        f'<rect x="{KEY_X + n*22}" y="{sw_y}" width="18" height="12" rx="2" fill="{c}"/>'
        for n, c in enumerate(PALETTE)
    )
    out.append(f"<g{op}>{a}{blocks}</g>")

    out.append("</g></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    dst = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "assets/info-card.svg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(build_svg(static=bool(os.environ.get("STATIC"))), encoding="utf-8")
    print(f"wrote {dst} ({len(ROWS)} rows)")
