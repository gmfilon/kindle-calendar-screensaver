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
SIZE = (1696, 1272)  # PW6 landscape layout; framebuffer orientation needs validation.
EXPORT_ROTATION = 270  # Native portrait PNG; Kindle's bottom/power button at the left.


@lru_cache(maxsize=32)
def load_font(pixels, bold):
    return ImageFont.truetype(str(FONTS / ("NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf")), pixels)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(day, size=SIZE, rotation=0):
    width, height = size
    if min(size) < 600 or max(size) < 800 or not 0.5 <= width / height <= 2:
        raise ValueError("Se requiere un panel de al menos 600 × 800, vertical u horizontal")
    if rotation not in (0, 90, 180, 270):
        raise ValueError("La rotación debe ser 0, 90, 180 o 270 grados horarios")
    landscape = width > height
    sx, sy = (width / 1696, height / 1272) if landscape else (width / 1272, height / 1696)
    image = Image.new("L", size, 255)
    draw = ImageDraw.Draw(image)

    def font(px, bold=False):
        return load_font(max(1, round(px * min(sx, sy))), bold)

    def text(x, y, value, px, bold=False, fill=0):
        draw.text((round(x * sx), round(y * sy)), value, font=font(px, bold), fill=fill, anchor="mm")

    if landscape:
        text(326, 380, f"{MONTHS[day.month].upper()} {day.year}", 46, True)
        text(326, 620, f"{day.day:02d}", 300, True)
        text(326, 850, WEEKDAYS[day.weekday()].upper(), 68, True)
        draw.line((640*sx, 200*sy, 640*sx, 1072*sy), fill=0, width=max(1, round(3*sx)))
        first_x, column_step, header_y, first_y, row_step = 744, 144, 300, 425, 118
        cell_half_width, cell_half_height = 49, 46
    else:
        text(636, 116, f"{MONTHS[day.month].upper()} {day.year}", 57, True)
        text(636, 300, f"{day.day:02d}", 242, True)
        text(636, 501, WEEKDAYS[day.weekday()].upper(), 76, True)
        draw.line((84*sx, 638*sy, 1188*sx, 638*sy), fill=0, width=max(1, round(3*sx)))
        first_x, column_step, header_y, first_y, row_step = 162, 158, 738, 863, 124
        cell_half_width, cell_half_height = 57, 51
    for col, label in enumerate(("LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB", "DOM")):
        text(first_x + col*column_step, header_y, label, 31, True)
    # Fixed six-row area: no jumps in the grid between months.
    for row, week in enumerate(month_rows(day)):
        for col, number in enumerate(week):
            if not number:
                continue
            x, y = first_x + col*column_step, first_y + row*row_step
            selected = number == day.day
            if selected:
                draw.rounded_rectangle(((x-cell_half_width)*sx, (y-cell_half_height)*sy,
                                        (x+cell_half_width)*sx, (y+cell_half_height)*sy),
                                       radius=12*min(sx, sy), fill=0)
            text(x, y, str(number), 54, selected, 255 if selected else 0)
    turns = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180,
             270: Image.Transpose.ROTATE_90}
    return image.transpose(turns[rotation]) if rotation else image


def generate(start, end, output, size=SIZE, rotation=None):
    output = Path(output)
    if rotation is None:
        rotation = EXPORT_ROTATION if size[0] > size[1] else 0
    # Do not leave an old manifest certifying a partially rewritten bundle.
    if output.exists() and any(output.iterdir()):
        raise ValueError("La carpeta de salida debe estar vacía; generar otra versión")
    output.mkdir(parents=True, exist_ok=True)
    entries = {}
    for day in dates(start, end):
        name = f"{day.isoformat()}.png"
        temporary = output / (name + ".tmp")
        rendered = render(day, size, rotation)
        rendered.save(temporary, format="PNG", optimize=False)
        os.replace(temporary, output / name)
        entries[day.isoformat()] = {"file": name, "sha256": digest(output / name)}
    manifest = {"schema": 1, "timezone": ZONE, "size": list(rendered.size), "mode": "L",
                "layout": "landscape" if size[0] > size[1] else "portrait",
                "layout_size": list(size), "rotation_clockwise": rotation,
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
