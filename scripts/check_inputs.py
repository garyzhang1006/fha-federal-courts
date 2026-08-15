#!/usr/bin/env python3
"""Fail fast when a frozen paper input is missing or has changed."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_manifest(root: Path, manifest_path: Path) -> list[str]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"manifest missing: {manifest_path}"]
    except json.JSONDecodeError as exc:
        return [f"manifest is not valid JSON: {manifest_path}: {exc}"]

    if not isinstance(manifest, dict):
        return [f"unsupported manifest schema: {manifest_path}"]
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), list):
        return [f"unsupported manifest schema: {manifest_path}"]

    failures = []
    for index, entry in enumerate(manifest["files"]):
        if not isinstance(entry, dict):
            failures.append(f"invalid manifest entry {index}: expected an object")
            continue
        relative = Path(entry.get("path", ""))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            failures.append(f"unsafe manifest path: {relative}")
            continue
        path = root / relative
        if not path.is_file():
            failures.append(f"missing input: {relative}")
            continue
        size = path.stat().st_size
        if size != entry.get("bytes"):
            failures.append(
                f"size mismatch: {relative}: expected {entry.get('bytes')}, got {size}"
            )
            continue
        actual = sha256(path)
        if actual != entry.get("sha256"):
            failures.append(
                f"SHA-256 mismatch: {relative}: expected {entry.get('sha256')}, got {actual}"
            )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest or root / "data" / "manifest.json"
    failures = check_manifest(root, manifest)
    if failures:
        print("frozen input verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        print("restore the committed files before running the paper workflow", file=sys.stderr)
        return 1
    count = len(json.loads(manifest.read_text(encoding="utf-8"))["files"])
    try:
        display = manifest.relative_to(root)
    except ValueError:
        display = manifest
    print(f"verified {count} frozen inputs against {display}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
