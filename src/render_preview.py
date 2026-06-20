#!/usr/bin/env python3
"""
Render the TRMNL Liquid layouts locally so you can eyeball them before pasting
into TRMNL. For each layout it prepends shared.liquid (mirroring how TRMNL
prepends "Shared Markup"), renders with the computed data, and wraps the result
in the TRMNL HTML shell at the exact device size for that layout.

  python src/render_preview.py            # uses output/trmnl_data.json
  python src/render_preview.py --data output/trmnl_data.json

Output: preview/<layout>.html  (open in a browser; each is sized to the device)
"""
import argparse
import json
import os
import sys

from liquid import Environment

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
MARKUP = os.path.join(ROOT, "markup")
PREVIEW = os.path.join(ROOT, "preview")

# device pixel sizes per TRMNL layout
SIZES = {
    "full": (800, 480),
    "half_horizontal": (800, 240),
    "half_vertical": (400, 480),
    "quadrant": (400, 240),
}

SHELL = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://trmnl.com/css/latest/plugins.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
  /* preview-only: frame each render at the real device size, 1-bit look */
  body {{ background:#888; margin:0; padding:24px; font-family:Inter,Arial,sans-serif; }}
  .device {{ width:{w}px; height:{h}px; background:#fff; overflow:hidden;
            box-shadow:0 0 0 1px #000, 0 8px 24px rgba(0,0,0,.4); }}
  .caption {{ color:#fff; font:600 13px Inter,Arial; margin:0 0 8px; }}
</style>
</head>
<body class="environment trmnl">
  <p class="caption">{name} — {w}×{h}</p>
  <div class="device">{body}</div>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(ROOT, "output", "trmnl_data.json"))
    args = ap.parse_args()

    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)

    env = Environment()
    os.makedirs(PREVIEW, exist_ok=True)

    with open(os.path.join(MARKUP, "shared.liquid"), encoding="utf-8") as f:
        shared = f.read()

    for name, (w, h) in SIZES.items():
        with open(os.path.join(MARKUP, name + ".liquid"), encoding="utf-8") as f:
            layout = f.read()
        # TRMNL prepends Shared Markup to each view; mirror that here.
        template = env.from_string(shared + "\n" + layout)
        body = template.render(**data)
        html = SHELL.format(name=name, w=w, h=h, body=body)
        out = os.path.join(PREVIEW, name + ".html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("rendered", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
