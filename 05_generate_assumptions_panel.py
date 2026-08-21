"""
Feature 10 — Assumptions Panel.

Reads the central ASSUMPTIONS registry (assumptions.py) and renders it into
a self-contained HTML fragment: a toggleable panel listing every hardcoded
constant used anywhere in the CaneCycle pipeline, grouped by category, each
with its value, unit, and justification.

This is deliberately NOT a standalone HTML page — it returns a fragment
(a <div> + a small <script>) meant to be injected directly into
supply_map.html by 04_render_supply_map.py, so it lives in the same file
your teammates and judges already open. No server, no second page.

Usage from another script:
    from importlib import import_module
    panel_html = import_module("05_generate_assumptions_panel").build_assumptions_panel_html()

(Can't use a plain `import` because the filename starts with a digit.)

Run directly (`python 05_generate_assumptions_panel.py`) to sanity-check
the fragment renders without errors and preview it in isolation.
"""
import html as html_escape
from assumptions import get_by_category


def build_assumptions_panel_html():
    """Returns a single HTML string: a floating toggle button + a hidden
    panel with the grouped assumptions table. Self-contained CSS/JS, no
    external dependencies, safe to inject into any existing HTML page."""

    grouped = get_by_category()

    rows_html = []
    for category, items in grouped.items():
        rows_html.append(
            f'<tr class="ca-category-row"><td colspan="3">{html_escape.escape(category)}</td></tr>'
        )
        for a in items:
            label = html_escape.escape(str(a["label"]))
            value = html_escape.escape(str(a["value"]))
            unit = html_escape.escape(str(a["unit"]))
            justification = html_escape.escape(str(a["justification"]))
            rows_html.append(
                "<tr>"
                f'<td class="ca-label">{label}'
                f'<div class="ca-justification">{justification}</div></td>'
                f'<td class="ca-value">{value}</td>'
                f'<td class="ca-unit">{unit}</td>'
                "</tr>"
            )
    table_rows = "\n".join(rows_html)

    return f"""
<style>
  #ca-assumptions-toggle {{
    position: fixed; bottom: 20px; right: 20px; z-index: 10000;
    background: #2b6cb0; color: white; border: none; border-radius: 6px;
    padding: 10px 16px; font-size: 13px; font-family: sans-serif;
    cursor: pointer; box-shadow: 0 1px 6px rgba(0,0,0,0.3);
  }}
  #ca-assumptions-toggle:hover {{ background: #235a94; }}
  #ca-assumptions-panel {{
    display: none; position: fixed; top: 0; right: 0; height: 100%;
    width: 420px; max-width: 90vw; background: white; z-index: 10001;
    box-shadow: -2px 0 12px rgba(0,0,0,0.25); overflow-y: auto;
    font-family: sans-serif; padding: 20px;
  }}
  #ca-assumptions-panel.ca-open {{ display: block; }}
  #ca-assumptions-panel h2 {{ font-size: 16px; margin: 0 0 4px 0; }}
  #ca-assumptions-panel p.ca-subtitle {{
    font-size: 12px; color: #666; margin: 0 0 16px 0;
  }}
  #ca-assumptions-close {{
    position: absolute; top: 16px; right: 18px; background: none;
    border: none; font-size: 20px; cursor: pointer; color: #666;
  }}
  .ca-table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  .ca-table td {{ padding: 8px 6px; vertical-align: top; border-bottom: 1px solid #eee; }}
  .ca-category-row td {{
    font-weight: 700; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.03em; color: #2b6cb0; padding-top: 18px;
    border-bottom: 2px solid #2b6cb0;
  }}
  .ca-label {{ font-weight: 600; width: 45%; }}
  .ca-justification {{ font-weight: 400; color: #777; margin-top: 3px; font-size: 11.5px; }}
  .ca-value {{ font-weight: 600; color: #d1495b; white-space: nowrap; }}
  .ca-unit {{ color: #888; font-size: 11.5px; }}
</style>

<button id="ca-assumptions-toggle" onclick="document.getElementById('ca-assumptions-panel').classList.add('ca-open')">
  &#9432; Assumptions
</button>

<div id="ca-assumptions-panel">
  <button id="ca-assumptions-close" onclick="document.getElementById('ca-assumptions-panel').classList.remove('ca-open')">&times;</button>
  <h2>Assumptions</h2>
  <p class="ca-subtitle">Every hardcoded constant used in this build, listed openly rather than buried in code.</p>
  <table class="ca-table">
    {table_rows}
  </table>
</div>
"""


if __name__ == "__main__":
    fragment = build_assumptions_panel_html()
    print(f"Generated assumptions panel fragment: {len(fragment):,} characters")
    with open("assumptions_panel_preview.html", "w", encoding="utf-8") as f:
        f.write(f"<html><body style='font-family:sans-serif;padding:40px;'>"
                 f"<h1>Preview host page</h1>{fragment}</body></html>")
    print("Wrote assumptions_panel_preview.html — open it in a browser to preview the panel in isolation.")
