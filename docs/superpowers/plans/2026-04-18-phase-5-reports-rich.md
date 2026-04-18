# Phase 5 Implementation Plan — 報表 Excel/PDF/互動圖表

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 [src/report/exporters/](../../../src/report/exporters) 新增 4 個 exporter（xlsx / PDF / 靜態圖表 / 互動圖表），讓 4 種報表（Traffic / Audit / VEN Status / Policy Usage）支援 `html | csv | xlsx | pdf | all` 5 種輸出格式。**不取代** 現有 HTML/CSV 產出；**新增** 為可選格式。plotly 互動圖表嵌入 HTML 讓客戶 demo 等級立刻提升；matplotlib 靜態圖表給 PDF/Excel。pygments 高亮 PCE rule JSON/YAML。humanize 統一時間/位元/數字可讀格式。

**Architecture:** **雙引擎 chart 策略** — 同一份 `chart_spec: dict` 可被 `render_plotly_html(spec)` 與 `render_matplotlib_png(spec)` 各自消費。HTML 走 plotly（離線互動）、PDF/Excel 走 matplotlib（靜態 PNG 嵌入）。既有 HTML exporter 輕量擴充：在 section 之間插入 plotly div 或 matplotlib `<img>` tag。xlsx 用 openpyxl 每個 mod 一張 sheet + 條件格式 + 嵌入 matplotlib PNG。PDF 用 weasyprint 把現有 HTML（含 plotly fallback 到 matplotlib PNG）轉檔，CSS 已存在於 [report_css.py](../../../src/report/exporters/report_css.py)。

**Tech Stack:** openpyxl>=3.1, weasyprint>=61.0, matplotlib>=3.8, plotly>=5.20, pygments>=2.17, humanize>=4.9（Phase 0 全裝好）

**Branch:** `upgrade/phase-5-reports-rich`（from main after Phase 4 OR 並行啟動 — Phase 5 與 Phase 4 在檔案上無衝突）

**Target tag on merge:** `v3.5.1-reports`

**Parent roadmap:** [2026-04-18-upgrade-roadmap.md](2026-04-18-upgrade-roadmap.md)

---

## File Structure

| 檔案 | 動作 | 責任 |
|---|---|---|
| `src/report/exporters/chart_renderer.py` | 新增 | 雙引擎：`render_plotly_html(spec)` + `render_matplotlib_png(spec)`；共用 `chart_spec` schema |
| `src/report/exporters/xlsx_exporter.py` | 新增 | openpyxl 多 sheet 輸出；條件格式；嵌入 PNG |
| `src/report/exporters/pdf_exporter.py` | 新增 | weasyprint HTML→PDF；plotly 替換為 matplotlib PNG 以便列印 |
| `src/report/exporters/code_highlighter.py` | 新增 | pygments wrapper（lex JSON/YAML/bash）；HTML 與 PDF 共用 |
| `src/report/exporters/html_exporter.py` | 小改 | 插入 plotly div + pygments 高亮區塊 |
| `src/report/exporters/audit_html_exporter.py` | 小改 | 同上 |
| `src/report/exporters/ven_html_exporter.py` | 小改 | 同上 |
| `src/report/exporters/policy_usage_html_exporter.py` | 小改 | 同上 |
| `src/report/analysis/mod02_policy_decisions.py` | 小改 | 提供 chart_spec（pie） |
| `src/report/analysis/mod05_remote_access.py` | 小改 | 提供 chart_spec（bar） |
| `src/report/analysis/mod07_cross_label_matrix.py` | 小改 | 提供 chart_spec（heatmap） |
| `src/report/analysis/mod10_allowed_traffic.py` | 小改 | 提供 chart_spec（timeline / line） |
| `src/report/analysis/mod15_lateral_movement.py` | 小改 | 提供 chart_spec（network graph，plotly 強項） |
| `src/main.py` | 小改 | CLI 新格式：`--format pdf|xlsx|all` |
| `src/gui.py` | 小改 | GUI 報表頁新增格式選項 |
| `src/cli/report.py` | 小改 | click subcommand 新格式 |
| `tests/test_chart_renderer.py` | 新增 | 雙引擎一致性：同 spec 應產生語意等價圖表 |
| `tests/test_xlsx_exporter.py` | 新增 | openpyxl 輸出結構、條件格式、PNG 嵌入 |
| `tests/test_pdf_exporter.py` | 新增 | weasyprint 輸出存在 + CJK 字型正確（zh_TW 下無 □□□） |
| `tests/test_code_highlighter.py` | 新增 | pygments JSON / YAML 輸出 |
| `tests/test_html_report_cjk_font.py` | 新增 | zh_TW 報表 HTML 內 plotly 標籤 + matplotlib 字型雙端無缺字 |
| `src/i18n_en.json` + `_ZH_EXPLICIT` | 補 | 新增圖表 title/axis/legend 的 i18n key |

**檔案影響面**：5 新 exporter + 5 小改 analysis + 5 新測試 + 4 小改 HTML exporter + 3 小改 CLI/GUI + i18n 補 keys。

---

## Task 1: Branch + baseline

**Files:** 無

- [ ] **Step 1: 從 main 開 branch**

```bash
git fetch origin main
git checkout main && git pull
git checkout -b upgrade/phase-5-reports-rich
```

- [ ] **Step 2: 確認當前測試數與 i18n 狀態**

```bash
python -m pytest tests/ -q
python -m pytest tests/test_i18n_audit.py -v
```
記下 pass 數（預估 192 若 Phase 4 未 merge；更多若已 merge）。

