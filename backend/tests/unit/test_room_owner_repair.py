import importlib.util
from pathlib import Path
import sqlite3


def test_owner_repair_restores_missing_and_wrong_roles_without_changing_members(monkeypatch):
    path = Path(__file__).resolve().parents[2] / "alembic/versions/f16d80d97501_restore_room_owners.py"
    spec = importlib.util.spec_from_file_location("owner_repair", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with sqlite3.connect(":memory:") as db:
        db.executescript("""
            CREATE TABLE rooms (id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL);
            CREATE TABLE room_members (room_id INTEGER, user_id INTEGER, role TEXT,
                PRIMARY KEY(room_id, user_id));
            INSERT INTO rooms VALUES (1, 1), (2, 2), (3, 3);
            INSERT INTO room_members VALUES (2, 2, 'invalid'), (3, 3, 'owner'), (3, 4, 'member');
        """)
        monkeypatch.setattr(migration.op, "execute", db.execute)
        migration.upgrade()
        migration.upgrade()
        assert db.execute("SELECT * FROM room_members ORDER BY room_id, user_id").fetchall() == [
            (1, 1, "owner"), (2, 2, "owner"), (3, 3, "owner"), (3, 4, "member")]
        migration.downgrade()
        assert db.execute("SELECT COUNT(*) FROM room_members").fetchone()[0] == 4
