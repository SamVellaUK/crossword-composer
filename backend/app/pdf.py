"""Single-page print-ready PDF export via WeasyPrint."""
from html import escape


def _grid_html(puzzle: dict) -> str:
    cols = puzzle["dimensions"]["cols"]
    rows = puzzle["dimensions"]["rows"]
    cells = {}
    numbers = {}
    for e in puzzle["entries"]:
        x, y = e["position"]["x"], e["position"]["y"]
        numbers.setdefault((y, x), e["humanNumber"])
        for i in range(e["length"]):
            cy = y + (i if e["direction"] == "down" else 0)
            cx = x + (i if e["direction"] == "across" else 0)
            cells[(cy, cx)] = True
    out = ['<table class="grid">']
    for r in range(rows):
        out.append("<tr>")
        for c in range(cols):
            if cells.get((r, c)):
                num = numbers.get((r, c), "")
                out.append(f'<td class="w"><span class="n">{num}</span></td>')
            else:
                out.append('<td class="b"></td>')
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


def _clues_html(puzzle: dict, direction: str) -> str:
    entries = sorted((e for e in puzzle["entries"] if e["direction"] == direction),
                     key=lambda e: e["number"])
    items = [f'<li><b>{e["humanNumber"]}</b> {escape(e.get("clue") or "—")}</li>' for e in entries]
    return f'<h2>{direction.capitalize()}</h2><ul class="clues">{"".join(items)}</ul>'


def render_pdf(puzzle: dict) -> bytes:
    from weasyprint import HTML  # imported lazily: slow import
    title = escape(puzzle.get("name") or "Crossword")
    author = escape((puzzle.get("creator") or {}).get("name") or "")
    cols = puzzle["dimensions"]["cols"]
    cell_mm = min(9, 120 // cols)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
      @page {{ size: A4; margin: 14mm; }}
      body {{ font-family: Helvetica, Arial, sans-serif; color: #000; }}
      h1 {{ font-size: 16pt; margin: 0 0 2mm; }}
      .author {{ font-size: 10pt; margin: 0 0 5mm; color: #333; }}
      table.grid {{ border-collapse: collapse; margin-bottom: 6mm; }}
      table.grid td {{ width: {cell_mm}mm; height: {cell_mm}mm; border: 0.4pt solid #000;
                       vertical-align: top; padding: 0; }}
      td.b {{ background: #000; }}
      td.w .n {{ font-size: 5.5pt; padding-left: 0.4mm; }}
      .cols {{ display: flex; gap: 8mm; }}
      .col {{ flex: 1; }}
      h2 {{ font-size: 11pt; border-bottom: 0.6pt solid #000; margin: 0 0 2mm; }}
      ul.clues {{ list-style: none; padding: 0; margin: 0; font-size: 8.5pt; line-height: 1.45; }}
    </style></head><body>
      <h1>{title}</h1>
      <p class="author">{("Set by " + author) if author else ""}</p>
      {_grid_html(puzzle)}
      <div class="cols">
        <div class="col">{_clues_html(puzzle, "across")}</div>
        <div class="col">{_clues_html(puzzle, "down")}</div>
      </div>
    </body></html>"""
    return HTML(string=html).write_pdf()
