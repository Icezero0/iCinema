import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings


TARGET_USER_ID = 1
ADMIN_ROLE = "admin"


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


def main() -> int:
    db = get_settings().db_path
    print("DB:", db)

    if not db.exists():
        print(f"Database file does not exist: {db}")
        return 1

    conn = sqlite3.connect(str(db))
    try:
        if not table_exists(conn, "users"):
            print("Table users does not exist.")
            return 1

        if not column_exists(conn, "users", "site_role"):
            print("Column users.site_role does not exist. Run migrations first.")
            return 1

        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, username, site_role FROM users WHERE id = ?",
            (TARGET_USER_ID,),
        )
        row = cur.fetchone()
        if row is None:
            print(f"User id={TARGET_USER_ID} does not exist.")
            return 1

        user_id, email, username, current_role = row
        if current_role == ADMIN_ROLE:
            print(
                f"User id={user_id} ({username or email}) is already site admin."
            )
            return 0

        cur.execute(
            "UPDATE users SET site_role = ? WHERE id = ?",
            (ADMIN_ROLE, TARGET_USER_ID),
        )
        conn.commit()
        print(
            f"Granted site admin to user id={user_id} ({username or email}). "
            f"Previous role: {current_role}"
        )
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
