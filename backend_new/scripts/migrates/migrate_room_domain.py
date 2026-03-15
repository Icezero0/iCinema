import sqlite3
from pathlib import Path


def ensure_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True if column exists, else False."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def get_column_info(conn: sqlite3.Connection, table: str, column: str):
    """Return PRAGMA table_info row for a column, or None."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        # row: cid, name, type, notnull, dflt_value, pk
        if row[1] == column:
            return row
    return None


def add_role_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("ALTER TABLE room_members ADD COLUMN role VARCHAR(16)")
    conn.commit()


def backfill_role_from_user_type(conn: sqlite3.Connection) -> None:
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


def rebuild_room_members_make_user_type_nullable(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    print("Rebuilding room_members to make user_type nullable ...")

    cur.execute("PRAGMA foreign_keys=OFF;")
    conn.commit()

    cur.execute(
        """
        CREATE TABLE room_members_new (
            room_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_type VARCHAR(16),
            role VARCHAR(16) NOT NULL,
            PRIMARY KEY (room_id, user_id),
            FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        INSERT INTO room_members_new (room_id, user_id, joined_at, user_type, role)
        SELECT room_id, user_id, joined_at, user_type, role
        FROM room_members
        """
    )

    cur.execute("DROP TABLE room_members")
    cur.execute("ALTER TABLE room_members_new RENAME TO room_members")

    cur.execute("PRAGMA foreign_keys=ON;")
    conn.commit()

    print("room_members.user_type is now nullable.")


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
        backfill_role_from_user_type(conn)

        # 3) Ensure user_type is nullable
        user_type_info = get_column_info(conn, "room_members", "user_type")
        if user_type_info is None:
            print("Column room_members.user_type does not exist, skip nullable migration.")
        else:
            # row[3] == notnull flag, 1 means NOT NULL
            if user_type_info[3] == 1:
                rebuild_room_members_make_user_type_nullable(conn)
            else:
                print("Column room_members.user_type is already nullable.")

        print("Room domain migration completed.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()