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


def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    rows = cur.fetchall()
    return any(row[1] == column for row in rows)


def create_room_settings_table(
    conn: sqlite3.Connection, table_name: str = "room_settings"
) -> None:
    cur = conn.cursor()

    cur.execute(
        f"""
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL UNIQUE,
            selected_room_video_source_type VARCHAR(32) NOT NULL DEFAULT 'external_url',
            sync_policy VARCHAR(32) NOT NULL DEFAULT 'auto_sync',
            active_sync_permission VARCHAR(32) NOT NULL DEFAULT 'owner_and_manager',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(room_id) REFERENCES rooms(id) ON DELETE CASCADE,
            CHECK (selected_room_video_source_type IN ('external_url', 'local_file')),
            CHECK (sync_policy IN ('auto_sync', 'disabled')),
            CHECK (active_sync_permission IN ('owner_only', 'owner_and_manager', 'all_members'))
        )
        """
    )

    conn.commit()
    print(f"Created table {table_name}.")


def migrate_room_settings_table(conn: sqlite3.Connection) -> None:
    """
    将旧版 room_settings 迁移到新版结构：
    - media_source_type -> selected_room_video_source_type
    - sync_policy 收敛为 auto_sync / disabled
    """
    cur = conn.cursor()

    old_has_new_col = column_exists(
        conn, "room_settings", "selected_room_video_source_type"
    )
    old_has_old_col = column_exists(conn, "room_settings", "media_source_type")

    if not old_has_new_col and not old_has_old_col:
        raise RuntimeError(
            "room_settings exists, but neither media_source_type nor "
            "selected_room_video_source_type column was found."
        )

    source_type_column = (
        "selected_room_video_source_type" if old_has_new_col else "media_source_type"
    )

    cur.execute("DROP TABLE IF EXISTS room_settings__new")
    conn.commit()

    create_room_settings_table(conn, table_name="room_settings__new")

    cur.execute(
        f"""
        INSERT INTO room_settings__new (
            id,
            room_id,
            selected_room_video_source_type,
            sync_policy,
            active_sync_permission,
            created_at,
            updated_at
        )
        SELECT
            id,
            room_id,
            CASE
                WHEN {source_type_column} IN ('external_url', 'local_file')
                    THEN {source_type_column}
                ELSE 'external_url'
            END,
            CASE
                WHEN sync_policy IN ('auto_sync', 'auto_pause') THEN 'auto_sync'
                WHEN sync_policy IN ('auto_seek', 'auto_speed', 'disabled') THEN 'disabled'
                ELSE 'auto_sync'
            END,
            CASE
                WHEN active_sync_permission IN ('owner_only', 'owner_and_manager', 'all_members')
                    THEN active_sync_permission
                ELSE 'owner_and_manager'
            END,
            created_at,
            updated_at
        FROM room_settings
        """
    )

    copied = cur.rowcount
    conn.commit()
    print("Copied room_settings rows into room_settings__new:", copied)

    conn.execute("PRAGMA foreign_keys=OFF")
    try:
        cur.execute("DROP TABLE room_settings")
        cur.execute("ALTER TABLE room_settings__new RENAME TO room_settings")
        conn.commit()
    finally:
        conn.execute("PRAGMA foreign_keys=ON")

    print("Migrated room_settings to new schema.")


def backfill_room_settings(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO room_settings (
            room_id,
            selected_room_video_source_type,
            sync_policy,
            active_sync_permission,
            created_at,
            updated_at
        )
        SELECT
            r.id,
            'external_url',
            'auto_sync',
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
            print("Table room_settings already exists, migrating schema if needed...")
            migrate_room_settings_table(conn)
        else:
            create_room_settings_table(conn)

        backfill_room_settings(conn)

        print("room_settings migration completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
