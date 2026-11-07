#!/usr/bin/env python3
"""Create a deterministic, disabled staging ZIP. Never reads a real Kindle."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

from kindle_calendar.deployment import MARKER, inventory
from kindle_calendar.generator import verify


def package(source, destination):
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or (source/".owner").read_text() != MARKER:
        raise ValueError("Se necesita un staging propio")
    if not (source/"DISABLED").is_file():
        raise ValueError("El paquete debe estar desactivado")
    if inventory(source) != json.loads((source/".inventory.json").read_text()):
        raise ValueError("El staging cambió después de validarse")
    verify(source/"images")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents silently replacing a previous release.
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            name = "kindle-calendar/" + path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(name + ("/" if path.is_dir() else ""), (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = ((0o40755 if path.is_dir() else 0o100644) << 16)
            archive.writestr(info, b"" if path.is_dir() else path.read_bytes(),
                             compress_type=zipfile.ZIP_DEFLATED)
    checksum = hashlib.sha256(destination.read_bytes()).hexdigest()
    destination.with_suffix(destination.suffix+".sha256").write_text(f"{checksum}  {destination.name}\n")
    return checksum


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    print(package(args.source, args.out))
