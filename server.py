#!/usr/bin/env python3
"""stats-mcp — a local statistical-analysis MCP server.

A Model Context Protocol (stdio) server that exposes common statistical
analysis tools as callable MCP tools. It is a license-clean, free replacement
for a SAS-backed MCP: it covers the frequent SAS procedures used in
field-trial / biostatistics / general statistical workflows
(PROC MEANS / GLM / MIXED / ANOVA / TUKEY / DUNNETT / CORR / REG) using
pandas + scipy + statsmodels.

The methods are domain-agnostic — ANOVA, mixed models, multiple comparisons,
t-tests, correlation and regression apply equally to agriculture, medicine,
psychology, engineering, finance, etc. The "agri" framing in examples is only
one use case.

Tools
-----
- describe            : descriptive statistics (PROC MEANS)
- oneway_anova        : one-way ANOVA + optional post-hoc (PROC GLM / ANOVA)
- twoway_anova        : two-way factorial ANOVA (PROC GLM)
- mixed_model         : linear mixed model, random intercept (PROC MIXED)
- tukey_hsd_test      : Tukey HSD all-pairs multiple comparisons
- dunnett_test        : Dunnett test vs. a control group
- ttest               : independent / paired t-test (two groups)
- correlation         : correlation matrix (PROC CORR)
- linear_regression   : OLS regression (PROC REG)

Input  : a CSV or XLSX file on disk (absolute path, or relative to the data dir).
Output : a human-readable summary returned to the agent, plus a full report
         written to the output directory (path printed in the result).

Configuration
-------------
The working directory defaults to the folder that contains this script
(so `data/` and `out/` live next to server.py). Override it with the
environment variable ``STATS_MCP_DIR`` (absolute path).
"""
import os
import sys
import functools
import warnings
from pathlib import Path

import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.formula.api import ols, mixedlm
from statsmodels.stats.anova import anova_lm
import scikit_posthocs as sp

from mcp.server.fastmcp import FastMCP

warnings.filterwarnings("ignore")

mcp = FastMCP("stats-mcp")

# Default working dir = this script's own directory; override with STATS_MCP_DIR.
_BASE_ENV = os.environ.get("STATS_MCP_DIR")
BASE = Path(_BASE_ENV) if _BASE_ENV else Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUT_DIR = BASE / "out"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _log(msg: str):
    print(f"[stats-mcp] {msg}", file=sys.stderr, flush=True)


def _load(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.is_absolute():
        cand = DATA_DIR / p
        if cand.exists():
            p = cand
    if not p.exists():
        raise FileNotFoundError(f"数据文件不存在: {path}")
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p)
    return pd.read_csv(p)


def _save_report(name: str, text: str) -> str:
    out = OUT_DIR / f"{name}.txt"
    out.write_text(text, encoding="utf-8")
    return str(out)


def _fmt_table(df: pd.DataFrame) -> str:
    return df.to_string(index=False)


