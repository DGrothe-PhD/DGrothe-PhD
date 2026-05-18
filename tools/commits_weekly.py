#!/usr/bin/env python3
"""
commits_weekly.py
Liest eine GitHub-Commit-Such-JSON (beliebig viele Items, gleiche Struktur)
und erzeugt eine HTML-Seite mit:
  - Tabelle: Jahr | KW | Montag der KW | Commits
  - Balkendiagramm pro Jahr (SVG, pure HTML/CSS/JS)

Aufruf (JSON-Datei):
    python commits_weekly.py commits.json
    python commits_weekly.py commits.json -o out.html

Aufruf (direkt von GitHub API holen, alle Seiten):
    python commits_weekly.py --fetch DGrothe-PhD 2023-01-01 2026-05-18
    python commits_weekly.py --fetch DGrothe-PhD 2023-01-01 2026-05-18 --token ghp_xxx
"""

import json
import sys
import time
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict
from pathlib import Path


def monday_of_isoweek(year: int, week: int) -> str:
    """Gibt den Montag der ISO-Kalenderwoche als YYYY-MM-DD zurück."""
    d = datetime.fromisocalendar(year, week, 1)
    return d.strftime("%Y-%m-%d")


def parse_commits(data: dict) -> dict:
    """
    Gibt {(year, week): count} zurück,
    sortiert nach Jahr und Woche.
    """
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for item in data.get("items", []):
        date_str = item["commit"]["author"]["date"]
        # ISO-8601 mit Offset: 2026-05-08T18:22:36.000+02:00
        dt = datetime.fromisoformat(date_str)
        iso = dt.isocalendar()
        counts[(iso[0], iso[1])] += 1
    return dict(sorted(counts.items()))


