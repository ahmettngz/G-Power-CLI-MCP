"""
Command-Line Interface (CLI) for Paired Samples t-Test Power Analysis (gpower-clone).

Follows CONTRACT.md:
- Single-line JSON output on stdout with exit code 0 for valid inputs.
- Single-line JSON {"error": "<message>"} with non-zero exit code (1) for invalid inputs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

# Ensure package root is importable when executed directly as `python src/cli.py`
if __package__ is None or __package__ == "":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.engine import ValidationError, calculate_t_paired


class _JSONArgumentParser(argparse.ArgumentParser):
    """Custom ArgumentParser that emits single-line JSON error instead of plain text."""

    def error(self, message: str) -> None:
        sys.stdout.write(json.dumps({"error": message}, ensure_ascii=False) + "\n")
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = _JSONArgumentParser(
        prog="gpower-clone",
        description="Clean-room Paired Samples t-Test (t-paired) power and sample size calculator.",
    )
    parser.add_argument(
        "--test",
        type=str,
        default="t-paired",
        help="Statistical test family identifier (must be 't-paired').",
    )
    parser.add_argument(
        "--mode",
        type=str,
        required=True,
        help="Analysis mode: 'a-priori' (compute N) or 'post-hoc' (compute power).",
    )
    parser.add_argument(
        "--tails",
        type=int,
        default=2,
        help="Number of tails: 1 (one-tailed) or 2 (two-tailed, default).",
    )
    parser.add_argument(
        "--dz",
        "--d",
        dest="dz",
        type=float,
        default=None,
        help="Effect size dz (Cohen's dz for paired differences).",
    )
    parser.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level alpha (default: 0.05).",
    )
    parser.add_argument(
        "--power",
        type=float,
        default=None,
        help="Target statistical power (1 - beta) for a-priori mode.",
    )
    parser.add_argument(
        "--n",
        "--n-total",
        "--n_total",
        dest="n_total",
        type=float,
        default=None,
        help="Total sample size (number of pairs N) for post-hoc mode.",
    )
    # Optional pre/post ("önce ve sonra tansiyon") group/difference parameters to compute dz
    parser.add_argument("--mean-dz", "--mean_dz", dest="mean_dz", type=float, default=None)
    parser.add_argument("--sd-dz", "--sd_dz", dest="sd_dz", type=float, default=None)
    parser.add_argument("--mean1", type=float, default=None, help="Group 1 (pre) mean.")
    parser.add_argument("--mean2", type=float, default=None, help="Group 2 (post) mean.")
    parser.add_argument("--sd1", type=float, default=None, help="Group 1 (pre) SD.")
    parser.add_argument("--sd2", type=float, default=None, help="Group 2 (post) SD.")
    parser.add_argument("--corr", "--r", dest="corr", type=float, default=None, help="Correlation r between paired measurements.")
    return parser


def run_cli(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    test_norm = (args.test or "").strip().lower().replace("_", "-")
    if test_norm not in ("t-paired", "tpaired", "paired-t"):
        sys.stdout.write(
            json.dumps(
                {"error": f"Unsupported test family '{args.test}'. This build implements 't-paired'."},
                ensure_ascii=False,
            )
            + "\n"
        )
        return 1

    try:
        result = calculate_t_paired(
            mode=args.mode,
            tails=args.tails,
            dz=args.dz,
            alpha=args.alpha,
            power=args.power,
            n_total=args.n_total,
            mean_dz=args.mean_dz,
            sd_dz=args.sd_dz,
            mean1=args.mean1,
            mean2=args.mean2,
            sd1=args.sd1,
            sd2=args.sd2,
            corr=args.corr,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
        return 0
    except ValidationError as exc:
        sys.stdout.write(
            json.dumps({"error": str(exc)}, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        return 1
    except Exception as exc:  # pragma: no cover
        sys.stdout.write(
            json.dumps({"error": f"Internal error: {exc}"}, ensure_ascii=False, separators=(",", ":")) + "\n"
        )
        return 1


def main() -> None:
    sys.exit(run_cli())


if __name__ == "__main__":
    main()