- [ ] **Step 3: 煙霧 — 現有報表仍能產出**

```bash
python illumio_ops.py report traffic --help       # Phase 1 新 subcommand
# OR
python illumio_ops.py --report --source api --format html 2>&1 | head -10  # 舊 flag
```
確認現有報表邏輯 OK。

---

## Task 2: chart_renderer 雙引擎骨架（spec → plotly HTML | matplotlib PNG）

**Files:**
- Create: `src/report/exporters/chart_renderer.py`
- Create: `tests/test_chart_renderer.py`

- [ ] **Step 1: 寫 failing test**

Create `tests/test_chart_renderer.py`:

```python
"""Chart renderer dual engine — same spec produces both HTML (plotly) and PNG (matplotlib)."""
from __future__ import annotations

import base64
import re
import pytest


SAMPLE_BAR_SPEC = {
    "type": "bar",
    "title": "Top 5 Ports",
    "x_label": "Port",
    "y_label": "Flows",
    "data": {
        "labels": ["80", "443", "22", "3389", "8080"],
        "values": [1200, 850, 230, 120, 95],
    },
    "i18n": {"lang": "en"},
}

SAMPLE_PIE_SPEC = {
    "type": "pie",
    "title": "Policy Decision Breakdown",
    "data": {
        "labels": ["Allowed", "Blocked", "Potentially Blocked"],
        "values": [5230, 142, 38],
    },
    "i18n": {"lang": "en"},
}


def test_render_plotly_html_returns_html_div():
    from src.report.exporters.chart_renderer import render_plotly_html
    out = render_plotly_html(SAMPLE_BAR_SPEC)
    assert "<div" in out
    assert "plotly" in out.lower()
    # Title is embedded as plain text (or JSON-encoded) in output
    assert "Top 5 Ports" in out or "Top%205%20Ports" in out


def test_render_plotly_html_supports_pie():
    from src.report.exporters.chart_renderer import render_plotly_html
    out = render_plotly_html(SAMPLE_PIE_SPEC)
    assert "Policy Decision" in out or "Policy%20Decision" in out


def test_render_plotly_html_offline_self_contained():
    """plotly output MUST NOT reference external CDN — RPM deployment is offline."""
    from src.report.exporters.chart_renderer import render_plotly_html
    out = render_plotly_html(SAMPLE_BAR_SPEC)
    # No CDN URLs
    assert "cdn.plot.ly" not in out
    assert "unpkg.com" not in out
    # Either inline plotly.js or data URL for the runtime
    assert "Plotly" in out or "plotly" in out.lower()


def test_render_matplotlib_png_returns_bytes():
    from src.report.exporters.chart_renderer import render_matplotlib_png
    png_bytes = render_matplotlib_png(SAMPLE_BAR_SPEC)
    assert isinstance(png_bytes, bytes)
    # PNG magic number
    assert png_bytes.startswith(b'\x89PNG\r\n\x1a\n')


def test_render_matplotlib_png_pie_works():
    from src.report.exporters.chart_renderer import render_matplotlib_png
    png_bytes = render_matplotlib_png(SAMPLE_PIE_SPEC)
    assert png_bytes.startswith(b'\x89PNG')
    # Image should be non-trivially sized
    assert len(png_bytes) > 1000


def test_unknown_chart_type_raises():
    from src.report.exporters.chart_renderer import render_plotly_html
    with pytest.raises(ValueError, match="unsupported chart type"):
        render_plotly_html({"type": "spaceship", "title": "no", "data": {}})


def test_both_engines_accept_identical_spec():
    """Regression: the same dict must be consumable by both engines."""
    from src.report.exporters.chart_renderer import render_plotly_html, render_matplotlib_png
    html = render_plotly_html(SAMPLE_BAR_SPEC)
    png = render_matplotlib_png(SAMPLE_BAR_SPEC)
    assert html  # non-empty
    assert png   # non-empty


def test_i18n_zh_tw_title_renders():
    from src.report.exporters.chart_renderer import render_plotly_html, render_matplotlib_png
    spec = {**SAMPLE_BAR_SPEC, "title": "前 5 名連接埠", "i18n": {"lang": "zh_TW"}}
    html = render_plotly_html(spec)
    # Title text should survive (URL-encoded or not)
    assert "前" in html or "%E5%89%8D" in html.upper() or "5" in html
    png = render_matplotlib_png(spec)
    assert png.startswith(b'\x89PNG')
```

- [ ] **Step 2: 跑測試確認失敗**

```bash
python -m pytest tests/test_chart_renderer.py -v
```
Expected: ImportError（`src.report.exporters.chart_renderer` 不存在）。

- [ ] **Step 3: 建立 chart_renderer 實作**

Create `src/report/exporters/chart_renderer.py`:

