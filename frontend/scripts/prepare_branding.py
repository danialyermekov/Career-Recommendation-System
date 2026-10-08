"""Export the supplied raster artwork without redrawing it (requires Pillow).

Usage: python prepare_branding.py square-logo.png horizontal-logo.png
"""
from pathlib import Path
import sys

from PIL import Image, ImageChops

PUBLIC = Path(__file__).resolve().parents[1] / "public"
BRANDING = PUBLIC / "branding"
BACKGROUND = (7, 9, 13, 255)


def cutout(path: str) -> Image.Image:
    original = Image.open(path).convert("RGB")
    brightest = ImageChops.lighter(ImageChops.lighter(*original.split()[:2]), original.split()[2])
    # Only the near-black matte is removed; opaque artwork pixels remain unchanged.
    alpha = brightest.point(lambda value: round(max(0, min(1, (value - 24) / 64)) * 255))
    pixels = original.convert("RGBA")
    pixels.putalpha(alpha)
    image_data = list(pixels.get_flattened_data())
    for index, (red, green, blue, opacity) in enumerate(image_data):
        if 0 < opacity < 255:
            fraction = opacity / 255
            image_data[index] = tuple(round(max(0, min(255, (color - matte * (1 - fraction)) / fraction)))
                                      for color, matte in zip((red, green, blue), BACKGROUND)) + (opacity,)
    pixels.putdata(image_data)
    return pixels.crop(alpha.getbbox())


def square_icon(wave: Image.Image, size: int, background=(0, 0, 0, 0)) -> Image.Image:
    icon = Image.new("RGBA", (size, size), background)
    fitted = wave.copy()
    fitted.thumbnail((round(size * .88), round(size * .88)), Image.Resampling.LANCZOS)
    icon.alpha_composite(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
    return icon


def main():
    square_path, horizontal_path = sys.argv[1:]
    BRANDING.mkdir(parents=True, exist_ok=True)
    horizontal = cutout(horizontal_path)
    # The wave is the separate component left of the wordmark in the supplied lockup.
    alpha = horizontal.getchannel("A")
    separator = next(x for x in range(round(horizontal.width * .25), round(horizontal.width * .4))
                     if alpha.crop((x, 0, x + 1, horizontal.height)).getbbox() is None)
    wave = horizontal.crop((0, 0, separator, horizontal.height))
    wave = wave.crop(wave.getchannel("A").getbbox())
    wave.save(BRANDING / "careerflow-wave.png", optimize=True)

    horizontal.thumbnail((624, 100), Image.Resampling.LANCZOS)
    horizontal.save(BRANDING / "careerflow-horizontal.png", optimize=True)
    horizontal.save(BRANDING / "careerflow-horizontal.webp", lossless=True, method=6)

    for size in (16, 32, 48):
        square_icon(wave, size).save(PUBLIC / f"favicon-{size}x{size}.png", optimize=True)
    square_icon(wave, 48).save(PUBLIC / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    square_icon(wave, 180, BACKGROUND).convert("RGB").save(PUBLIC / "apple-touch-icon.png", optimize=True)
    for size in (192, 512):
        square_icon(wave, size).save(PUBLIC / f"icon-{size}.png", optimize=True)

    stacked = cutout(square_path)
    stacked.thumbnail((900, 490), Image.Resampling.LANCZOS)
    preview = Image.new("RGBA", (1200, 630), BACKGROUND)
    preview.alpha_composite(stacked, ((1200 - stacked.width) // 2, (630 - stacked.height) // 2))
    preview.convert("RGB").save(PUBLIC / "careerflow-og.png", optimize=True)

    assert horizontal.width / horizontal.height > 7
    assert wave.width / wave.height > 2
    assert horizontal.getpixel((0, 0))[3] == 0
    for size in (32, 48):
        assert Image.open(PUBLIC / f"favicon-{size}x{size}.png").size == (size, size)
    assert Image.open(PUBLIC / "apple-touch-icon.png").size == (180, 180)
    assert Image.open(PUBLIC / "careerflow-og.png").size == (1200, 630)
    print(f"Exported original artwork: horizontal {horizontal.size}, wave {wave.size}, OG 1200x630.")


if __name__ == "__main__":
    main()
