from pathlib import Path

from app.services.parser import parse_csv, parse_sql
from app.services.seed import generate_samples


def test_parse_generated_csv_and_sql(tmp_path: Path):
    paths = generate_samples(tmp_path)
    table, columns, rows = parse_csv(paths["database_a"])
    assert "email" in columns
    assert len(rows) >= 5
    assert rows[0]["email"]

    tables = parse_sql(paths["database_d"])
    assert tables
    name, cols, sql_rows = tables[0]
    assert name == "members"
    assert "member_id" in cols
    assert len(sql_rows) >= 4