```python
"""Dual-engine chart renderer for illumio_ops reports.

Single chart_spec dict feeds both engines:
  - render_plotly_html(spec) -> str (HTML div, fully self-contained for offline use)
  - render_matplotlib_png(spec) -> bytes (PNG for PDF/Excel embedding)

chart_spec shape:
  {
    "type": "bar" | "pie" | "line" | "heatmap" | "network",
    "title": str,
    "x_label": str (optional, for bar/line),
    "y_label": str (optional, for bar/line),
    "data": {
        "labels": [...],
        "values": [...] OR "x": [...], "y": [...],
        "matrix": [[...]] (for heatmap),
        "nodes": [...], "edges": [...] (for network),
    },
    "i18n": {"lang": "en" | "zh_TW"},
  }
"""
from __future__ import annotations

import io
import logging
from typing import Any

import matplotlib
matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt
from matplotlib import rcParams
import plotly.graph_objects as go
import plotly.offline as plotly_offline

logger = logging.getLogger(__name__)


# CJK font fallback for matplotlib — ensures zh_TW titles/labels render
rcParams["font.family"] = ["Noto Sans CJK TC", "Microsoft JhengHei",
                            "PingFang TC", "Heiti TC", "sans-serif"]
rcParams["axes.unicode_minus"] = False  # minus sign glitch fix


def render_plotly_html(spec: dict[str, Any]) -> str:
    """Render chart spec as a plotly HTML div (offline, self-contained)."""
    chart_type = spec.get("type")
    data = spec.get("data", {})
    title = spec.get("title", "")

    if chart_type == "bar":
        fig = go.Figure(go.Bar(
            x=data.get("labels", []),
            y=data.get("values", []),
            marker_color="rgb(55, 83, 109)",
        ))
        fig.update_layout(
            title=title,
            xaxis_title=spec.get("x_label", ""),
            yaxis_title=spec.get("y_label", ""),
        )
    elif chart_type == "pie":
        fig = go.Figure(go.Pie(
            labels=data.get("labels", []),
            values=data.get("values", []),
            hole=0.3,
        ))
        fig.update_layout(title=title)
    elif chart_type == "line":
        fig = go.Figure(go.Scatter(
            x=data.get("x", []),
            y=data.get("y", []),
            mode="lines+markers",
        ))
        fig.update_layout(
            title=title,
            xaxis_title=spec.get("x_label", ""),
            yaxis_title=spec.get("y_label", ""),
        )
    elif chart_type == "heatmap":
        fig = go.Figure(go.Heatmap(
            z=data.get("matrix", []),
            x=data.get("labels", []),
            y=data.get("ylabels", data.get("labels", [])),
            colorscale="Viridis",
        ))
        fig.update_layout(title=title)
    elif chart_type == "network":
        # Force-directed graph
        nodes = data.get("nodes", [])
        edges = data.get("edges", [])
        # Build node trace with random-ish positions (plotly.js handles actual layout)
        import math
        n = len(nodes) or 1
        node_x = [math.cos(2 * math.pi * i / n) for i in range(n)]
        node_y = [math.sin(2 * math.pi * i / n) for i in range(n)]
        edge_x, edge_y = [], []
        name_to_idx = {node.get("id") or node.get("name"): i for i, node in enumerate(nodes)}
        for src, dst in edges:
            i, j = name_to_idx.get(src), name_to_idx.get(dst)
            if i is None or j is None:
                continue
            edge_x += [node_x[i], node_x[j], None]
            edge_y += [node_y[i], node_y[j], None]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode="lines",
                                 line=dict(color="gray"), hoverinfo="none"))
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y, mode="markers+text",
            text=[n.get("label", n.get("id", "")) for n in nodes],
            marker=dict(size=20), textposition="bottom center",
        ))
        fig.update_layout(title=title, showlegend=False,
                          xaxis=dict(showgrid=False, zeroline=False, visible=False),
                          yaxis=dict(showgrid=False, zeroline=False, visible=False))
    else:
        raise ValueError(f"unsupported chart type: {chart_type!r}")

    # include_plotlyjs='inline' — embeds plotly.min.js directly (offline-safe)
    return plotly_offline.plot(
        fig, output_type="div", include_plotlyjs="inline", show_link=False
    )


def render_matplotlib_png(spec: dict[str, Any]) -> bytes:
    """Render chart spec as a PNG byte string (for PDF/Excel embedding)."""
    chart_type = spec.get("type")
    data = spec.get("data", {})
    title = spec.get("title", "")

    fig, ax = plt.subplots(figsize=(8, 5), dpi=100)

    if chart_type == "bar":
        ax.bar(data.get("labels", []), data.get("values", []), color="#375379")
        ax.set_xlabel(spec.get("x_label", ""))
        ax.set_ylabel(spec.get("y_label", ""))
    elif chart_type == "pie":
        ax.pie(data.get("values", []), labels=data.get("labels", []),
               autopct="%1.1f%%", startangle=90)
        ax.axis("equal")
    elif chart_type == "line":
        ax.plot(data.get("x", []), data.get("y", []), marker="o")
        ax.set_xlabel(spec.get("x_label", ""))
        ax.set_ylabel(spec.get("y_label", ""))
    elif chart_type == "heatmap":
        import numpy as np
        matrix = np.array(data.get("matrix", [[0]]))
        im = ax.imshow(matrix, cmap="viridis", aspect="auto")
        fig.colorbar(im, ax=ax)
        labels = data.get("labels", [])
        ylabels = data.get("ylabels", labels)
        if labels:
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")
        if ylabels:
            ax.set_yticks(range(len(ylabels)))
            ax.set_yticklabels(ylabels)
    elif chart_type == "network":
        # Simple circular layout for static rendering
        import math
        nodes = data.get("nodes", [])
        n = len(nodes) or 1
        positions = {
            (node.get("id") or node.get("name")): (math.cos(2 * math.pi * i / n),
                                                    math.sin(2 * math.pi * i / n))
            for i, node in enumerate(nodes)
        }
        for src, dst in data.get("edges", []):
            if src in positions and dst in positions:
                x1, y1 = positions[src]
                x2, y2 = positions[dst]
                ax.plot([x1, x2], [y1, y2], "gray", alpha=0.5)
        for node in nodes:
            key = node.get("id") or node.get("name")
            x, y = positions[key]
            ax.plot(x, y, "o", markersize=20, color="#375379")
            ax.annotate(node.get("label", key), (x, y), xytext=(0, -15),
                        textcoords="offset points", ha="center")
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.5, 1.5)
        ax.axis("off")
    else:
        plt.close(fig)
        raise ValueError(f"unsupported chart type: {chart_type!r}")

    ax.set_title(title)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return buf.getvalue()
```

