"""Maintainer-only local export. No public API or browser administrator credentials."""
import argparse
import csv
from pathlib import Path
import sqlalchemy as sa
from database import feedback, get_connection

def export_feedback(path: Path):
    # Exclusive creation avoids overwriting an existing review/export.
    with get_connection() as conn, path.open('x', encoding='utf-8', newline='') as output:
        rows = conn.execute(sa.select(feedback).order_by(feedback.c.created_at)).mappings()
        writer = csv.DictWriter(output, fieldnames=list(feedback.c.keys()))
        writer.writeheader()
        for row in rows:
            # CSV spreadsheet applications must not interpret user text as formulas.
            writer.writerow({key: "'" + value if isinstance(value, str) and
                (value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n'))) else value for key, value in row.items()})

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        export_feedback(args.output)
    except Exception:
        parser.exit(1, 'Export failed. Check database access and use a new, private output filename.\n')
