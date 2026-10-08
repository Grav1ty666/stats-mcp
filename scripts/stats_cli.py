#!/usr/bin/env python3
"""Standalone CLI for stats-mcp analyses (works without the MCP server).

Reuses the analysis functions defined in ../server.py so there is a single
source of truth. Handy as a WorkBuddy skill fallback or for batch use.
"""
import argparse
import sys
from pathlib import Path

# Make the parent dir (repo root, where server.py lives) importable.
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import server as s  # noqa: E402

TOOLS = {
    "describe": s.describe,
    "oneway_anova": s.oneway_anova,
    "twoway_anova": s.twoway_anova,
    "mixed_model": s.mixed_model,
    "tukey_hsd_test": s.tukey_hsd_test,
    "dunnett_test": s.dunnett_test,
    "ttest": s.ttest,
    "correlation": s.correlation,
    "linear_regression": s.linear_regression,
}


def build_parser():
    p = argparse.ArgumentParser(
        prog="stats_cli", description="Run a statistical analysis (no MCP needed).")
    p.add_argument("tool", choices=list(TOOLS.keys()), help="Analysis to run")
    p.add_argument("--csv", required=True, help="Path to CSV/XLSX data file")
    p.add_argument("--group_col", help="Grouping column (anova/ttest/etc.)")
    p.add_argument("--value_col", help="Response/value column")
    p.add_argument("--factor_cols", help="Two factor columns, comma-separated (twoway_anova)")
    p.add_argument("--fixed_cols", help="Fixed-effect columns, comma-separated (mixed_model)")
    p.add_argument("--random_intercept_col", help="Random intercept column (mixed_model)")
    p.add_argument("--control", help="Control level (dunnett_test)")
    p.add_argument("--posthoc", default="tukey", help="Post-hoc for oneway_anova: tukey/none")
    p.add_argument("--paired", action="store_true", help="Paired t-test")
    p.add_argument("--cols", help="Columns for describe/correlation, comma-separated")
    p.add_argument("--method", default="pearson", help="Correlation method")
    p.add_argument("--y_col", help="Dependent variable (regression)")
    p.add_argument("--x_cols", help="Independent variables, comma-separated (regression)")
    return p


def main():
    args = build_parser().parse_args()
    tool = args.tool
    if tool == "describe":
        kwargs = {"csv_path": args.csv, "value_cols": args.cols or ""}
    elif tool == "oneway_anova":
        kwargs = {"csv_path": args.csv, "group_col": args.group_col,
                  "value_col": args.value_col, "posthoc": args.posthoc}
    elif tool == "twoway_anova":
        kwargs = {"csv_path": args.csv, "factor_cols": args.factor_cols,
                  "value_col": args.value_col}
    elif tool == "mixed_model":
        kwargs = {"csv_path": args.csv, "value_col": args.value_col,
                  "fixed_cols": args.fixed_cols,
                  "random_intercept_col": args.random_intercept_col}
    elif tool == "tukey_hsd_test":
        kwargs = {"csv_path": args.csv, "group_col": args.group_col,
                  "value_col": args.value_col}
    elif tool == "dunnett_test":
        kwargs = {"csv_path": args.csv, "group_col": args.group_col,
                  "value_col": args.value_col, "control": args.control}
    elif tool == "ttest":
        kwargs = {"csv_path": args.csv, "group_col": args.group_col,
                  "value_col": args.value_col, "paired": args.paired}
    elif tool == "correlation":
        kwargs = {"csv_path": args.csv, "cols": args.cols or "",
                  "method": args.method}
    elif tool == "linear_regression":
        kwargs = {"csv_path": args.csv, "y_col": args.y_col, "x_cols": args.x_cols}
    else:  # unreachable due to choices=
        raise SystemExit(f"Unknown tool: {tool}")
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    print(TOOLS[tool](**kwargs))


if __name__ == "__main__":
    main()