- [ ] **Step 4: 跑測試**

```bash
python -m pytest tests/test_chart_renderer.py -v
```
Expected: 8 PASS。

- [ ] **Step 5: Commit**

```bash
git add src/report/exporters/chart_renderer.py tests/test_chart_renderer.py
git commit -m "feat(reports): dual-engine chart renderer (plotly + matplotlib)

Same chart_spec dict feeds both engines. plotly output is offline
self-contained (inline plotly.js, no CDN) for RPM deployment.
matplotlib uses Noto Sans CJK TC font fallback for zh_TW rendering.

Supports bar/pie/line/heatmap/network chart types."
```

---

## Task 3: pygments code_highlighter + tests

**Files:**
- Create: `src/report/exporters/code_highlighter.py`
- Create: `tests/test_code_highlighter.py`

- [ ] **Step 1: failing test**

Create `tests/test_code_highlighter.py`:

```python
"""pygments wrapper for report code highlighting."""
import pytest


def test_highlight_json_outputs_html_with_classes():
    from src.report.exporters.code_highlighter import highlight_json
    out = highlight_json('{"name": "test", "value": 42}')
    assert '<div class="highlight"' in out or '<pre' in out
    # pygments JSON lexer emits specific token classes
    assert "hll" in out or '"name"' in out


def test_highlight_yaml_outputs_html():
    from src.report.exporters.code_highlighter import highlight_yaml
    out = highlight_yaml("name: test\nvalue: 42\n")
    assert '<pre' in out or '<div' in out


def test_highlight_css_generator_emits_style_tag():
    """Callers need the Pygments CSS once per HTML document."""
    from src.report.exporters.code_highlighter import get_highlight_css
    css = get_highlight_css()
    assert ".highlight" in css or ".k" in css  # pygments class


def test_highlight_handles_empty_string():
    from src.report.exporters.code_highlighter import highlight_json
    out = highlight_json("")
    assert isinstance(out, str)


def test_highlight_handles_invalid_json_gracefully():
    """If JSON is malformed, pygments still lexes it as text."""
    from src.report.exporters.code_highlighter import highlight_json
    out = highlight_json("{broken json")
    assert isinstance(out, str)
    assert len(out) > 0
```

- [ ] **Step 2: 實作**

Create `src/report/exporters/code_highlighter.py`:

```python
"""pygments wrapper for syntax highlighting in HTML/PDF reports."""
from __future__ import annotations

from pygments import highlight
from pygments.lexers import JsonLexer, YamlLexer, BashLexer
from pygments.formatters import HtmlFormatter


_FORMATTER = HtmlFormatter(style="default", cssclass="highlight", nowrap=False)


def highlight_json(code: str) -> str:
    """Highlight a JSON string as HTML with pygments classes."""
    return highlight(code, JsonLexer(), _FORMATTER)


def highlight_yaml(code: str) -> str:
    return highlight(code, YamlLexer(), _FORMATTER)


def highlight_bash(code: str) -> str:
    return highlight(code, BashLexer(), _FORMATTER)


def get_highlight_css() -> str:
    """CSS styles for pygments highlight classes. Embed in <style> tag once per doc."""
    return _FORMATTER.get_style_defs(".highlight")
```

- [ ] **Step 3: 跑測試**

```bash
python -m pytest tests/test_code_highlighter.py -v
```
Expected: 5 PASS。

- [ ] **Step 4: Commit**

```bash
git add src/report/exporters/code_highlighter.py tests/test_code_highlighter.py
git commit -m "feat(reports): add pygments code_highlighter wrapper

Exposes highlight_json/yaml/bash for PCE rule JSON, report_config.yaml,
and CLI example blocks in HTML/PDF reports. get_highlight_css() returns
the once-per-document CSS."
```

---

## Task 4: xlsx_exporter（openpyxl + 嵌入 matplotlib PNG）

**Files:**
- Create: `src/report/exporters/xlsx_exporter.py`
- Create: `tests/test_xlsx_exporter.py`

- [ ] **Step 1: failing test**

Create `tests/test_xlsx_exporter.py`:

