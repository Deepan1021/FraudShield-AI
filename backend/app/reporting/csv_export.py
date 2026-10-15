import csv
import io


def _cell(v) -> str:
    s = str(v) if v is not None else ""
    # Neutralise spreadsheet formula injection.
    return "'" + s if s[:1] in ("=", "+", "-", "@") and not s.replace(".", "", 1).lstrip("-").isdigit() else s


def export_csv(report: dict) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([report["title"]])
    w.writerow(["Report ID", report["report_id"], "Generated at", report["generated_at"]])
    for s in report["sections"]:
        w.writerow([])
        w.writerow([f"## {s['title']}"])
        d = s["data"]
        if s["type"] == "text":
            w.writerow([_cell(d)])
        elif s["type"] == "kv":
            for k, v in d:
                w.writerow([_cell(k), _cell(", ".join(map(str, v)) if isinstance(v, list) else v)])
        elif s["type"] == "list":
            for item in d:
                w.writerow([_cell(item)])
        elif s["type"] == "table":
            w.writerow(d["columns"])
            for row in d["rows"]:
                w.writerow([_cell(c) for c in row])
    return buf.getvalue().encode("utf-8-sig")
