"""Command-line interface for the change sentinel."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .engine import review_change


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review a Kubernetes manifest change without contacting a cluster."
    )
    parser.add_argument("input", type=Path, help="Path to a JSON change request")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    report = review_change(payload)
    print(json.dumps(report, indent=None if args.compact else 2, sort_keys=True))
    return {"PASS": 0, "REVIEW": 1, "BLOCK": 2}[report["decision"]]

