---
name: stats-mcp
description: "Local, license-clean statistical analysis for field trials / biostatistics / general stats. Covers ANOVA, mixed models (PROC MIXED), Tukey/Dunnett multiple comparisons, t-tests, correlation, regression — a free SAS replacement. | 本地、无授权风险的统计分析（农学田间试验 / 生物统计 / 通用统计）：方差分析、混合模型、Tukey/Dunnett 多重比较、t 检验、相关、回归，可作为 SAS 的免费替代。"
version: "1.0.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash
---

# stats-mcp — 本地统计分析 Skill

一个**无需 SAS、无需联网**的统计分析能力包。底层用 `pandas` / `scipy` /
`statsmodels` / `scikit_posthocs` 实现，等价于 SAS 的常见过程
（`PROC MEANS` / `GLM` / `MIXED` / `ANOVA` / `TUKEY` / `DUNNETT` / `CORR` /
`REG`），方法本身领域无关，适用于农业田间试验、医学、心理、工程、金融等。

## 何时启用

当用户提出以下需求时加载本 Skill：

- 方差分析 / ANOVA（单因素、双因素含交互）
- 混合模型 / 随机效应（区组、重复测量）
- 多重比较：Tukey HSD、Dunnett（各处理 vs 对照）
- t 检验（独立 / 配对）、相关分析、多元线性回归
- 提到 SAS 的 `PROC GLM/MIXED/MEANS/REG/CORR/ANOVA`，想要免费、合规的结果

## 两种运行方式

### A. MCP 工具（若 `stats-mcp` MCP 已连接，优先用）

直接调用 MCP 工具：`describe` / `oneway_anova` / `twoway_anova` /
`mixed_model` / `tukey_hsd_test` / `dunnett_test` / `ttest` / `correlation` /
`linear_regression`。

### B. CLI 兜底（无需配置 MCP，任意装了依赖的 Python 均可）

通过 Bash 运行本 Skill 自带的脚本（路径相对于本 Skill 目录解析）：

```bash
python <skill_dir>/scripts/stats_cli.py oneway_anova \
    --csv data/sample_field_trial.csv --group_col variety --value_col yield
```

常见调用：

```bash
# 描述性统计
python <skill_dir>/scripts/stats_cli.py describe --csv data.csv --cols yield,height

# 单因素 ANOVA + Tukey
python <skill_dir>/scripts/stats_cli.py oneway_anova --csv data.csv --group_col trt --value_col yield

# 双因素 ANOVA（含交互）
python <skill_dir>/scripts/stats_cli.py twoway_anova --csv data.csv --factor_cols trt,block --value_col yield

# 线性混合模型（随机截距=区组）
python <skill_dir>/scripts/stats_cli.py mixed_model --csv data.csv --value_col yield --fixed_cols trt --random_intercept_col block

# Dunnett（对照=A）
python <skill_dir>/scripts/stats_cli.py dunnett_test --csv data.csv --group_col trt --value_col yield --control A

# t 检验（配对加 --paired）
python <skill_dir>/scripts/stats_cli.py ttest --csv data.csv --group_col group --value_col yield

# 相关 / 回归
python <skill_dir>/scripts/stats_cli.py correlation --csv data.csv --cols yield,height
python <skill_dir>/scripts/stats_cli.py linear_regression --csv data.csv --y_col yield --x_cols height,nitrogen
```

## 意图 → 工具映射

| 用户说 | 工具 | SAS 对应 |
|--------|------|----------|
| 描述统计 / 均值标准差 | `describe` | `PROC MEANS` |
| 单因素方差分析 | `oneway_anova` + Tukey | `PROC GLM` |
| 双因素（交互）方差分析 | `twoway_anova` | `PROC GLM` |
| 随机区组 / 混合模型 | `mixed_model` | `PROC MIXED` |
| 多重比较（两两） | `tukey_hsd_test` | `MEANS / TUKEY` |
| 各处理 vs 对照 | `dunnett_test` | `MEANS / DUNNETT` |
| 两组比较 | `ttest` | `PROC TTEST` |
| 相关系数 | `correlation` | `PROC CORR` |
| 回归 | `linear_regression` | `PROC REG` |

## 使用要点

- **输入**：CSV 或 XLSX。把数据放进本 Skill 的 `data/` 目录，或传绝对路径。
- **输出**：返回摘要文本，并在 `out/` 写入完整报告（含路径）。
- **工作目录**：默认本 Skill 所在目录；可用环境变量 `STATS_MCP_DIR` 覆盖。
- **依赖**：`pip install -r requirements.txt`（`mcp` 已锁 `<2`）。

## 首次接入 MCP（可选）

```bash
pip install -r requirements.txt
python <skill_dir>/scripts/install_mcp.py
```

然后在工作区连接器管理页对 `stats-mcp` 点「信任」，即可用方式 A 调用工具。
