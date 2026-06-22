#!/usr/bin/env python3
"""
Render the TRMNL Liquid layouts locally so you can eyeball them before pasting
into TRMNL. For each layout it prepends shared.liquid (mirroring how TRMNL
prepends "Shared Markup"), renders with the computed data, and wraps the result
in the *real* TRMNL platform structure (verified on TRMNL X):

    body.trmnl.environment
      .screen.screen--v2.screen--4bit
        .view--<layout>            (full) or .mashup--… with .view--<layout> slots
          <plugin layout: .layout.layout--col > .x-canvas>

We deliberately do NOT create our own .screen/.view or pin pixel sizes — that is
exactly what broke earlier renders (see TRMNL_X_Start/readmefirst.md). The body
is set to the TRMNL X panel size (1872x1404) and screen--v2 handles the scaling
via --pixel-ratio, just like the device.

  python src/render_preview.py            # uses output/trmnl_data.json
  python src/render_preview.py --data output/trmnl_data.json

Output: preview/<layout>.html  (open in a browser)
"""
import argparse
import json
import os

from liquid import Environment

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
MARKUP = os.path.join(ROOT, "markup")
PREVIEW = os.path.join(ROOT, "preview")

# An empty sibling slot so mashups show our layout in a realistic neighbour
# context without rendering the plugin four times.
EMPTY = '<div class="view view--{view}"><div class="layout layout--col">' \
        '<div class="x-canvas" style="display:grid;place-items:center;' \
        'border:2px dashed #000;color:#000;font:600 14px Inter,Arial">(other plugin)' \
        '</div></div></div>'


def slot(view, body):
    return f'<div class="view view--{view}">{body}</div>'


def screen_inner(name, body):
    """Wrap the rendered plugin body in the platform view/mashup for `name`."""
    if name == "full":
        return slot("full", body)
    if name == "half_horizontal":  # stacked top/bottom
        return ('<div class="mashup mashup--1Tx1B">'
                + slot("half_horizontal", body)
                + EMPTY.format(view="half_horizontal") + '</div>')
    if name == "half_vertical":  # side by side
        return ('<div class="mashup mashup--1Lx1R">'
                + slot("half_vertical", body)
                + EMPTY.format(view="half_vertical") + '</div>')
    if name == "quadrant":  # 2x2 grid, our group top-left
        return ('<div class="mashup mashup--2x2">'
                + slot("quadrant", body)
                + EMPTY.format(view="quadrant") * 3 + '</div>')
    raise ValueError(name)


SHELL = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://trmnl.com/css/3.1.1/plugins.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>html, body {{ width:1872px; height:1404px; margin:0; overflow:hidden; }}</style>
</head>
<body class="trmnl environment">
  <div class="screen screen--v2 screen--4bit">{inner}</div>
</body>
</html>
"""

LAYOUTS = ("full", "half_horizontal", "half_vertical", "quadrant")


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

    for name in LAYOUTS:
        with open(os.path.join(MARKUP, name + ".liquid"), encoding="utf-8") as f:
            layout = f.read()
        # TRMNL prepends Shared Markup to each view; mirror that here.
        template = env.from_string(shared + "\n" + layout)
        body = template.render(**data)
        html = SHELL.format(inner=screen_inner(name, body))
        out = os.path.join(PREVIEW, name + ".html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print("rendered", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