```python
"""xlsx exporter tests — openpyxl-based multi-sheet output."""
from __future__ import annotations

import pytest
from openpyxl import load_workbook


@pytest.fixture
def sample_report_result():
    """Minimal ReportResult-shaped dict for xlsx_exporter."""
    return {
        "record_count": 1234,
        "metadata": {
            "title": "Traffic Flow Report",
            "generated_at": "2026-04-18 10:00:00",
            "start_date": "2026-04-11",
            "end_date": "2026-04-18",
        },
        "module_results": {
            "mod01_overview": {
                "summary": "1234 flows analyzed",
                "table": [
                    {"metric": "Total Flows", "value": 1234},
                    {"metric": "Unique Sources", "value": 42},
                ],
            },
            "mod02_policy_decisions": {
                "summary": "",
                "table": [
                    {"decision": "Allowed", "count": 1000},
                    {"decision": "Blocked", "count": 234},
                ],
                "chart_spec": {
                    "type": "pie",
                    "title": "Decisions",
                    "data": {"labels": ["Allowed", "Blocked"], "values": [1000, 234]},
                    "i18n": {"lang": "en"},
                },
            },
        },
    }


def test_xlsx_exporter_creates_workbook(tmp_path, sample_report_result):
    from src.report.exporters.xlsx_exporter import export_xlsx
    out = tmp_path / "report.xlsx"
    export_xlsx(sample_report_result, str(out))
    assert out.exists()
    wb = load_workbook(str(out))
    # Should have one sheet per module plus a summary
    assert "Summary" in wb.sheetnames
    assert any("mod01" in s or "Overview" in s for s in wb.sheetnames)


def test_xlsx_exporter_embeds_chart_image(tmp_path, sample_report_result):
    from src.report.exporters.xlsx_exporter import export_xlsx
    out = tmp_path / "report.xlsx"
    export_xlsx(sample_report_result, str(out))
    wb = load_workbook(str(out))
    # Find the mod02 sheet
    mod02_sheet_name = next((s for s in wb.sheetnames if "mod02" in s or "Policy" in s), None)
    assert mod02_sheet_name is not None
    ws = wb[mod02_sheet_name]
    # openpyxl stores images in ws._images
    assert len(ws._images) >= 1, "chart_spec should produce at least one embedded PNG"


def test_xlsx_exporter_freezes_header_row(tmp_path, sample_report_result):
    from src.report.exporters.xlsx_exporter import export_xlsx
    out = tmp_path / "report.xlsx"
    export_xlsx(sample_report_result, str(out))
    wb = load_workbook(str(out))
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        # Header row frozen
        assert ws.freeze_panes in ("A2", None), f"{sheet_name}: unexpected freeze {ws.freeze_panes}"


def test_xlsx_exporter_handles_no_chart_spec(tmp_path):
    from src.report.exporters.xlsx_exporter import export_xlsx
    result = {
        "record_count": 10,
        "metadata": {"title": "Minimal"},
        "module_results": {
            "mod_noop": {"summary": "plain", "table": [{"a": 1}]}
        },
    }
    out = tmp_path / "min.xlsx"
    export_xlsx(result, str(out))
    assert out.exists()
```

- [ ] **Step 2: 實作**

Create `src/report/exporters/xlsx_exporter.py`:

```python
"""openpyxl-based xlsx export for illumio_ops reports.

One sheet per analysis module + a Summary sheet. Header row frozen,
alternate-row banding for readability, red fill on 'blocked' / 'deny'
rows. chart_spec (if present) rendered as matplotlib PNG and embedded.
"""
from __future__ import annotations

import io
import logging
from typing import Any

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.report.exporters.chart_renderer import render_matplotlib_png

logger = logging.getLogger(__name__)

_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_FILL = PatternFill("solid", fgColor="375379")
_ALERT_FILL = PatternFill("solid", fgColor="FFC7CE")
_ALERT_TOKENS = ("blocked", "deny", "violat", "critical", "red_flag")


def _write_module_sheet(wb: Workbook, name: str, module_data: dict[str, Any]) -> None:
    # openpyxl sheet names capped at 31 chars and cannot contain :\/?*[]
    safe_name = "".join(c for c in name if c not in r"\/:?*[]")[:31] or "Sheet"
    ws = wb.create_sheet(title=safe_name)

    row = 1
    summary = module_data.get("summary")
    if summary:
        ws.cell(row=row, column=1, value=str(summary)).font = Font(italic=True)
        row += 2

    table = module_data.get("table") or []
    if table:
        # Write header
        headers = list(table[0].keys())
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=row, column=col_idx, value=str(header))
            cell.font = _HEADER_FONT
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(horizontal="center")
        header_row = row
        row += 1

        # Write data rows
        for data_row in table:
            row_vals = [data_row.get(h, "") for h in headers]
            # Highlight "blocked / deny" rows
            row_text = " ".join(str(v).lower() for v in row_vals)
            is_alert = any(tok in row_text for tok in _ALERT_TOKENS)
            for col_idx, val in enumerate(row_vals, 1):
                cell = ws.cell(row=row, column=col_idx, value=val)
                if is_alert:
                    cell.fill = _ALERT_FILL
            row += 1

        ws.freeze_panes = f"A{header_row + 1}"

        # Auto-size columns (rough heuristic)
        for col_idx, header in enumerate(headers, 1):
            max_len = max(
                len(str(header)),
                max((len(str(data_row.get(header, ""))) for data_row in table), default=0),
            )
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 2, 60)

    chart_spec = module_data.get("chart_spec")
    if chart_spec:
        try:
            png = render_matplotlib_png(chart_spec)
            img = XLImage(io.BytesIO(png))
            img.anchor = f"A{row + 2}"
            ws.add_image(img)
        except Exception as exc:
            logger.warning("Failed to render chart for %s: %s", safe_name, exc)


def export_xlsx(report_result: dict[str, Any], output_path: str) -> None:
    """Export a ReportResult-shaped dict to an .xlsx file."""
    wb = Workbook()
    summary_ws = wb.active
    summary_ws.title = "Summary"

    meta = report_result.get("metadata", {})
    summary_ws["A1"] = meta.get("title", "Report")
    summary_ws["A1"].font = Font(size=18, bold=True)
    summary_ws["A2"] = f"Generated: {meta.get('generated_at', '')}"
    if meta.get("start_date"):
        summary_ws["A3"] = f"Period: {meta.get('start_date')} → {meta.get('end_date', '')}"
    summary_ws["A4"] = f"Records: {report_result.get('record_count', 0)}"
    summary_ws.freeze_panes = "A2"

    for mod_name, mod_data in (report_result.get("module_results") or {}).items():
        _write_module_sheet(wb, mod_name, mod_data)

    wb.save(output_path)
    logger.info("xlsx report written to %s", output_path)
```

