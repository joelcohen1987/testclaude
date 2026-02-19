"""Run this once to generate the extension icons. Requires Pillow."""

from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 48, 128]

for size in SIZES:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Blue rounded rectangle background
    margin = max(1, size // 16)
    radius = max(2, size // 6)
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=radius,
        fill="#1976d2",
    )

    # White "R" letter
    font_size = int(size * 0.6)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("Arial Bold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), "R", font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2
    ty = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), "R", fill="white", font=font)

    img.save(f"icon{size}.png")
    print(f"Created icon{size}.png")
