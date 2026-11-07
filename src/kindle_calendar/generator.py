"""Render grayscale PNGs on the development computer, never on the Kindle."""
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .calendar import MONTHS, WEEKDAYS, ZONE, dates, month_rows

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "assets" / "fonts"
SIZE = (1272, 1696)  # PW6 portrait; verify framebuffer before device enablement.


@lru_cache(maxsize=32)
def load_font(pixels, bold):
    return ImageFont.truetype(str(FONTS / ("NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf")), pixels)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(day, size=SIZE):
    width, height = size
    if width < 600 or height < 800 or width / height > 0.85:
        raise ValueError("Se requiere un panel vertical de al menos 600 × 800")
    sx, sy = width / 1272, height / 1696
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)

    def font(px, bold=False):
        return load_font(max(1, round(px * min(sx, sy))), bold)

    def text(x, y, value, px, bold=False, fill=0):
        draw.text((round(x * sx), round(y * sy)), value, font=font(px, bold), fill=fill, anchor="mm")

    text(636, 116, f"{MONTHS[day.month].upper()} {day.year}", 57, True)
    text(636, 300, f"{day.day:02d}", 242, True)
    text(636, 501, WEEKDAYS[day.weekday()].upper(), 76, True)
    draw.line((84*sx, 638*sy, 1188*sx, 638*sy), fill=0, width=max(1, round(3*sx)))
    for col, label in enumerate(("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM")):
        text(162 + col*158, 738, label, 31, True)
    # Fixed six-row area: no jumps in the grid between months.
    for row, week in enumerate(month_rows(day)):
        for col, number in enumerate(week):
            if not number:
                continue
            x, y = 162 + col*158, 863 + row*124
            selected = number == day.day
            if selected:
                draw.rounded_rectangle(((x-57)*sx, (y-51)*sy, (x+57)*sx, (y+51)*sy),
                                       radius=12*min(sx, sy), fill=0)
            text(x, y, str(number), 54, selected, 255 if selected else 0)
    return image


def generate(start, end, output, size=SIZE):
    output = Path(output)
    # Do not leave an old manifest certifying a partially rewritten bundle.
    if output.exists() and any(output.iterdir()):
        raise ValueError("La carpeta de salida debe estar vacía; generar otra versión")
    output.mkdir(parents=True, exist_ok=True)
    entries = {}
    for day in dates(start, end):
        name = f"{day.isoformat()}.png"
        temporary = output / (name + ".tmp")
        render(day, size).save(temporary, format="PNG", optimize=False)
        os.replace(temporary, output / name)
        entries[day.isoformat()] = {"file": name, "sha256": digest(output / name)}
    manifest = {"schema": 1, "timezone": ZONE, "size": list(size), "mode": "L",
                "start": start.isoformat(), "end": end.isoformat(), "images": entries,
                "fonts": {p.name: digest(p) for p in sorted(FONTS.glob("*.ttf"))}}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    lines = [f"{entry['sha256']}  {entry['file']}\n" for entry in entries.values()]
    (output / "SHA256SUMS").write_text("".join(lines))
    return manifest


def verify(bundle):
    bundle = Path(bundle)
    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest["schema"] != 1 or manifest["timezone"] != ZONE or manifest["mode"] != "L":
        raise ValueError("Manifiesto incompatible")
    from datetime import date
    expected = [d.isoformat() for d in dates(date.fromisoformat(manifest["start"]),
                                          date.fromisoformat(manifest["end"]))]
    if set(expected) != set(manifest["images"]) or not expected:
        raise ValueError("Cobertura incompleta")
    sums = []
    for day in expected:
        entry = manifest["images"][day]
        if entry["file"] != day + ".png":
            raise ValueError("Nombre de imagen inválido")
        path = bundle / entry["file"]
        if path.is_symlink() or digest(path) != entry["sha256"]:
            raise ValueError(f"Integridad incorrecta: {day}")
        with Image.open(path) as image:
            image.load()
            if list(image.size) != manifest["size"] or image.mode != "L" or image.format != "PNG":
                raise ValueError(f"Formato incorrecto: {day}")
        sums.append(f"{entry['sha256']}  {entry['file']}\n")
    if (bundle / "SHA256SUMS").read_text() != "".join(sums):
        raise ValueError("SHA256SUMS no coincide con el manifiesto")
    return manifest