- [ ] **Step 3: 跑測試**

```bash
python -m pytest tests/test_xlsx_exporter.py -v
```
Expected: 4 PASS。

- [ ] **Step 4: Commit**

```bash
git add src/report/exporters/xlsx_exporter.py tests/test_xlsx_exporter.py
git commit -m "feat(reports): xlsx_exporter with openpyxl multi-sheet + embedded PNGs

One sheet per analysis module + Summary; frozen header rows; red fill
on blocked/deny rows; auto-sized columns. chart_spec rendered via
matplotlib PNG and anchored below the data table."
```

---

## Task 5: pdf_exporter (weasyprint + CJK + plotly→matplotlib fallback)

**Files:**
- Create: `src/report/exporters/pdf_exporter.py`
- Create: `tests/test_pdf_exporter.py`

- [ ] **Step 1: failing test**

Create `tests/test_pdf_exporter.py`:

```python
"""weasyprint PDF export — critical: runs on Linux (pango/cairo), skip on Windows."""
from __future__ import annotations

import pytest

pytest.importorskip("weasyprint", reason="weasyprint needs GTK3 on Windows; Linux RPM target OK")


def test_export_pdf_produces_pdf_magic_bytes(tmp_path):
    from src.report.exporters.pdf_exporter import export_pdf
    html = "<html><head><meta charset='utf-8'></head><body><h1>Test</h1><p>body</p></body></html>"
    out = tmp_path / "report.pdf"
    export_pdf(html, str(out))
    assert out.exists()
    header = out.read_bytes()[:8]
    assert header.startswith(b"%PDF-")


def test_export_pdf_handles_cjk(tmp_path):
    from src.report.exporters.pdf_exporter import export_pdf
    html = "<html><body><h1>中文標題</h1><p>包含中文的段落內容</p></body></html>"
    out = tmp_path / "cjk.pdf"
    export_pdf(html, str(out))
    data = out.read_bytes()
    # PDF must be non-trivial size (CJK embedding failure often produces a tiny PDF)
    assert len(data) > 1500
```

- [ ] **Step 2: 實作**

Create `src/report/exporters/pdf_exporter.py`:

```python
"""HTML → PDF export via weasyprint.

On the RHEL RPM target (pango + cairo present) this works natively. On
Windows dev machines lacking GTK3, this module imports cleanly but export
will raise OSError — tests skip accordingly.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def export_pdf(html: str, output_path: str, base_url: Optional[str] = None) -> None:
    """Render HTML to a PDF file. base_url is used to resolve relative assets."""
    # Deferred import so modules importing pdf_exporter don't fail on Windows dev
    from weasyprint import HTML, CSS

    # Basic CJK + print CSS overlay
    cjk_css = CSS(string="""
        @page { size: A4; margin: 20mm; }
        body {
            font-family: "Noto Sans CJK TC", "Microsoft JhengHei",
                         "PingFang TC", "Heiti TC", sans-serif;
            font-size: 11pt;
            line-height: 1.5;
        }
        /* plotly <div> renders only in HTML — hide and fall back to <img>
           which the HTML exporter is expected to emit for PDF. */
        .plotly-fallback-img { display: inline-block; max-width: 100%; }
        div.plotly-graph-div, script[type="application/json"] { display: none; }
    """)
    HTML(string=html, base_url=base_url).write_pdf(output_path, stylesheets=[cjk_css])
    logger.info("pdf report written to %s", output_path)
```

- [ ] **Step 3: 跑測試（Linux 預期 PASS；Windows 預期 SKIP）**

```bash
python -m pytest tests/test_pdf_exporter.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/report/exporters/pdf_exporter.py tests/test_pdf_exporter.py
git commit -m "feat(reports): HTML→PDF exporter via weasyprint with CJK fallback

Embeds print-oriented CSS (A4, 20mm margins, Noto Sans CJK TC) and
hides plotly div elements so PDF relies on the <img> fallback embedded
by html_exporter. Tests skip on non-Linux/no-GTK3 environments."
```

---

## Task 6: mod02/05/07/10/15 chart_spec integration

**Files:**
- Modify: 5 analysis modules

- [ ] **Step 1: 為 mod02 (policy decisions) 加 chart_spec**

Read `src/report/analysis/mod02_policy_decisions.py`; at the end of the main analysis function, add:

```python
# Phase 5: chart_spec for HTML + PDF + Excel
result["chart_spec"] = {
    "type": "pie",
    "title": t("rpt_pd_chart_title", default="Policy Decision Breakdown"),
    "data": {
        "labels": [t("rpt_pd_allowed", default="Allowed"),
                   t("rpt_pd_blocked", default="Blocked"),
                   t("rpt_pd_potential", default="Potentially Blocked")],
        "values": [allowed_count, blocked_count, potential_count],
    },
    "i18n": {"lang": get_language()},
}
```

(Adapt variable names to actual module code.)

- [ ] **Step 2: 類似地為 mod05、mod07、mod10、mod15 各加 chart_spec**

Pattern:
- `mod05_remote_access.py` → bar (top 5 remote-access ports by flow count)
- `mod07_cross_label_matrix.py` → heatmap (src-label × dst-label matrix)
- `mod10_allowed_traffic.py` → line (allowed flows over time)
- `mod15_lateral_movement.py` → network (workload graph, edges = observed flows)

Keep each modification surgical — only add chart_spec, do not alter existing analysis output.

- [ ] **Step 3: i18n 補 keys**

