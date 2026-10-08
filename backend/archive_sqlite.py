"""Read-only legacy migration path: snapshot shared demo history; never assign it to an account."""
import argparse
import sqlite3
from pathlib import Path

def archive(source: Path, destination: Path):
    if not source.is_file():
        raise ValueError('Source database does not exist')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb'):
        pass
    # SQLite backup captures committed WAL data without modifying the source.
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(destination) as backup:
            original.backup(backup)
            assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        archive(args.source, args.destination)
    except Exception:
        parser.exit(1, 'Backup failed. Source retained. Check paths and choose a new destination.\n')
