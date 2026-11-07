import argparse
import json
from datetime import date, datetime

from .calendar import wake_plan
from .deployment import install, uninstall
from .generator import generate, verify


def main():
    parser = argparse.ArgumentParser(description="Calendario local para Kindle: prototipo seguro")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--start", type=date.fromisoformat, required=True)
    gen.add_argument("--end", type=date.fromisoformat, required=True)
    gen.add_argument("--out", required=True)
    gen.add_argument("--width", type=int, default=1272)
    gen.add_argument("--height", type=int, default=1696)
    check = sub.add_parser("verify")
    check.add_argument("bundle")
    plan = sub.add_parser("plan")
    plan.add_argument("--now", type=datetime.fromisoformat, required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("bundle")
    stage.add_argument("--root", required=True)
    remove = sub.add_parser("unstage")
    remove.add_argument("--root", required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            result = generate(args.start, args.end, args.out, (args.width, args.height))
            print(f"Generadas {len(result['images'])} imágenes en {args.out}")
        elif args.command == "verify":
            print(f"Verificadas {len(verify(args.bundle)['images'])} imágenes")
        elif args.command == "plan":
            print(json.dumps(wake_plan(args.now), indent=2))
        elif args.command == "stage":
            path, count = install(args.bundle, args.root)
            print(f"Staging local desactivado: {path} ({count} imágenes)")
        else:
            uninstall(args.root)
            print("Staging eliminado")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