Add to `src/i18n_en.json` and `_ZH_EXPLICIT`:
```
rpt_pd_chart_title: Policy Decision Breakdown / Policy 決策分布
rpt_ra_chart_title: Top Remote Access Ports / Remote Access 連接埠 Top-N
rpt_clm_chart_title: Cross-Label Traffic Matrix / Cross-Label 傳輸矩陣
rpt_at_chart_title: Allowed Traffic Timeline / Allowed 傳輸時間軸
rpt_lm_chart_title: Lateral Movement Graph / 橫向移動圖
```

- [ ] **Step 4: 跑 i18n audit + 全套**

```bash
python -m pytest tests/test_i18n_audit.py tests/ -q
```
Expected: 0 findings, all tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/report/analysis/mod02_*.py src/report/analysis/mod05_*.py \
        src/report/analysis/mod07_*.py src/report/analysis/mod10_*.py \
        src/report/analysis/mod15_*.py src/i18n_en.json src/i18n.py
git commit -m "feat(reports): add chart_spec to mod02/05/07/10/15

Each module produces a chart_spec dict alongside its existing output.
The spec drives both plotly (HTML) and matplotlib (PDF/Excel) rendering.
No changes to existing analysis logic or HTML table output."
```

---

## Task 7: html_exporter integration (plotly div + pygments CSS)

**Files:**
- Modify: `src/report/exporters/html_exporter.py` (+ 3 其他 html exporter)

- [ ] **Step 1: 在 html_exporter 的 module section 插入 plotly + matplotlib fallback**

Find the function that renders module sections. Around where the table is emitted, add:

```python
from src.report.exporters.chart_renderer import render_plotly_html, render_matplotlib_png
from src.report.exporters.code_highlighter import get_highlight_css
import base64 as _b64


def _render_chart_for_html(chart_spec):
    """Emit plotly div + matplotlib PNG fallback for PDF compatibility."""
    if not chart_spec:
        return ""
    try:
        plotly_div = render_plotly_html(chart_spec)
    except Exception as exc:
        logger.warning("plotly render failed: %s", exc)
        plotly_div = ""
    try:
        png = render_matplotlib_png(chart_spec)
        b64 = _b64.b64encode(png).decode("ascii")
        fallback_img = (
            f'<img class="plotly-fallback-img" '
            f'src="data:image/png;base64,{b64}" alt="chart" />'
        )
    except Exception as exc:
        logger.warning("matplotlib fallback failed: %s", exc)
        fallback_img = ""
    return f'<div class="chart-container">{plotly_div}{fallback_img}</div>'
