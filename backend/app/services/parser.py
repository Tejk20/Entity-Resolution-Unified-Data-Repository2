import csv
import re
from pathlib import Path
from typing import Iterator


INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+[`\"'\[]?(\w+)[`\"'\]]?\s*(?:\((.*?)\))?\s*VALUES\s*(.*);",
    re.IGNORECASE | re.DOTALL,
)
CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"'\[]?(\w+)[`\"'\]]?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def sniff_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".sql"):
        return "sql"
    return "unknown"


def parse_csv(path: Path) -> tuple[str, list[str], list[dict]]:
    table = path.stem
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(fh, dialect=dialect)
        columns = [c.strip() for c in (reader.fieldnames or [])]
        rows = []
        for i, row in enumerate(reader, start=1):
            cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k}
            cleaned["_row_id"] = str(i)
            rows.append(cleaned)
    return table, columns, rows


def _split_sql_values(blob: str) -> list[str]:
    values = []
    buf = []
    depth = 0
    in_quote = False
    quote_char = ""
    escape = False
    for ch in blob:
        if in_quote:
            buf.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_quote = False
            continue
        if ch in {"'", '"'}:
            in_quote = True
            quote_char = ch
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
            if depth == 1:
                buf = []
                continue
            buf.append(ch)
            continue
        if ch == ")":
            depth -= 1
            if depth == 0:
                values.append("".join(buf))
                buf = []
                continue
            buf.append(ch)
            continue
        if depth > 0:
            buf.append(ch)
    return values


def _parse_value_tuple(raw: str) -> list[str]:
    parts = []
    buf = []
    in_quote = False
    quote_char = ""
    escape = False
    for ch in raw:
        if in_quote:
            if escape:
                buf.append(ch)
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote_char:
                in_quote = False
            else:
                buf.append(ch)
            continue
        if ch in {"'", '"'}:
            in_quote = True
            quote_char = ch
            continue
        if ch == ",":
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    parts.append("".join(buf).strip())
    cleaned = []
    for p in parts:
        if p.upper() == "NULL":
            cleaned.append("")
        else:
            cleaned.append(p.strip().strip("`"))
    return cleaned


def parse_sql(path: Path) -> list[tuple[str, list[str], list[dict]]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    schema: dict[str, list[str]] = {}
    for match in CREATE_RE.finditer(text):
        table = match.group(1)
        body = match.group(2)
        cols = []
        for line in body.split(","):
            line = line.strip()
            if not line:
                continue
            if line.upper().startswith(("PRIMARY", "UNIQUE", "KEY", "CONSTRAINT", "INDEX", "FOREIGN")):
                continue
            name = re.split(r"\s+", line)[0].strip("`\"'[]")
            cols.append(name)
        schema[table] = cols

    grouped: dict[str, tuple[list[str], list[dict]]] = {}
    for match in INSERT_RE.finditer(text):
        table = match.group(1)
        col_blob = match.group(2)
        values_blob = match.group(3)
        if col_blob:
            columns = [c.strip().strip("`\"'[]") for c in col_blob.split(",")]
        else:
            columns = schema.get(table, [])
        tuples = _split_sql_values(values_blob)
        rows = grouped.get(table, (columns, []))[1] if table in grouped else []
        if table in grouped and not columns:
            columns = grouped[table][0]
        for t in tuples:
            values = _parse_value_tuple(t)
            if not columns:
                columns = [f"col_{i+1}" for i in range(len(values))]
            row = {columns[i]: values[i] if i < len(values) else "" for i in range(len(columns))}
            row["_row_id"] = str(len(rows) + 1)
            rows.append(row)
        grouped[table] = (columns, rows)

    results = []
    for table, (columns, rows) in grouped.items():
        results.append((table, columns, rows))
    if not results:
        table = path.stem
        results.append((table, [], []))
    return results


def iter_chunks(rows: list[dict], batch_size: int) -> Iterator[list[dict]]:
    for i in range(0, len(rows), batch_size):
        yield rows[i : i + batch_size]


def load_file(path: Path) -> list[tuple[str, list[str], list[dict]]]:
    kind = sniff_type(path.name)
    if kind == "csv":
        table, columns, rows = parse_csv(path)
        return [(table, columns, rows)]
    if kind == "sql":
        return parse_sql(path)
    raise ValueError(f"Unsupported file type: {path.name}")
