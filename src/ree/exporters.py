"""Deterministic data files and a self-contained, offline HTML run report."""

import csv
import importlib.util
import json
from hashlib import sha256
from html import escape

from ree.models import canonical
from ree.storage import TABLES, connect

FILENAMES = {"source": "sources", "document": "documents", "claim": "claims",
             "location": "locations", "event": "events", "event_claim": "event_claim_links",
             "assessment": "assessments", "review": "reviews", "provenance": "transformations"}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def csv_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: csv_cell(canonical(row[k]) if isinstance(row.get(k), (dict, list))
                                        else row.get(k)) for k in columns})


def preflight_exports(formats):
    for fmt, module, extra in [("parquet", "pyarrow", "columnar"), ("gpkg", "geopandas", "gis")]:
        if fmt in formats and importlib.util.find_spec(module) is None:
            raise ValueError(f"{fmt} export needs optional dependencies: pip install '.[{extra}]'")


def export_all(root, tables, events, proposals, formats, summary):
    columns_db = connect()
    try:
        for table in TABLES:
            name = FILENAMES.get(table, table)
            columns = [x[1] for x in columns_db.execute(f"PRAGMA table_info({table})")]
            if "json" in formats:
                write_json(root / "data" / (name + ".json"), tables[table])
            if "csv" in formats:
                write_csv(root / "data" / (name + ".csv"), tables[table], columns)
            if "parquet" in formats:
                import pyarrow as pa
                import pyarrow.parquet as pq
                sql_types = {x[1]: x[2] for x in columns_db.execute(f"PRAGMA table_info({table})")}
                arrow_types = {"TEXT": pa.string(), "INTEGER": pa.int64(), "REAL": pa.float64()}
                arrays = {k: [row.get(k) for row in tables[table]]
                          for k in columns}
                frame = pa.Table.from_pydict(arrays, schema=pa.schema(
                    [(k, arrow_types[sql_types[k]]) for k in columns]))
                pq.write_table(frame, root / "data" / (name + ".parquet"))
    finally:
        columns_db.close()
    location_features = [{"type": "Feature", "id": x["location_id"],
                          "geometry": json.loads(x["geometry_json"]) if x["geometry_json"] else None,
                          "properties": {k: v for k, v in x.items() if k != "geometry_json"}}
                         for x in tables["location"]]
    event_features = [{"type": "Feature", "id": e["event_id"], "geometry": e["geometry"],
                       "properties": {k: v for k, v in e.items() if k != "geometry"}}
                      for e in events]
    for name, features in [("locations", location_features), ("events", event_features)]:
        if "geojson" in formats:
            write_json(root / "gis" / (name + ".geojson"), {"type": "FeatureCollection", "features": features})
        if "gpkg" in formats:
            import geopandas as gpd
            flat = [{**f, "properties": {k: canonical(v) if isinstance(v, (dict, list)) else v
                                          for k, v in f["properties"].items()}} for f in features]
            frame = gpd.GeoDataFrame.from_features(flat, crs="EPSG:4326") if flat else gpd.GeoDataFrame(
                {"geometry": []}, geometry="geometry", crs="EPSG:4326")
            frame.to_file(root / "gis" / "evidence.gpkg", layer=name, driver="GPKG", engine="pyogrio")
    review_columns = ["review_id", "claim_id", "reason", "status", "decision", "reviewer", "note", "location_id"]
    write_csv(root / "review" / "decisions_template.csv", tables["review"], review_columns)
    for filename, key in [("ambiguous_locations", "location"), ("uncertain_claims", "")]:
        rows = [r for r in tables["review"] if key in r["reason"] and r["status"] == "pending"]
        write_csv(root / "review" / (filename + ".csv"), rows, review_columns)
    write_csv(root / "review" / "possible_event_links.csv", proposals,
              ["left_event_id", "right_event_id", "reason", "status", "text_similarity",
               "decision", "reviewer", "note"])
    write_json(root / "provenance" / "sources.json", tables["source"])
    write_json(root / "provenance" / "transformations.json", tables["provenance"])
    render_report(root, events, summary)


