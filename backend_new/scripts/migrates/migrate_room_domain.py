import sqlite3
from pathlib import Path


def ensure_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True if column exists, else False."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]  # row[1] = column name
    return column in cols


def add_role_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("ALTER TABLE room_members ADD COLUMN role VARCHAR(16)")
    conn.commit()


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        # 1) Ensure room_members.role exists
        if ensure_column_exists(conn, "room_members", "role"):
            print("Column room_members.role already exists.")
        else:
            print("Adding column room_members.role ...")
            add_role_column(conn)
            print("Added column room_members.role.")

        # 2) Copy user_type -> role (only fill empty role)
        cur = conn.cursor()
        cur.execute("SELECT room_id, user_id, user_type, role FROM room_members")
        rows = cur.fetchall()

        updated = 0
        skipped_has_role = 0
        skipped_no_user_type = 0

        for room_id, user_id, user_type, role in rows:
            if role and str(role).strip():
                skipped_has_role += 1
                continue

            if not user_type or not str(user_type).strip():
                skipped_no_user_type += 1
                continue

            cur.execute(
                """
                UPDATE room_members
                SET role = ?
                WHERE room_id = ? AND user_id = ?
                """,
                (str(user_type).strip(), room_id, user_id),
            )
            updated += 1

        conn.commit()

        print("migrated room_members.role rows:", updated)
        print("skipped (already has role):", skipped_has_role)
        print("skipped (no user_type):", skipped_no_user_type)
        print("Room domain migration completed.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()