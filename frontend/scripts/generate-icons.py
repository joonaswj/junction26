"""Generate the PWA / iOS home-screen icons from the brand colour.

Run from the frontend directory:  python3 scripts/generate-icons.py
Outputs PNGs into public/ (Vite copies them to dist/ on build).
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BRAND = (0, 122, 61)  # --brand in src/index.css
WHITE = (255, 255, 255)
PUBLIC = Path(__file__).resolve().parents[1] / "public"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def draw_icon(size: int, glyph_ratio: float) -> Image.Image:
    """Green square with a centred white S. glyph_ratio is the S height / size."""
    img = Image.new("RGB", (size, size), BRAND)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, int(size * glyph_ratio))
    # Anchor "mm" centres the glyph on its own bounding box, not the em box.
    draw.text((size / 2, size / 2), "S", font=font, fill=WHITE, anchor="mm")
    return img


def main() -> None:
    PUBLIC.mkdir(parents=True, exist_ok=True)

    # iOS applies its own rounded mask, so this must be full-bleed and opaque.
    draw_icon(180, 0.62).save(PUBLIC / "apple-touch-icon.png")

    # Manifest icons. "any" can be full-bleed; "maskable" needs the glyph inside
    # the 80% safe zone so Android's circular crop does not clip it.
    draw_icon(192, 0.62).save(PUBLIC / "icon-192.png")
    draw_icon(512, 0.62).save(PUBLIC / "icon-512.png")
    draw_icon(512, 0.46).save(PUBLIC / "icon-maskable-512.png")

    for name in (
        "apple-touch-icon.png",
        "icon-192.png",
        "icon-512.png",
        "icon-maskable-512.png",
    ):
        print(f"wrote public/{name}")


if __name__ == "__main__":
    main()
