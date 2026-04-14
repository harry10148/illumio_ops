from __future__ import annotations

import html
from typing import Callable


def _is_empty(value) -> bool:
    if value is None:
        return True
    text = str(value)
    return text in ("None", "nan", "NaT")


def _default_cell(value) -> str:
    if _is_empty(value):
        return ""
    return html.escape(str(value))


def render_df_table(
    df,
    *,
    col_i18n: dict[str, str],
    no_data_key: str = "rpt_no_data",
    render_cell: Callable | None = None,
    row_attrs: Callable | None = None,
) -> str:
    if df is None or (hasattr(df, "empty") and df.empty):
        return f'<p class="note" data-i18n="{no_data_key}">No data</p>'

    columns = list(df.columns)
    n_cols = len(columns)
    interactive = n_cols >= 3
    compact = n_cols <= 3
    table_cls_parts = ["report-table", "report-table--auto"]
    if interactive:
        table_cls_parts.append("report-table--interactive")
    table_class = " ".join(table_cls_parts)

    panel_class = "report-table-panel"
    if compact:
        panel_class += " report-table-panel--compact"

    html_parts = [
        f'<div class="{panel_class}">',
        '<div class="report-table-wrap">',
        (
            f'<table class="{table_class}" '
            f'data-interactive="{str(interactive).lower()}" '
            f'data-column-count="{n_cols}">'
        ),
        "<colgroup>",
    ]

    for _ in columns:
        html_parts.append('<col>')

    html_parts.extend([
        "</colgroup>",
        "<thead><tr>",
    ])
    for col in columns:
        i18n_key = col_i18n.get(col)
        title = html.escape(str(col), quote=True)
        if i18n_key:
            html_parts.append(
                f'<th data-i18n="{i18n_key}" title="{title}">{html.escape(str(col))}</th>'
            )
        else:
            html_parts.append(f'<th title="{title}">{html.escape(str(col))}</th>')
    html_parts.append("</tr></thead><tbody>")

    for _, row in df.iterrows():
        attr_str = ""
        if row_attrs:
            attr_str = row_attrs(row) or ""
        html_parts.append(f"<tr{attr_str}>")
        for col in columns:
            cell_html = render_cell(col, row[col], row) if render_cell else _default_cell(row[col])
            html_parts.append(f"<td>{cell_html}</td>")
        html_parts.append("</tr>")

    html_parts.extend(["</tbody></table>", "</div>", "</div>"])
    return "".join(html_parts)