def fetch_all_commits(user: str, date_from: str, date_to: str, token: str | None = None) -> tuple[list, int]:
    """
    Ruft die GitHub Search Commits API seitenweise ab (max. 10 Seiten à 100).
    Gibt (items, total_count) zurück.
    """
    headers = {"Accept": "application/vnd.github.cloak-preview"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    all_items = []
    total_count = 0
    page = 1

    while page <= 10:  # API-Limit: max 1000 Ergebnisse = 10 × 100
        q = f"author:{user}+committer-date:{date_from}..{date_to}"
        url = f"https://api.github.com/search/commits?q={q}&per_page=100&page={page}"
        req = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print("Rate limit erreicht – 60 Sekunden warten …", file=sys.stderr)
                time.sleep(60)
                continue
            raise

        if page == 1:
            total_count = data.get("total_count", 0)
            print(f"  total_count laut API: {total_count}", file=sys.stderr)

        items = data.get("items", [])
        all_items.extend(items)
        print(f"  Seite {page}: {len(items)} Items geholt (gesamt bisher: {len(all_items)})", file=sys.stderr)

        if len(items) < 100:
            break  # letzte Seite
        page += 1
        time.sleep(1)  # Rate limit schonen

    return all_items, total_count


def build_html(counts: dict[tuple[int, int], int], total: int) -> str:
    rows_html = ""
    by_year: dict[int, list[tuple[int, int, int]]] = defaultdict(list)

    for (year, week), count in counts.items():
        monday = monday_of_isoweek(year, week)
        rows_html += f"""
        <tr>
          <td>{year}</td>
          <td>{week}</td>
          <td>{monday}</td>
          <td class="num">{count}</td>
        </tr>"""
        by_year[year].append((week, monday, count))

    # Diagramm-Daten als JS-Objekt
    chart_data_js = "const chartData = " + json.dumps(
        {str(y): [{"week": w, "monday": m, "count": c} for w, m, c in entries]
         for y, entries in sorted(by_year.items())}
    ) + ";"

    years = sorted(by_year.keys())
    year_tabs = "".join(
        f'<button class="tab-btn{" active" if i == 0 else ""}" data-year="{y}">{y}</button>'
        for i, y in enumerate(years)
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Commits pro Woche</title>
<style>
  :root {{
    --bg: #f8f7f4;
    --surface: #ffffff;
    --border: #e2e0d8;
    --text: #1a1917;
    --muted: #7a7870;
    --accent: IndianRed;
    --bar: IndianRed;
    --bar-hover: Salmon;
    font-family: 'Georgia', serif;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    padding: 2rem;
    min-height: 100vh;
  }}
  h1 {{
    font-size: 1.5rem;
    font-weight: normal;
    letter-spacing: 0.02em;
    margin-bottom: 0.25rem;
  }}
  .meta {{ color: var(--muted); font-size: 0.85rem; margin-bottom: 2rem; }}

  .layout {{
    display: flex;
    gap: 2rem;
    align-items: flex-start;
    flex-wrap: wrap;
  }}

  /* ── Tabelle ── */
  .table-wrap {{
    flex: 0 0 auto;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }}
  table {{
    border-collapse: collapse;
    font-size: 0.875rem;
    min-width: 320px;
  }}
  thead tr {{
    background: #f0eeea;
  }}
  th, td {{
    padding: 0.55rem 1rem;
    text-align: left;
    border-bottom: 1px solid var(--border);
  }}
  th {{
    font-weight: normal;
    color: var(--muted);
    font-size: 0.78rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr:last-child td {{ border-bottom: none; }}
  tbody tr:hover {{ background: #faf9f6; }}

  /* ── Diagramm ── */
  .chart-wrap {{
    flex: 1 1 340px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 1.25rem 1.5rem 1rem;
  }}
  .chart-header {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    flex-wrap: wrap;
  }}
  .chart-title {{
    font-size: 0.85rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    flex: 1;
  }}
  .tab-btn {{
    background: none;
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.25rem 0.65rem;
    font-size: 0.8rem;
    cursor: pointer;
    color: var(--muted);
    font-family: inherit;
    transition: all 0.15s;
  }}
  .tab-btn.active, .tab-btn:hover {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }}
  .chart-area {{
    display: flex;
    gap: 0;
    align-items: stretch;
  }}
  .y-axis {{
    width: 32px;
    flex-shrink: 0;
    position: relative;
    padding-bottom: 28px;
  }}
  .y-tick {{
    position: absolute;
    right: 6px;
    font-size: 0.65rem;
    color: var(--muted);
    transform: translateY(50%);
    line-height: 1;
    text-align: right;
  }}
  .bars {{
    flex: 1;
    display: flex;
    align-items: flex-end;
    gap: 6px;
    height: 180px;
    padding-bottom: 28px;
    position: relative;
  }}
  .bars::before {{
    content: '';
    position: absolute;
    top: 0; bottom: 28px;
    left: 0;
    width: 1px;
    background: var(--border);
  }}
  .bars::after {{
    content: '';
    position: absolute;
    bottom: 28px;
    left: 0; right: 0;
    height: 1px;
    background: var(--border);
  }}
  .bar-col {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    height: 100%;
    gap: 4px;
    position: relative;
  }}
  .bar {{
    width: 100%;
    background: var(--bar);
    border-radius: 3px 3px 0 0;
    transition: height 0.35s ease, background 0.15s;
    cursor: default;
    min-height: 2px;
  }}
  .bar:hover {{ background: var(--bar-hover); }}
  .bar-label {{
    position: absolute;
    bottom: 0;
    font-size: 0.65rem;
    color: var(--muted);
    white-space: nowrap;
    transform: rotate(-45deg) translateX(-30%);
    transform-origin: top left;
    line-height: 1;
    pointer-events: none;
  }}
  .bar-val {{
    font-size: 0.7rem;
    color: var(--muted);
    position: absolute;
    top: -18px;
    left: 50%;
    transform: translateX(-50%);
    white-space: nowrap;
  }}
  /* tooltip */
  .tooltip {{
    position: fixed;
    background: #1a1917;
    color: #fff;
    font-size: 0.78rem;
    padding: 4px 9px;
    border-radius: 4px;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.1s;
    z-index: 100;
  }}
</style>
</head>
<body>
<h1>Commits pro Kalenderwoche</h1>
<p class="meta">Gesamt: {total} Commits &nbsp;·&nbsp; Quelle: GitHub Search API</p>

<div class="layout">
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Jahr</th>
          <th>KW</th>
          <th>Montag</th>
          <th style="text-align:right">Commits</th>
        </tr>
      </thead>
      <tbody>{rows_html}
      </tbody>
    </table>
  </div>

  <div class="chart-wrap">
    <div class="chart-header">
      <span class="chart-title">Commits / Woche</span>
      <div id="tabs">{year_tabs}</div>
    </div>
    <div class="chart-area">
      <div class="y-axis" id="y-axis"></div>
      <div class="bars" id="bars"></div>
    </div>
  </div>
</div>

<div class="tooltip" id="tip"></div>

<script>
{chart_data_js}

const barsEl = document.getElementById('bars');
const yAxis = document.getElementById('y-axis');
const tip = document.getElementById('tip');
let activeYear = Object.keys(chartData)[0];

const BAR_HEIGHT = 148;

function render(year) {{
  const entries = chartData[year] || [];
  const max = Math.max(...entries.map(e => e.count), 1);
  barsEl.innerHTML = '';
  entries.forEach(e => {{
    const pct = (e.count / max) * BAR_HEIGHT;
    const col = document.createElement('div');
    col.className = 'bar-col';
    col.innerHTML = `
      <div class="bar" style="height:${{pct}}px" data-info="KW ${{e.week}} (${{e.monday}}): ${{e.count}}"></div>
      <span class="bar-label">KW${{e.week}}</span>`;
    barsEl.appendChild(col);
  }});
  // Y-Achse: 4 Ticks (0, 25%, 50%, 75%, 100%)
  yAxis.innerHTML = '';
  const ticks = 4;
  for (let i = 0; i <= ticks; i++) {{
    const val = Math.round((max * i) / ticks);
    const bottomPx = 28 + (i / ticks) * BAR_HEIGHT;
    const span = document.createElement('span');
    span.className = 'y-tick';
    span.textContent = val;
    span.style.bottom = bottomPx + 'px';
    yAxis.appendChild(span);
  }}
  // Tooltip
  barsEl.querySelectorAll('.bar').forEach(b => {{
    b.addEventListener('mousemove', ev => {{
      tip.textContent = b.dataset.info;
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX + 12) + 'px';
      tip.style.top = (ev.clientY - 28) + 'px';
    }});
    b.addEventListener('mouseleave', () => tip.style.opacity = 0);
  }});
}}

document.getElementById('tabs').addEventListener('click', ev => {{
  const btn = ev.target.closest('.tab-btn');
  if (!btn) return;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeYear = btn.dataset.year;
  render(activeYear);
}});

render(activeYear);
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="GitHub-Commits-JSON → HTML-Tabelle + Diagramm")
    parser.add_argument("input", nargs="?", help="Pfad zur JSON-Datei")
    parser.add_argument("-o", "--output", help="Ausgabe-HTML")
    parser.add_argument("--fetch", nargs=3, metavar=("USER", "VON", "BIS"),
                        help="Direkt von GitHub API holen: --fetch USERNAME 2023-01-01 2026-05-18")
    parser.add_argument("--token", help="GitHub Personal Access Token (erhöht Rate Limit)")
    args = parser.parse_args()

    if args.fetch:
        user, date_from, date_to = args.fetch
        print(f"Hole Commits für {user} ({date_from} – {date_to}) …", file=sys.stderr)
        items, total = fetch_all_commits(user, date_from, date_to, args.token)
        data = {"total_count": total, "items": items}
        out = Path(args.output) if args.output else Path(f"commits_{user}.html")
    elif args.input:
        src = Path(args.input)
        if not src.exists():
            print(f"Fehler: Datei nicht gefunden: {src}", file=sys.stderr)
            sys.exit(1)
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        total = data.get("total_count", 0)
        out = Path(args.output) if args.output else src.with_suffix(".html")
    else:
        parser.print_help()
        sys.exit(1)

    counts = parse_commits(data)
    html = build_html(counts, total)
    out.write_text(html, encoding="utf-8")
    print(f"✓ Gespeichert: {out}  ({len(counts)} Kalenderwochen, {sum(counts.values())} Items verarbeitet)")


if __name__ == "__main__":
    main()
