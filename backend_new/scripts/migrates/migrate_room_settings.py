import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table,),
    )
    return cur.fetchone() is not None


def create_room_settings_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE room_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL UNIQUE,
            media_source_type VARCHAR(32) NOT NULL DEFAULT 'external_url',
            sync_policy VARCHAR(32) NOT NULL DEFAULT 'auto_pause',
            active_sync_permission VARCHAR(32) NOT NULL DEFAULT 'owner_and_manager',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
            CHECK (media_source_type IN ('external_url', 'local_file')),
            CHECK (sync_policy IN ('auto_pause', 'auto_seek', 'disabled')),
            CHECK (active_sync_permission IN ('owner_only', 'owner_and_manager', 'all_members'))
        )
        """
    )

    conn.commit()
    print("Created table room_settings.")


def backfill_room_settings(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO room_settings (
            room_id,
            media_source_type,
            sync_policy,
            active_sync_permission,
            created_at,
            updated_at
        )
        SELECT
            r.id,
            'external_url',
            'auto_pause',
            'owner_and_manager',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        FROM rooms r
        LEFT JOIN room_settings rs ON rs.room_id = r.id
        WHERE rs.room_id IS NULL
        """
    )

    inserted = cur.rowcount
    conn.commit()
    print("Backfilled room_settings rows:", inserted)


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA foreign_keys=ON")

        if table_exists(conn, "room_settings"):
            print("Table room_settings already exists.")
        else:
            create_room_settings_table(conn)

        backfill_room_settings(conn)

        print("room_settings migration completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()