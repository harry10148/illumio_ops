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
