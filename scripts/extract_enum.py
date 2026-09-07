#!/usr/bin/env python3

"""Extract carta-python enum contracts for carta-frontend CI.

The manifest records all public enums owned by carta-python and the subset
which is defined by the CARTA frontend or protobuf declarations.  Frontend
and protobuf names are kept unqualified; their manifest section identifies the
source.
"""

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from carta import constants  # noqa: E402


ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "carta-python-enum.json"

REGISTRIES = (
    ("carta-python", constants.CartaPythonEnum),
    ("frontend", constants.FrontendEnum),
    ("protobuf", constants.ProtobufEnum),
)


def enum_members(enum):
    """Return a canonical, JSON-serialisable representation of an enum."""
    return [
        {"name": name, "value": member.value}
        for name, member in sorted(enum.__members__.items())
    ]


def manifest():
    """Return the canonical enum contract."""
    return {
        "enums": {
            source: {
                name: enum_members(enum)
                for name, enum in sorted(registry.ENUMS.items())
            }
            for source, registry in REGISTRIES
        },
    }


def dump_manifest(data):
    """Serialise a manifest canonically."""
    return json.dumps(data, indent=2) + "\n"


def main():
    """Run the enum manifest generator."""
    parser = argparse.ArgumentParser(description="Extract carta-python enum values for carta-frontend CI.")
    parser.add_argument("--write-manifest", action="store_true", help=f"write the contract manifest to {MANIFEST.name}")
    parser.add_argument("--output", metavar="FILE", help="write the manifest to FILE instead of the default path")
    args = parser.parse_args()

    if args.output and not args.write_manifest:
        parser.error("--output requires --write-manifest")

    data = manifest()

    if args.write_manifest:
        output = pathlib.Path(args.output) if args.output else MANIFEST
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(dump_manifest(data))
        counts = {
            source: sum(len(members) for members in enums.values())
            for source, enums in data["enums"].items()
        }
        total = sum(counts.values())
        breakdown = ", ".join(f"{source}: {count}" for source, count in counts.items())
        print(f"Wrote {total} enum values to {output} ({breakdown}).")

    if not args.write_manifest:
        print(dump_manifest(data), end="")

    return 0


if __name__ == "__main__":
    sys.exit(main())
