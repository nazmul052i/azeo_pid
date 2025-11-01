import os
from PIL import Image
import io
import cairosvg

# Input SVG you want to use as your base icon (you can switch to another)
ICON_NAME = "tune.svg"

# Paths
ROOT = os.path.dirname(__file__)
SRC = os.path.join(ROOT, "qrc", "icons", ICON_NAME)
DST = os.path.join(ROOT, "qrc", "icons", "app.ico")

# Sizes for multi-resolution ICO (Windows-friendly)
SIZES = [16, 32, 48, 64, 128, 256]

def svg_to_png_bytes(svg_path: str, size: int) -> bytes:
    """Render SVG to PNG bytes using cairosvg."""
    return cairosvg.svg2png(url=svg_path, output_width=size, output_height=size)

def main():
    if not os.path.exists(SRC):
        raise FileNotFoundError(f"Source SVG not found: {SRC}")

    pngs = []
    for s in SIZES:
        data = svg_to_png_bytes(SRC, s)
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        pngs.append(img)

    # Save multi-size ICO
    pngs[0].save(DST, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"✅ Created multi-resolution icon: {DST}")

if __name__ == "__main__":
    main()