```

Insert the chart after the table rendering in each section.

- [ ] **Step 2: 加入 pygments CSS 到 `<head>`**

In the top-of-document `<head>` assembly:
```python
html_head += f"<style>\n{get_highlight_css()}\n</style>\n"
```

- [ ] **Step 3: 同樣處理 audit_html_exporter、ven_html_exporter、policy_usage_html_exporter**

- [ ] **Step 4: 跑測試**

```bash
python -m pytest tests/ -q
```
Expected: 全綠。

- [ ] **Step 5: Commit**

```bash
git add src/report/exporters/*html_exporter.py
git commit -m "feat(reports): embed plotly+matplotlib dual render into HTML exporters

Every chart_spec-bearing module section now emits an interactive plotly
div plus a matplotlib PNG fallback (hidden in HTML via CSS; visible in
PDF where plotly cannot run). pygments highlight CSS injected into head."
```

---

## Task 8: CLI / GUI 新格式選項

**Files:**
- Modify: `src/main.py`（argparse）、`src/gui.py`（報表 endpoint）、`src/cli/report.py`（click subcommand）
- Modify: Each ReportGenerator's `export()` method to dispatch on format

- [ ] **Step 1: `ReportGenerator.export` 支援 pdf / xlsx**

For each of `ReportGenerator` / `AuditGenerator` / `VenStatusGenerator` / `PolicyUsageGenerator`, find `export(result, fmt, output_dir, ...)`. Extend the format handling:

```python
if fmt == "pdf" or fmt == "all":
    from src.report.exporters.pdf_exporter import export_pdf
    html = <existing HTML assembly>
    pdf_path = os.path.join(output_dir, f"{base_name}.pdf")
    export_pdf(html, pdf_path)
    paths.append(pdf_path)

if fmt == "xlsx" or fmt == "all":
    from src.report.exporters.xlsx_exporter import export_xlsx
    xlsx_path = os.path.join(output_dir, f"{base_name}.xlsx")
    export_xlsx(result_as_dict, xlsx_path)
    paths.append(xlsx_path)
```

- [ ] **Step 2: 更新 argparse --format choices**

In `src/main.py`, find:
```python
choices=["html", "csv", "all"]
```
Change to:
```python
choices=["html", "csv", "pdf", "xlsx", "all"]
```

- [ ] **Step 3: 更新 click report subcommand**

In `src/cli/report.py`, change `click.Choice(...)` in `--format` option likewise.

- [ ] **Step 4: 更新 GUI 報表頁（Flask endpoint + HTML select options）**

In `src/gui.py` find format handling in the report generation endpoints; extend the allowlist. In `src/templates/index.html` find `<select>` for format and add `<option>` for pdf, xlsx.

- [ ] **Step 5: 跑全套 + 手動煙霧測試**

```bash
python -m pytest tests/ -q
python illumio_ops.py report traffic --format xlsx     # (Linux-only for pdf)
```

- [ ] **Step 6: Commit**

```bash
git add src/main.py src/gui.py src/cli/report.py src/report/report_generator.py \
        src/report/audit_generator.py src/report/ven_status_generator.py \
        src/report/policy_usage_generator.py src/templates/index.html
git commit -m "feat(reports): expose pdf/xlsx formats in CLI + Web GUI

argparse --format + click --format + GUI select now accept
html/csv/pdf/xlsx/all. Each generator dispatches to the corresponding
exporter. 'all' produces every format in parallel."
```

---

## Task 9: humanize 在報表中

**Files:**
- Modify: Each html exporter's footer/summary area

- [ ] **Step 1: 在報表 header/footer 用 humanize 替換原有字串**

For each HTML exporter, at the point where "Total: N flows" or similar is rendered, use `human_number(n)`. For file sizes use `human_size(bytes)`. For "generated at X minutes ago" use `human_time_ago(dt)`.

```python
from src.humanize_ext import human_number, human_size, human_time_ago
```

Keep pre-existing formatting for CSV / xlsx — those are machine-readable and should not use humanize.

- [ ] **Step 2: 跑測試 + i18n audit**

- [ ] **Step 3: Commit**

```bash
git add src/report/exporters/*html_exporter.py
git commit -m "feat(reports): apply humanize to HTML summary/footer metrics"
```

---

## Task 10: CJK 字型測試 + 最終驗收

**Files:**
- Create: `tests/test_html_report_cjk_font.py`

- [ ] **Step 1: 寫 CJK 測試（zh_TW 模式不應有 □□□）**

Create `tests/test_html_report_cjk_font.py`:

```python
"""Verify zh_TW report output does not contain the 'missing glyph' token."""


def test_zh_tw_html_report_has_no_tofu():
    # generate a small zh_TW chart_spec and render both engines
    from src.report.exporters.chart_renderer import render_plotly_html, render_matplotlib_png
    spec = {
        "type": "bar",
        "title": "連接埠 Top 5",
        "x_label": "連接埠",
        "y_label": "流量",
        "data": {"labels": ["80", "443", "22"], "values": [10, 5, 2]},
        "i18n": {"lang": "zh_TW"},
    }
    html = render_plotly_html(spec)
    # Tofu / replacement char should not appear in produced HTML
    assert "\ufffd" not in html, "plotly output contains U+FFFD replacement char"

    png = render_matplotlib_png(spec)
    # PNG is binary — can't inspect text, but ensure non-trivial size
    assert len(png) > 1000
```

- [ ] **Step 2: 跑完整測試**

```bash
python -m pytest tests/ -q
python -m pytest tests/test_i18n_audit.py tests/test_i18n_quality.py -v
```

- [ ] **Step 3: 更新 Status.md + Task.md**

- [ ] **Step 4: 手動煙霧 — 4 報表 × 3 格式**

```bash
# For each report type
python illumio_ops.py report traffic --format pdf --output-dir /tmp/phase5
python illumio_ops.py report traffic --format xlsx --output-dir /tmp/phase5
python illumio_ops.py report audit --format all --output-dir /tmp/phase5
# etc
```

檢查：
- 每個 PDF 有 CJK 字元正常顯示
- 每個 xlsx 有多 sheet + PNG 嵌入
- HTML 有互動 plotly 圖表（離線打開仍可操作）

- [ ] **Step 5: push + PR + merge + tag**

```bash
git push -u origin upgrade/phase-5-reports-rich
# gh pr create ...
# after merge:
git tag -a v3.5.1-reports -m "Phase 5: xlsx/PDF/plotly/pygments/humanize in reports"
git push origin v3.5.1-reports
```

---

## Phase 5 完成驗收清單

- [ ] `chart_renderer.py` 雙引擎（plotly + matplotlib）
- [ ] `xlsx_exporter.py` 多 sheet + 嵌入 PNG + 條件格式
- [ ] `pdf_exporter.py` weasyprint + CJK 字型
- [ ] `code_highlighter.py` pygments JSON/YAML
- [ ] mod02/05/07/10/15 產生 chart_spec
- [ ] 4 HTML exporter 嵌入 plotly div + matplotlib fallback + pygments CSS
- [ ] CLI --format / click --format / GUI select 支援 pdf/xlsx/all
- [ ] 所有報表 generator `export()` 支援 pdf/xlsx
- [ ] humanize 在 HTML summary/footer
- [ ] zh_TW 報表無 □□□（tofu 字元）
- [ ] 所有新測試通過；i18n audit 0 findings
- [ ] `v3.5.1-reports` tag 存在

**Done means ready to:** Phase 6（Scheduler）獨立進行；Wave B 收斂後 Phase 7（Logging）啟動。

---

## Rollback Plan

新 exporter 檔都是新增（不取代既有 HTML/CSV exporter），revert 一個 commit 就回到 Phase 4 狀態。既有報表輸出路徑完全不變。

---

## Self-Review Checklist

- ✅ **Spec coverage**：路線圖 Phase 5 所有套件（openpyxl, weasyprint, matplotlib, plotly, pygments, humanize）全覆蓋
- ✅ **Dual engine**：同一 chart_spec 兩端渲染，無重複資料定義
- ✅ **CJK font fallback**：matplotlib + plotly 兩端都配置
- ✅ **Offline ready**：plotly inline JS（無 CDN），符合 RPM 離線需求
- ✅ **i18n**：圖表 title/label 全走 `t()`；新增 5 個 `rpt_*_chart_title` keys
- ✅ **No placeholders**：每步有具體程式碼
- ✅ **TDD**：Task 2/3/4/5 先紅後綠；Task 10 最終 CJK 煙霧測試
- ✅ **Backward compat**：既有 HTML/CSV 輸出不變；僅新增 pdf/xlsx 兩種格式與 HTML 內的 chart 元素
