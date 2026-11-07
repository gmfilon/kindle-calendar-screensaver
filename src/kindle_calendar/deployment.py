"""Reversible desktop staging, with no privileged or automatic device actions."""
import os
import shutil
import json
from pathlib import Path

from .generator import ROOT, digest, verify

MARKER = "kindle-calendar-staging-v1\n"


def inventory(target):
    result = {}
    for path in sorted(target.rglob("*")):
        if path.name == ".inventory.json" and path.parent == target:
            continue
        if path.is_symlink():
            raise ValueError("Staging no admite enlaces simbólicos")
        result[str(path.relative_to(target))] = "dir" if path.is_dir() else digest(path)
    return result


def safe_root(root):
    root = Path(root).expanduser().resolve()
    blocked = ("/mnt", "/Volumes", "/media", "/run/media", "/sys", "/proc", "/dev", "/etc", "/usr", "/var/local")
    forbidden = {Path(p).resolve() for p in blocked}
    if root == Path("/") or any(root == path or path in root.parents for path in forbidden):
        raise ValueError("Sólo staging local: no se permiten destinos de sistema ni del Kindle")
    return root


def install(bundle, root):
    manifest = verify(bundle)
    root = safe_root(root)
    root.mkdir(parents=True, exist_ok=True)
    target, temporary = root / "kindle-calendar", root / ".kindle-calendar-new"
    if target.exists() or target.is_symlink() or temporary.exists() or temporary.is_symlink():
        raise ValueError("El destino ya existe; conservarlo y usar otra carpeta de staging")
    try:
        temporary.mkdir()
        (temporary / ".owner").write_text(MARKER)
        shutil.copytree(bundle, temporary / "images")
        shutil.copytree(ROOT / "device", temporary / "device")
        shutil.copytree(ROOT / "docs", temporary / "docs")
        shutil.copy2(ROOT / "LICENSE", temporary / "LICENSE")
        (temporary / "state").mkdir()
        (temporary / "DISABLED").write_text("Integración de hardware pendiente de validar.\n")
        verify(temporary / "images")
        (temporary / ".inventory.json").write_text(json.dumps(inventory(temporary), indent=2))
        os.replace(temporary, target)
    except Exception:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    return target, len(manifest["images"])


def uninstall(root):
    target = safe_root(root) / "kindle-calendar"
    if target.is_symlink() or not target.is_dir() or (target / ".owner").is_symlink():
        raise ValueError("No es una instalación de staging propia")
    if (target / ".owner").read_text() != MARKER:
        raise ValueError("Marcador de propiedad inválido")
    # Preserve anything the user added after installation by refusing to delete it.
    snapshot = target / ".inventory.json"
    if snapshot.is_symlink() or inventory(target) != json.loads(snapshot.read_text()):
        raise ValueError("El staging cambió: conservar y revisar manualmente")
    shutil.rmtree(target)
