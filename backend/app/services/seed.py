import csv
from pathlib import Path

from app.config import SAMPLE_DIR

OVERLAPPING_PEOPLE = [
    {
        "name": "John Carter",
        "email": "john.carter@example.com",
        "phone": "+1-415-555-0198",
        "username": "jcarter",
        "member_id": "MEM-1001",
        "address": "12 Market St, San Francisco, CA",
        "company": "Northwind Labs",
        "city": "San Francisco",
    },
    {
        "name": "Aisha Rahman",
        "email": "aisha.rahman@example.com",
        "phone": "9876543210",
        "username": "aishar",
        "member_id": "MEM-2044",
        "address": "88 MG Road, Bengaluru",
        "company": "Horizon Pay",
        "city": "Bengaluru",
    },
    {
        "name": "Luis Mendoza",
        "email": "luis.mendoza@example.net",
        "phone": "+52 55 1234 7788",
        "username": "lmendoza",
        "member_id": "MEM-3310",
        "address": "Av. Reforma 450, CDMX",
        "company": "Sol y Mar",
        "city": "Mexico City",
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@example.org",
        "phone": "9123456780",
        "username": "priyan",
        "member_id": "MEM-4421",
        "address": "14 Marine Drive, Mumbai",
        "company": "BluePeak Soft",
        "city": "Mumbai",
    },
    {
        "name": "Chen Wei",
        "email": "chen.wei@example.com",
        "phone": "+86 138 0013 8000",
        "username": "chenwei",
        "member_id": "MEM-5502",
        "address": "88 Nanjing Rd, Shanghai",
        "company": "Lotus Analytics",
        "city": "Shanghai",
    },
]


def _extra_people(count: int, start: int):
    rows = []
    for i in range(start, start + count):
        rows.append(
            {
                "name": f"User {i}",
                "email": f"user{i}@sample.dev",
                "phone": f"90000{i:05d}"[-10:],
                "username": f"user{i}",
                "member_id": f"MEM-{7000 + i}",
                "address": f"{i} Sample Ave",
                "company": f"Org {i % 17}",
                "city": ["Delhi", "Austin", "London", "Tokyo", "Sydney"][i % 5],
            }
        )
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def generate_samples(output_dir: Path | None = None) -> dict[str, Path]:
    out = output_dir or SAMPLE_DIR
    out.mkdir(parents=True, exist_ok=True)

    extras = _extra_people(40, 100)

    db_a = []
    for p in OVERLAPPING_PEOPLE + extras[:12]:
        db_a.append(
            {
                "full_name": p["name"],
                "email": p["email"],
                "mobile_number": p["phone"],
                "city": p["city"],
            }
        )
    path_a = out / "database_a_crm.csv"
    write_csv(path_a, ["full_name", "email", "mobile_number", "city"], db_a)

    db_b = []
    for p in [OVERLAPPING_PEOPLE[0], OVERLAPPING_PEOPLE[1], OVERLAPPING_PEOPLE[3]] + extras[8:20]:
        db_b.append(
            {
                "email_id": p["email"],
                "address": p["address"],
                "country": "IN" if p["city"] in {"Bengaluru", "Mumbai", "Delhi"} else "US",
            }
        )
    path_b = out / "database_b_billing.csv"
    write_csv(path_b, ["email_id", "address", "country"], db_b)

    db_c = []
    for p in [OVERLAPPING_PEOPLE[1], OVERLAPPING_PEOPLE[2], OVERLAPPING_PEOPLE[4]] + extras[15:28]:
        db_c.append(
            {
                "username": p["username"],
                "contact_no": p["phone"],
                "company": p["company"],
            }
        )
    path_c = out / "database_c_directory.csv"
    write_csv(path_c, ["username", "contact_no", "company"], db_c)

    db_d_rows = []
    for p in [OVERLAPPING_PEOPLE[0], OVERLAPPING_PEOPLE[2], OVERLAPPING_PEOPLE[3], OVERLAPPING_PEOPLE[4]] + extras[25:40]:
        db_d_rows.append(
            f"('{p['member_id']}', '{p['email']}', '{p['username']}', '{p['name']}')"
        )
    path_d = out / "database_d_members.sql"
    sql = (
        "CREATE TABLE members (\n"
        "  member_id VARCHAR(32),\n"
        "  email_address VARCHAR(255),\n"
        "  user_name VARCHAR(64),\n"
        "  full_name VARCHAR(128)\n"
        ");\n\n"
        "INSERT INTO members (member_id, email_address, user_name, full_name) VALUES\n"
        + ",\n".join(db_d_rows)
        + ";\n"
    )
    path_d.write_text(sql, encoding="utf-8")

    part1 = extras[:8]
    part2 = extras[8:16]
    path_p1 = out / "database_a_part1.csv"
    path_p2 = out / "database_a_part2.csv"
    write_csv(
        path_p1,
        ["full_name", "email", "mobile_number", "city"],
        [{"full_name": p["name"], "email": p["email"], "mobile_number": p["phone"], "city": p["city"]} for p in part1],
    )
    write_csv(
        path_p2,
        ["full_name", "email", "mobile_number", "city"],
        [{"full_name": p["name"], "email": p["email"], "mobile_number": p["phone"], "city": p["city"]} for p in part2],
    )

    return {
        "database_a": path_a,
        "database_b": path_b,
        "database_c": path_c,
        "database_d": path_d,
        "part1": path_p1,
        "part2": path_p2,
    }
