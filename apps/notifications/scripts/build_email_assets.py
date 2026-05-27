"""Generate Lucide-style social PNGs for HTML emails (matches landing footer icons)."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / 'static' / 'email'
OUT.mkdir(parents=True, exist_ok=True)

# Lucide paths from lucide-react (24×24 viewBox) — same icons as landing footer.
LUCIDE_ICONS: dict[str, list[tuple[str, dict[str, str]]]] = {
    'icon-twitter': [
        (
            'path',
            {
                'd': 'M22 4s-.7 2.1-2 3.4c1.6 10-9.4 17.3-18 11.6 2.2.1 4.4-.6 6-2C3 15.5.5 9.6 3 5c2.2 2.6 5.6 4.1 9 4-.9-4.2 4-6.6 7-3.8 1.1 0 3-1.2 3-1.2z',
            },
        ),
    ],
    'icon-facebook': [
        ('path', {'d': 'M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z'}),
    ],
    'icon-instagram': [
        ('rect', {'width': '20', 'height': '20', 'x': '2', 'y': '2', 'rx': '5', 'ry': '5'}),
        ('path', {'d': 'M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z'}),
        ('line', {'x1': '17.5', 'x2': '17.51', 'y1': '6.5', 'y2': '6.5'}),
    ],
    'icon-linkedin': [
        ('path', {'d': 'M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z'}),
        ('rect', {'width': '4', 'height': '12', 'x': '2', 'y': '9'}),
        ('circle', {'cx': '4', 'cy': '4', 'r': '2'}),
    ],
    'icon-youtube': [
        (
            'path',
            {
                'd': 'M2.5 17a24.12 24.12 0 0 1 0-10 2 2 0 0 1 1.4-1.4 49.56 49.56 0 0 1 16.2 0A2 2 0 0 1 21.5 7a24.12 24.12 0 0 1 0 10 2 2 0 0 1-1.4 1.4 49.55 49.55 0 0 1-16.2 0A2 2 0 0 1 2.5 17',
            },
        ),
        ('path', {'d': 'm10 15 5-3-5-3z'}),
    ],
}

STROKE = '#152a1e'
BORDER = '#9ca3af'


def _element_xml(tag: str, attrs: dict[str, str]) -> str:
    if tag == 'line':
        return (
            f'<line x1="{attrs["x1"]}" y1="{attrs["y1"]}" x2="{attrs["x2"]}" y2="{attrs["y2"]}" />'
        )
    if tag == 'circle':
        return f'<circle cx="{attrs["cx"]}" cy="{attrs["cy"]}" r="{attrs["r"]}" />'
    if tag == 'rect':
        extra = ''
        if 'rx' in attrs:
            extra += f' rx="{attrs["rx"]}" ry="{attrs.get("ry", attrs["rx"])}"'
        return (
            f'<rect x="{attrs["x"]}" y="{attrs["y"]}" width="{attrs["width"]}" '
            f'height="{attrs["height"]}"{extra} />'
        )
    return f'<path d="{attrs["d"]}" />'


def _social_svg(elements: list[tuple[str, dict[str, str]]]) -> str:
    inner = '\n    '.join(_element_xml(tag, attrs) for tag, attrs in elements)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36">
  <rect x="0.5" y="0.5" width="35" height="35" rx="6" fill="#ffffff" stroke="{BORDER}" stroke-width="1"/>
  <g transform="translate(6,6)" fill="none" stroke="{STROKE}" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
    {inner}
  </g>
</svg>"""


def _rasterize_svg(svg_path: Path, png_path: Path) -> bool:
    """Try qlmanage (macOS), then rsvg-convert."""
    for cmd in (
        ['qlmanage', '-t', '-s', '144', '-o', str(png_path.parent), str(svg_path)],
        ['rsvg-convert', '-w', '72', '-h', '72', str(svg_path), '-o', str(png_path)],
    ):
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            if cmd[0] == 'qlmanage':
                generated = png_path.parent / f'{svg_path.name}.png'
                if generated.exists():
                    generated.rename(png_path)
                    return True
            return png_path.is_file()
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False


def _social_icon_pil(elements: list[tuple[str, dict[str, str]]], png_path: Path) -> None:
    """Fallback: bordered tile with label when SVG rasterize unavailable."""
    size = 36
    img = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=6, outline=BORDER, width=1)
    labels = {
        'icon-twitter': '𝕏',
        'icon-facebook': 'f',
        'icon-instagram': '◎',
        'icon-linkedin': 'in',
        'icon-youtube': '▶',
    }
    label = labels.get(png_path.stem, '•')
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 14)
    except OSError:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), label, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - 1), label, fill=STROKE, font=font)
    img.save(png_path, 'PNG', optimize=True)


def _save(name: str, img: Image.Image) -> None:
    path = OUT / name
    img.save(path, 'PNG', optimize=True)
    print('wrote', path, img.size)


def logo_wordmark() -> None:
    w, h = 200, 48
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((0, 6), 'SafaPay', fill=(255, 255, 255, 255), font=font)
    _save('logo-white.png', img)


def social_icons() -> None:
    for filename, elements in LUCIDE_ICONS.items():
        svg_path = OUT / f'{filename}.svg'
        png_path = OUT / f'{filename}.png'
        svg_path.write_text(_social_svg(elements), encoding='utf-8')
        if not _rasterize_svg(svg_path, png_path):
            _social_icon_pil(elements, png_path)
            print('wrote (pil fallback)', png_path)
        else:
            print('wrote', png_path)
        svg_path.unlink(missing_ok=True)


def main() -> None:
    logo_wordmark()
    social_icons()


if __name__ == '__main__':
    main()
