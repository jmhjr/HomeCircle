"""Render HomeCircle's original geometric icon; requires Pillow."""

from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SCALE = 4
image = Image.new("RGBA", (256 * SCALE, 256 * SCALE))
draw = ImageDraw.Draw(image)


def points(values):
    return [(x * SCALE, y * SCALE) for x, y in values]


def ellipse(box, fill):
    draw.ellipse(tuple(value * SCALE for value in box), fill=fill)


ellipse((8, 8, 248, 248), "#142b40")
draw.line(
    points([(55, 118), (128, 57), (201, 118)]),
    fill="#65dec5",
    width=12 * SCALE,
    joint="curve",
)
draw.line(
    points([(73, 107), (73, 192), (183, 192), (183, 107)]),
    fill="#65dec5",
    width=10 * SCALE,
)
for center, top in [(104, 128), (152, 128), (128, 152)]:
    ellipse((center - 10, top - 10, center + 10, top + 10), "#ffffff")
path = ROOT / "custom_components/homecircle/brand/icon.png"
path.parent.mkdir(parents=True, exist_ok=True)
image.resize((256, 256), Image.Resampling.LANCZOS).save(path, optimize=True)
print("Rendered original HomeCircle icon.")
