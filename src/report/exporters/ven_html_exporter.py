"""
src/report/exporters/ven_html_exporter.py
Self-contained HTML report for the VEN Status Inventory Report.
Includes embedded EN ↔ 繁體中文 language toggle (via report_i18n).
"""
from __future__ import annotations
import datetime
import os
import logging
import pandas as pd

from .report_i18n import make_i18n_js, lang_btn_html, STRINGS as _RPT_STRINGS

logger = logging.getLogger(__name__)

# Auto-build column name → i18n key mapping from report_i18n STRINGS
_COL_I18N: dict[str, str] = {}
for _k, _v in _RPT_STRINGS.items():
    if _k.startswith("rpt_col_"):
        _en = _v.get("en", "")
        if _en:
            _COL_I18N[_en] = _k

_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --cyan-120:#1A2C32; --cyan-110:#24393F; --cyan-100:#2D454C; --cyan-90:#325158;
    --orange:#FF5500;   --gold:#FFA22F;     --gold-110:#F97607;
    --green:#166644;    --green-80:#299B65; --green-10:#D1FAE5;
    --red:#BE122F;      --red-80:#F43F51;   --red-10:#FEE2E2;
    --slate:#313638;    --slate-20:#D6D7D7; --slate-50:#989A9B;
    --tan:#F7F4EE;      --tan-120:#E3D8C5;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Montserrat', -apple-system, sans-serif;
         background: var(--tan); color: var(--slate); }
  nav { position: fixed; top: 0; left: 0; width: 210px; height: 100vh;
        background: var(--cyan-120); overflow-y: auto; padding: 60px 0 20px; z-index: 100; }
  nav .nav-brand { position:absolute; top:0; left:0; width:100%; padding:14px 16px;
                   background:var(--orange); color:#fff; font-weight:700; font-size:13px; }
  nav a { display: block; color: var(--slate-20); text-decoration: none;
          padding: 7px 16px; font-size: 12px; border-left: 3px solid transparent; }
  nav a:hover { background: var(--cyan-100); border-left-color: var(--orange); color: #fff; }
  main { margin-left: 210px; padding: 24px; }
  h1 { color: var(--orange); font-size: 22px; font-weight: 700; margin-bottom: 4px; }
  h2 { color: var(--cyan-120); font-size: 16px; font-weight: 600; margin: 24px 0 10px;
       border-bottom: 2px solid var(--orange); padding-bottom: 6px; }
  h3 { color: var(--slate); font-size: 13px; font-weight: 600; margin: 16px 0 8px; }
  .kpi-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
  .kpi-card { background: #fff; border-radius: 8px; padding: 14px 18px;
               box-shadow: 0 1px 4px rgba(0,0,0,.08); min-width: 160px;
               border-top: 3px solid var(--orange); }
  .kpi-label { font-size: 11px; color: var(--slate-50); text-transform:uppercase; letter-spacing:.04em; }
  .kpi-value { font-size: 22px; font-weight: 700; color: var(--cyan-120); }
  .card { background: #fff; border-radius: 8px; padding: 20px;
          box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 20px; }
  .card.online  { border-top: 4px solid var(--green-80); }
  .card.offline { border-top: 4px solid var(--red-80); }
  .card.warn    { border-top: 4px solid var(--gold-110); }
  table { width: 100%; border-collapse: collapse; font-size: 12px; }
  th { background: var(--cyan-110); color: #fff; padding: 8px 10px; text-align: left;
       cursor: pointer; user-select: none; font-weight: 600; }
  th:hover { background: var(--cyan-100); }
  td { padding: 6px 10px; border-bottom: 1px solid var(--slate-20); word-break: break-all; }
  tr:nth-child(even) td { background: var(--tan); }
  tr:hover td { background: var(--tan-120); }
  .badge-online   { background: var(--green-10); color: var(--green); padding:2px 8px;
                    border-radius:4px; font-size:11px; font-weight:700; }
  .badge-offline  { background: var(--red-10); color: var(--red); padding:2px 8px;
                    border-radius:4px; font-size:11px; font-weight:700; }
  .badge-synced   { background: var(--green-10); color: var(--green); padding:2px 8px;
                    border-radius:4px; font-size:11px; font-weight:700; }
  .badge-unsynced { background: var(--red-10); color: var(--red); padding:2px 8px;
                    border-radius:4px; font-size:11px; font-weight:700; }
  .badge-staged   { background: #FFF3CD; color: #856404; padding:2px 8px;
                    border-radius:4px; font-size:11px; font-weight:700; }
  .note { background: var(--tan); border-left: 4px solid var(--orange);
          padding: 12px; border-radius: 4px; color: var(--cyan-120); font-size: 13px; }
  footer { text-align: center; color: var(--slate-50); font-size: 11px; margin: 40px 0 20px; }
</style>
"""

_SORT_JS = """
<script>
document.querySelectorAll('th').forEach((th, i) => {
  th.addEventListener('click', () => {
    var table = th.closest('table');
    var rows = Array.from(table.rows).slice(1);
    var asc = table.dataset.sortCol === String(i) && table.dataset.sortDir === 'asc';
    rows.sort((a, b) => {
      var av = a.cells[i]?.innerText || '', bv = b.cells[i]?.innerText || '';
      var an = parseFloat(av.replace(/,/g,'')), bn = parseFloat(bv.replace(/,/g,''));
      if (!isNaN(an) && !isNaN(bn)) return asc ? bn - an : an - bn;
      return asc ? bv.localeCompare(av) : av.localeCompare(bv);
    });
    rows.forEach(r => table.tBodies[0].appendChild(r));
    table.dataset.sortCol = i; table.dataset.sortDir = asc ? 'desc' : 'asc';
  });
});
</script>
"""


def _policy_sync_badge(val: str) -> str:
    """Return a styled badge for the Policy Sync column value."""
    v = str(val).lower().strip()
    if v == 'synced':
        return f'<span class="badge-synced">{val}</span>'
    if v in ('staged',):
        return f'<span class="badge-staged">{val}</span>'
    if v and v != 'none' and v != 'nan':
        return f'<span class="badge-unsynced">{val}</span>'
    return '—'


def _df_to_html(df, no_data_key: str = "rpt_no_records") -> str:
    if df is None or (hasattr(df, 'empty') and df.empty):
        return f'<p class="note" data-i18n="{no_data_key}">— No records —</p>'
    html = '<table><thead><tr>'
    for col in df.columns:
        i18n_key = _COL_I18N.get(col)
        if i18n_key:
            html += f'<th data-i18n="{i18n_key}">{col}</th>'
        else:
            html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    for _, row in df.iterrows():
        html += '<tr>'
        for col, val in zip(df.columns, row.values):
            val_str = '' if val is None or str(val) in ('None', 'nan') else str(val)
            if col == 'Policy Sync':
                html += f'<td>{_policy_sync_badge(val_str)}</td>'
            else:
                html += f'<td>{val_str}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


class VenHtmlExporter:
    def __init__(self, results: dict, df: pd.DataFrame = None):
        self._r = results
        self._df = df

    def export(self, output_dir: str = 'reports') -> str:
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H%M')
        filename = f'illumio_ven_status_{ts}.html'
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self._build())
        logger.info(f"[VenHtmlExporter] Saved: {filepath}")
        return filepath

    def _build(self) -> str:
        kpis = self._r.get('kpis', [])
        gen_at = self._r.get('generated_at', '')
        today_str = str(datetime.date.today())

        nav_html = (
            '<nav>'
            '<a href="#summary"><span data-i18n="rpt_ven_nav_summary">📊 Executive Summary</span></a>'
            '<a href="#online"><span data-i18n="rpt_ven_nav_online">✅ Online VENs</span></a>'
            '<a href="#offline"><span data-i18n="rpt_ven_nav_offline">❌ Offline VENs</span></a>'
            '<a href="#lost-today"><span data-i18n="rpt_ven_nav_lost_today">🔴 Lost Today (&lt;24h)</span></a>'
            '<a href="#lost-yest"><span data-i18n="rpt_ven_nav_lost_yest">🟠 Lost Yesterday</span></a>'
            '</nav>'
        )
        kpi_cards = ''.join(
            '<div class="kpi-card"><div class="kpi-label">' + k['label'] + '</div>'
            '<div class="kpi-value">' + k['value'] + '</div></div>'
            for k in kpis
        )
        df_online  = self._r.get('online')
        df_offline = self._r.get('offline')
        df_today   = self._r.get('lost_today')
        df_yest    = self._r.get('lost_yesterday')

        online_count  = len(df_online)  if df_online  is not None and not df_online.empty  else 0
        offline_count = len(df_offline) if df_offline is not None and not df_offline.empty else 0
        today_count   = len(df_today)   if df_today   is not None and not df_today.empty   else 0
        yest_count    = len(df_yest)    if df_yest    is not None and not df_yest.empty    else 0

        body = (
            '<section id="summary" class="card">'
            '<h1 data-i18n="rpt_ven_title">Illumio VEN Status Inventory Report</h1>'
            '<p style="color:#718096;margin-top:4px">'
            '<span data-i18n="rpt_generated">Generated:</span> ' + gen_at + '</p>'
            '<h2 data-i18n="rpt_key_metrics">Key Metrics</h2>'
            '<div class="kpi-grid">' + kpi_cards + '</div>'
            '</section>\n'

            '<section id="online" class="card online">'
            '<h2><span data-i18n="rpt_ven_sec_online">✅ Online VENs</span> (' + str(online_count) + ')</h2>'
            + _df_to_html(df_online) +
            '</section>\n'

            '<section id="offline" class="card offline">'
            '<h2><span data-i18n="rpt_ven_sec_offline">❌ Offline VENs</span> (' + str(offline_count) + ')</h2>'
            + _df_to_html(df_offline) +
            '</section>\n'

            '<section id="lost-today" class="card offline">'
            '<h2><span data-i18n="rpt_ven_sec_lost_today">🔴 Lost Connection in Last 24h</span>'
            ' (' + str(today_count) + ')</h2>'
            '<p style="color:#718096;font-size:12px;margin-bottom:12px" data-i18n="rpt_ven_desc_today">'
            'VENs currently offline whose last heartbeat was within the past 24 hours.</p>'
            + _df_to_html(df_today) +
            '</section>\n'

            '<section id="lost-yest" class="card warn">'
            '<h2><span data-i18n="rpt_ven_sec_lost_yest">🟠 Lost Connection 24\u201348h Ago</span>'
            ' (' + str(yest_count) + ')</h2>'
            '<p style="color:#718096;font-size:12px;margin-bottom:12px" data-i18n="rpt_ven_desc_yest">'
            'VENs currently offline whose last heartbeat was 24\u201348 hours ago.</p>'
            + _df_to_html(df_yest) +
            '</section>\n'

            '<footer><span data-i18n="rpt_ven_footer">Illumio PCE Ops — VEN Status Report</span>'
            ' &middot; ' + today_str + '</footer>'
        )
        return (
            '<!DOCTYPE html><html lang="en"><head>\n'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<title>Illumio VEN Status Report</title>' + _CSS + '</head>\n'
            '<body>' + lang_btn_html() + nav_html + '<main>' + body + '</main>'
            + _SORT_JS + make_i18n_js() + '</body></html>'
        )
