#!/usr/bin/env python3
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fha.pipeline import run


ROOT = Path(__file__).resolve().parents[1]


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def portable_summary(value):
    """Remove checkout-specific path prefixes before persisting a run report."""
    result = json_safe(value)
    if isinstance(result, dict) and "outputs" in result:
        output_path = Path(result["outputs"])
        try:
            result["outputs"] = str(output_path.resolve().relative_to(ROOT))
        except ValueError:
            result["outputs"] = output_path.name
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=("paper", "synthetic"), default="paper")
    args = parser.parse_args()
    result = portable_summary(run(args.source))
    if args.source == "paper":
        out = ROOT / "outputs" / "paper" / "pipeline_summary.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2, default=str, allow_nan=False) + "\n",
                       encoding="utf-8")
    print(json.dumps(result, indent=2, default=str, allow_nan=False))


if __name__ == "__main__":
    main()
