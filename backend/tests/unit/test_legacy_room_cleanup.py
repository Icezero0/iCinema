import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine


def test_legacy_startup_timestamp_aborts_cleanup_without_deleting_members(monkeypatch):
    path = Path(__file__).resolve().parents[2] / "alembic/versions/a71c5e4d2b90_prevent_deleted_room_data_reuse.py"
    spec = importlib.util.spec_from_file_location("legacy_room_cleanup", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as db:
        db.exec_driver_sql("CREATE TABLE rooms (id INTEGER PRIMARY KEY, created_at TEXT)")
        db.exec_driver_sql("CREATE TABLE room_members (room_id INTEGER, user_id INTEGER, joined_at TEXT)")
        # Old default=datetime.now(...) assigned startup time even to users
        # joining a room created later during the same server process.
        db.exec_driver_sql("INSERT INTO rooms VALUES (1, '2025-06-19 15:35:39.938586')")
        db.exec_driver_sql("INSERT INTO room_members VALUES (1, 2, '2025-06-19 15:00:00.000000')")
        monkeypatch.setattr(migration.op, "get_bind", lambda: db)
        def no_cleanup(*args):
            pytest.fail("Cleanup must not begin before legacy membership review")
        monkeypatch.setattr(migration.op, "execute", no_cleanup)
        with pytest.raises(RuntimeError, match="Ambiguous legacy room memberships"):
            migration.upgrade()
        assert db.exec_driver_sql("SELECT room_id, user_id FROM room_members").all() == [(1, 2)]
    engine.dispose()