def _guard(fn_name: str):
    """Return a friendly error instead of crashing the MCP tool."""
    def deco(f):
        @functools.wraps(f)
        def wrap(*a, **k):
            try:
                return f(*a, **k)
            except Exception as e:
                return (f"⚠️ {fn_name} 执行出错：{e}\n"
                        "（常见原因：列名不存在、数据量过小/模型饱和、存在缺失值。请检查输入。）")
        return wrap
    return deco


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool()
@_guard("describe")
def describe(csv_path: str, value_cols: str = "") -> str:
    """描述性统计（对应 PROC MEANS）。

    Args:
        csv_path: CSV/XLSX 路径（绝对路径，或相对于数据目录）。
        value_cols: 需要统计的数值列名，逗号分隔；留空则对所有数值列统计。
    Returns:
        各列的均值/标准差/最值/分位数/缺失数，并写出完整报告文件。
    """
    df = _load(csv_path)
    if value_cols:
        cols = [c.strip() for c in value_cols.split(",") if c.strip()]
    else:
        cols = list(df.select_dtypes(include=[np.number]).columns)
    if not cols:
        return "未找到数值列，无法计算描述性统计。"
    sub = df[cols]
    desc = sub.describe(percentiles=[0.25, 0.5, 0.75]).T
    miss = sub.isna().sum().rename("missing")
    out = pd.concat([desc, miss], axis=1).reset_index().rename(columns={"index": "指标"})
    text = "== 描述性统计 ==\n" + _fmt_table(out) + f"\n\n样本量 n = {len(df)}"
    path = _save_report("describe", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("oneway_anova")
def oneway_anova(csv_path: str, group_col: str, value_col: str,
                posthoc: str = "tukey") -> str:
    """单因素方差分析（对应 PROC GLM / PROC ANOVA）。

    Args:
        csv_path: 数据文件路径。
        group_col: 分组（处理）列名。
        value_col: 观测值（如产量）列名。
        posthoc: 显著性时的事后检验，"tukey"(默认) 或 "none"。
    Returns:
        F 值、p 值、各组均值/标准差/样本量；若显著则给出 Tukey HSD 两两比较。
    """
    df = _load(csv_path)
    groups = [g[value_col].dropna().values for _, g in df.groupby(group_col)]
    f_stat, p_val = stats.f_oneway(*groups)
    means = df.groupby(group_col)[value_col].agg(["mean", "std", "count"])
    text = (f"== 单因素方差分析 ==\n因子: {group_col}  响应: {value_col}\n"
            f"F({len(groups)-1}, {int(sum(len(g)-1 for g in groups))}) = {f_stat:.4f}\n"
            f"p = {p_val:.3e}{'  *** 显著 ***' if p_val < 0.05 else '  不显著'}\n\n"
            f"各组统计:\n{_fmt_table(means.reset_index())}")
    if p_val < 0.05 and posthoc == "tukey":
        ph = sp.posthoc_tukey(df, val_col=value_col, group_col=group_col)
        text += f"\n\nTukey HSD 两两比较 (p 值):\n{ph.to_string()}"
    path = _save_report("oneway_anova", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("twoway_anova")
def twoway_anova(csv_path: str, factor_cols: str, value_col: str) -> str:
    """双因素（可含交互）方差分析（对应 PROC GLM）。

    Args:
        csv_path: 数据文件路径。
        factor_cols: 两个因素列名，逗号分隔（如 "trt,block"）。
        value_col: 响应变量列名。
    Returns:
        II 型方差分析表（各主效应与交互效应的 F、p）。
    """
    df = _load(csv_path)
    fs = [c.strip() for c in factor_cols.split(",") if c.strip()]
    if len(fs) != 2:
        return "twoway_anova 需要恰好两个因素列（用逗号分隔）。"
    a, b = fs
    formula = (f"Q('{value_col}') ~ C(Q('{a}')) + C(Q('{b}')) + "
               f"C(Q('{a}')):C(Q('{b}'))")
    model = ols(formula, data=df).fit()
    table = anova_lm(model, typ=2).reset_index().rename(columns={"index": "来源"})
    text = (f"== 双因素方差分析 ==\n因素: {a} × {b}  响应: {value_col}\n\n"
            f"{_fmt_table(table)}")
    path = _save_report("twoway_anova", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("mixed_model")
def mixed_model(csv_path: str, value_col: str, fixed_cols: str,
                random_intercept_col: str) -> str:
    """线性混合模型（对应 PROC MIXED，随机截距）。

    Args:
        csv_path: 数据文件路径。
        value_col: 响应变量列名。
        fixed_cols: 固定效应列名，逗号分隔（如 "trt" 或 "trt,fertilizer"）。
        random_intercept_col: 随机截距分组列（如 "block" 区组）。
    Returns:
        固定效应估计、p 值、随机效应方差分量。
    """
    df = _load(csv_path)
    fixed = [c.strip() for c in fixed_cols.split(",") if c.strip()]
    fixed_terms = " + ".join(f"C(Q('{c}'))" if df[c].dtype == object
                             else f"Q('{c}')" for c in fixed)
    formula = f"Q('{value_col}') ~ {fixed_terms}"
    model = mixedlm(formula, data=df, groups=df[random_intercept_col]).fit(reml=True)
    fe = pd.DataFrame({
        "coef": model.fe_params,
        "std_err": model.bse,
        "p_value": model.pvalues,
    }).reset_index().rename(columns={"index": "项"})
    fe = fe[~fe["项"].isin(["Group Var"])].dropna(subset=["coef"])
    varcomp = model.cov_re.iloc[0, 0]
    text = (f"== 线性混合模型 (REML) ==\n公式: {value_col} ~ {fixed_terms}\n"
            f"随机截距: {random_intercept_col}\n\n"
            f"固定效应:\n{_fmt_table(fe)}\n\n"
            f"随机效应方差分量 (组间): {varcomp:.4f}\n"
            f"残差方差: {model.scale:.4f}")
    path = _save_report("mixed_model", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("tukey_hsd_test")
def tukey_hsd_test(csv_path: str, group_col: str, value_col: str) -> str:
    """Tukey HSD 多重比较（对应 PROC GLM 的 MEANS ... / TUKEY）。

    Args:
        csv_path: 数据文件路径。
        group_col: 分组列名。
        value_col: 响应变量列名。
    Returns:
        所有处理两两比较的 p 值矩阵。
    """
    df = _load(csv_path)
    ph = sp.posthoc_tukey(df, val_col=value_col, group_col=group_col)
    text = (f"== Tukey HSD 多重比较 ==\n组: {group_col}  响应: {value_col}\n\n"
            f"{ph.to_string()}")
    path = _save_report("tukey_hsd", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("dunnett_test")
def dunnett_test(csv_path: str, group_col: str, value_col: str,
                control: str) -> str:
    """Dunnett 检验：各处理与对照组的比较（对应 PROC GLM 的 DUNNETT）。

    Args:
        csv_path: 数据文件路径。
        group_col: 分组列名。
        value_col: 响应变量列名。
        control: 对照组名称（必须是 group_col 中的某个水平）。
    Returns:
        各处理 vs 对照的 p 值矩阵。
    """
    df = _load(csv_path)
    ph = sp.posthoc_dunnett(df, val_col=value_col, group_col=group_col,
                            control=control)
    text = (f"== Dunnett 检验 (对照={control}) ==\n组: {group_col}  响应: {value_col}\n\n"
            f"{ph.to_string()}")
    path = _save_report("dunnett", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("ttest")
def ttest(csv_path: str, group_col: str, value_col: str,
          paired: bool = False) -> str:
    """两样本 t 检验（对应 PROC TTEST）。

    Args:
        csv_path: 数据文件路径。
        group_col: 分组列名（恰好两个水平）。
        value_col: 响应变量列名。
        paired: True 为配对 t 检验，False（默认）为独立样本 t 检验。
    Returns:
        t 值、p 值、两组均值与差值。
    """
    df = _load(csv_path)
    levels = df[group_col].dropna().unique()
    if len(levels) != 2:
        return f"ttest 要求 {group_col} 恰好有两个水平，当前为 {list(levels)}。"
    a = df[df[group_col] == levels[0]][value_col].dropna()
    b = df[df[group_col] == levels[1]][value_col].dropna()
    if paired:
        res = stats.ttest_rel(a, b)
        kind = "配对"
    else:
        res = stats.ttest_ind(a, b, equal_var=False)
        kind = "独立(Welch)"
    text = (f"== {kind} t 检验 ==\n{levels[0]} vs {levels[1]}  响应: {value_col}\n"
            f"均值 {levels[0]}={a.mean():.4f}, {levels[1]}={b.mean():.4f}\n"
            f"t = {res.statistic:.4f}   p = {res.pvalue:.3e}"
            f"{'  *** 显著 ***' if res.pvalue < 0.05 else '  不显著'}")
    path = _save_report("ttest", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("correlation")
def correlation(csv_path: str, cols: str = "", method: str = "pearson") -> str:
    """相关系数矩阵（对应 PROC CORR）。

    Args:
        csv_path: 数据文件路径。
        cols: 参与相关的列名，逗号分隔；留空则所有数值列。
        method: "pearson"(默认) / "spearman" / "kendall"。
    Returns:
        相关系数矩阵。
    """
    df = _load(csv_path)
    if cols:
        use = [c.strip() for c in cols.split(",") if c.strip()]
    else:
        use = list(df.select_dtypes(include=[np.number]).columns)
    corr = df[use].corr(method=method)
    text = f"== 相关系数矩阵 ({method}) ==\n\n{corr.to_string()}"
    path = _save_report("correlation", text)
    return text + f"\n\n[报告已保存] {path}"


@mcp.tool()
@_guard("linear_regression")
def linear_regression(csv_path: str, y_col: str, x_cols: str) -> str:
    """多元线性回归（对应 PROC REG）。

    Args:
        csv_path: 数据文件路径。
        y_col: 因变量列名。
        x_cols: 自变量列名，逗号分隔（如 "x1,x2"）。
    Returns:
        回归系数、标准误、t、p 及 R²。
    """
    df = _load(csv_path)
    xs = [c.strip() for c in x_cols.split(",") if c.strip()]
    xterms = " + ".join(f"Q('{x}')" for x in xs)
    formula = f"Q('{y_col}') ~ {xterms}"
    model = ols(formula, data=df).fit()
    coef = pd.DataFrame({
        "coef": model.params,
        "std_err": model.bse,
        "t": model.tvalues,
        "p_value": model.pvalues,
    }).reset_index().rename(columns={"index": "项"})
    text = (f"== 线性回归 ==\n公式: {y_col} ~ {xterms}\n"
            f"R² = {model.rsquared:.4f}   调整 R² = {model.rsquared_adj:.4f}\n"
            f"F = {model.fvalue:.4f} (p = {model.f_pvalue:.3e})\n\n"
            f"{_fmt_table(coef)}")
    path = _save_report("regression", text)
    return text + f"\n\n[报告已保存] {path}"


if __name__ == "__main__":
    _log("stats-mcp server starting (stdio)")
    mcp.run()
