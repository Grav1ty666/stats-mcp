# stats-mcp

A local, license-clean **Model Context Protocol (MCP)** server that exposes
common statistical-analysis tools as callable MCP tools. It works as a free,
legitimate replacement for a SAS-backed MCP, and covers the SAS procedures
most used in field-trial / biostatistics / general statistical workflows —
`PROC MEANS`, `PROC GLM`, `PROC MIXED`, `PROC ANOVA`, `PROC CORR`, `PROC REG`,
plus multiple-comparison tests (Tukey / Dunnett).

The statistical methods are **domain-agnostic**: ANOVA, mixed models,
multiple comparisons, t-tests, correlation and regression apply equally to
agriculture, medicine, psychology, engineering, finance, etc. The `agri`
framing in the examples is only one use case.

## Tools

| MCP tool            | SAS equivalent            | Purpose                                  |
|---------------------|--------------------------|------------------------------------------|
| `describe`          | `PROC MEANS`             | Descriptive statistics                   |
| `oneway_anova`      | `PROC GLM / ANOVA`       | One-way ANOVA (+ Tukey post-hoc)         |
| `twoway_anova`      | `PROC GLM`               | Two-way factorial ANOVA (with interaction) |
| `mixed_model`       | `PROC MIXED`             | Linear mixed model, random intercept     |
| `tukey_hsd_test`    | `MEANS ... / TUKEY`      | Tukey HSD all-pairs comparison          |
| `dunnett_test`      | `MEANS ... / DUNNETT`    | Each treatment vs. a control             |
| `ttest`             | `PROC TTEST`             | Two-sample / paired t-test               |
| `correlation`       | `PROC CORR`              | Correlation matrix                       |
| `linear_regression` | `PROC REG`               | OLS multiple regression                  |

## Install

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> ⚠️ `requirements.txt` pins `mcp<2` on purpose: the `FastMCP` API changed in
> `mcp>=2.0`. Keep the v1.x line for this server.

## Run (stdio)

```bash
python server.py
```

The server speaks the MCP stdio protocol, so you normally don't run it
directly — your MCP host launches it.

## Connect to an MCP host

Add the server to your host's MCP config (see `mcp-config-example.json`):

```json
{
  "mcpServers": {
    "stats-mcp": {
      "command": "python",
      "args": ["/absolute/path/to/stats-mcp/server.py"]
    }
  }
}
```

- **WorkBuddy**: merge the entry into `~/.workbuddy/mcp.json`, then open the
  connector management page and click **Trust** on `stats-mcp`.
- **Claude Desktop / Cursor**: put the same entry in their `mcp.json`.

Point `command` at a Python that has the dependencies installed (a managed
Python venv works well).

## Data & output

- Drop a CSV/XLSX in the server's `data/` directory (or pass an absolute
  path). An example, `data/sample_field_trial.csv` (3 varieties × 3 blocks ×
  2 reps), is included.
- Each run writes a full text report to `out/` and returns a summary to the
  agent.
- Override the working directory (where `data/` and `out/` live) with the
  environment variable `STATS_MCP_DIR` (absolute path). By default it is the
  folder containing `server.py`.

## Example call (for the agent / host)

> "Using `sample_field_trial.csv`, run a one-way ANOVA of `variety` on `yield`;
> if significant, do Tukey HSD."

## License

MIT — see [LICENSE](./LICENSE).
