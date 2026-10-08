import sqlite3
import pytest
import sqlalchemy as sa
from archive_sqlite import archive
from feedback_export import export_feedback
import database

def test_legacy_backup_retains_demo_without_import_or_overwrite(tmp_path):
    source, target = tmp_path / 'old.sqlite3', tmp_path / 'backup.sqlite3'
    with sqlite3.connect(source) as conn:
        conn.execute('CREATE TABLE users(id TEXT)')
        conn.execute("INSERT INTO users VALUES ('demo')")
    archive(source, target)
    for path in (source, target):
        with sqlite3.connect(path) as conn:
            assert conn.execute('SELECT id FROM users').fetchall() == [('demo',)]
    with pytest.raises(FileExistsError):
        archive(source, target)

def test_feedback_export_is_local_exclusive_and_formula_safe(isolated_db, tmp_path):
    database.save_feedback({'type': 'review', 'rating': 5, 'message': '=1+1', 'session_id': None})
    database.save_feedback({'type': 'review', 'rating': 4, 'message': '  =2+2', 'session_id': None})
    target = tmp_path / 'feedback.csv'
    export_feedback(target)
    assert "'=1+1" in target.read_text(encoding='utf-8')
    assert "'  =2+2" in target.read_text(encoding='utf-8')
    with pytest.raises(FileExistsError):
        export_feedback(target)