def render_report(root, events, summary):
    # Geographic coordinate plot. No invented coastlines or impact footprints.
    points = [e for e in events if e["geometry"] and e["geometry"]["type"] == "Point"]
    w, h = 1000, 400
    svg = [(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
            'aria-label="Reported coordinates and representational reference points">'),
           '<rect width="1000" height="400" fill="#edf3f2"/>']
    for lon in range(-180, 181, 60):
        x = (lon + 180) / 360 * 940 + 30
        svg.append(f'<path d="M{x} 20V365" stroke="#c1d3ce"/><text x="{x}" y="389" '
                   f'text-anchor="middle" font-size="12">{lon}°</text>')
    for lat in range(-60, 61, 30):
        y = (90 - lat) / 180 * 340 + 20
        svg.append(f'<path d="M30 {y}H970" stroke="#c1d3ce"/><text x="4" y="{y}" '
                   f'font-size="11">{lat}°</text>')
    for e in points:
        lon, lat = e["geometry"]["coordinates"]
        x, y = (lon + 180) / 360 * 940 + 30, (90 - lat) / 180 * 340 + 20
        color = "#b87520" if e["representational"] else "#136f63"
        svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="white" stroke-width="2">'
                   f'<title>{escape(e["label"])}; {escape(e["spatial_precision"])}</title></circle>')
    svg.append('</svg>')
    svg_text = "".join(svg)
    (root / "maps" / "event_coordinates.svg").write_text(svg_text, encoding="utf-8")
    cards = "".join(f'<div class="card"><strong>{escape(str(summary[k]))}</strong><span>{label}</span></div>'
                    for k, label in [("documents", "Documents"), ("claims", "Claims"),
                                     ("events", "Candidate events"), ("pending_reviews", "Pending reviews")])
    rows = "".join('<tr>' + ''.join(f'<td>{escape(str(e.get(k) if e.get(k) is not None else "Unknown"))}</td>'
                                  for k in ["category", "label", "start_date", "spatial_precision", "state"])
                   + '</tr>' for e in events)
    html = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>REE run report</title>
<style>body{margin:0;background:#f6f8f7;color:#173d37;font:16px/1.6 system-ui,sans-serif}
main{max-width:1120px;margin:auto;padding:42px 24px}h1{font-size:40px;line-height:1.15;margin:8px 0}
.eyebrow{letter-spacing:.14em;font-size:12px;font-weight:700}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:26px 0}
.card{background:white;border:1px solid #d3ded9;border-radius:12px;padding:22px}.card strong{display:block;font-size:32px}.card span{font-size:14px}
section{background:white;border:1px solid #d3ded9;border-radius:12px;padding:24px;margin:20px 0}svg{width:100%;height:auto}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:12px;border-bottom:1px solid #dce5e1}
.scroll{overflow:auto}a{color:#126c5d}code{background:#eaf0ee;padding:3px 6px}input{padding:10px;border:1px solid #a4bbb3;border-radius:6px;width:min(90%,420px)}
@media(max-width:640px){.cards{grid-template-columns:repeat(2,1fr)}h1{font-size:30px}main{padding:24px 12px}section{padding:16px}}
</style><main><div class="eyebrow">RESILIENCE EVIDENCE ENGINE · v0.1</div><h1>Evidence with a traceable path.</h1>
<p>Inspect source claims, uncertainty and candidate events. This is a software run report; it does not establish hazard risk or event completeness.</p>'''
    html += cards + '<section><h2>Coordinate overview</h2>' + svg_text
    html += (f'<p>{len(points)} of {len(events)} candidate events have a point representation. '
             'Green: source-reported point. Amber: representational reference. Unresolved places remain unmapped. '
             'This coordinate plot has no boundary or impact layer.</p></section>')
    html += '<section><h2>Candidate events</h2><input id="filter" aria-label="Filter events" placeholder="Filter category or place"><div class="scroll"><table><thead><tr><th>Category</th><th>Place / label</th><th>Start</th><th>Spatial precision</th><th>State</th></tr></thead><tbody>'
    html += rows + '</tbody></table></div></section>'
    data_name = next((name for name in ("claims.csv", "claims.json", "claims.parquet")
                      if (root / "data" / name).is_file()), "evidence.sqlite")
    html += (f'<section><h2>Inspect and review</h2><p>Start with <a href="../data/{data_name}">{data_name}</a>, '
             '<a href="../review/decisions_template.csv">the review template</a>, and '
             '<a href="../provenance/run_manifest.json">the run manifest</a>. '
             'The SQLite database and replay snapshot are authoritative for this run.</p>'
             '<p>Grades summarize explicit indicators. Human acceptance does not remove uncertainty '
             'in time or geography. Outputs follow the selected privacy and data-rights policy.</p></section>')
    html += '<script>document.getElementById("filter").addEventListener("input",function(){for(const row of document.querySelectorAll("tbody tr")){row.hidden=!row.textContent.toLowerCase().includes(this.value.toLowerCase());}});</script></main></html>'
    (root / "summary" / "run_report.html").write_text(html, encoding="utf-8")


def file_hashes(root):
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and p.name != "run_manifest.json"}
