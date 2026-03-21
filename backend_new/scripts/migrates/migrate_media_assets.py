import sqlite3
from pathlib import Path


def infer_mime_type_from_key(storage_key: str | None) -> str:
    if not storage_key:
        return "application/octet-stream"

    key = storage_key.lower()

    if key.endswith(".jpg") or key.endswith(".jpeg"):
        return "image/jpeg"
    if key.endswith(".png"):
        return "image/png"
    if key.endswith(".webp"):
        return "image/webp"
    if key.endswith(".gif"):
        return "image/gif"

    return "application/octet-stream"


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def index_exists(conn: sqlite3.Connection, index: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        (index,),
    )
    return cur.fetchone() is not None


def trigger_exists(conn: sqlite3.Connection, trigger: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name = ?",
        (trigger,),
    )
    return cur.fetchone() is not None


def get_column_info(conn: sqlite3.Connection, table: str, column: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        # row: cid, name, type, notnull, dflt_value, pk
        if row[1] == column:
            return row
    return None


def create_media_assets_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    if table_exists(conn, "media_assets"):
        print("Table media_assets already exists, skip creating.")
        return

    print("Creating table media_assets ...")
    cur.execute(
        """
        CREATE TABLE media_assets (
            id INTEGER PRIMARY KEY NOT NULL,
            asset_type VARCHAR NOT NULL,
            storage_key VARCHAR NOT NULL,
            mime_type VARCHAR NOT NULL,
            file_size INTEGER NOT NULL,
            width INTEGER,
            height INTEGER,
            duration_seconds INTEGER,
            sha256 VARCHAR,
            uploaded_by_user_id INTEGER,
            status VARCHAR NOT NULL DEFAULT 'active',
            expires_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def create_user_avatar_assets_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    if table_exists(conn, "user_avatar_assets"):
        print("Table user_avatar_assets already exists, skip creating.")
        return

    print("Creating table user_avatar_assets ...")
    cur.execute(
        """
        CREATE TABLE user_avatar_assets (
            id INTEGER PRIMARY KEY NOT NULL,
            user_id INTEGER NOT NULL,
            media_asset_id INTEGER NOT NULL,
            is_deleted BOOLEAN NOT NULL DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def create_user_sticker_library_items_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    if table_exists(conn, "user_sticker_library_items"):
        print("Table user_sticker_library_items already exists, skip creating.")
        return

    print("Creating table user_sticker_library_items ...")
    cur.execute(
        """
        CREATE TABLE user_sticker_library_items (
            id INTEGER PRIMARY KEY NOT NULL,
            user_id INTEGER NOT NULL,
            media_asset_id INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def create_message_resource_refs_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    if table_exists(conn, "message_resource_refs"):
        print("Table message_resource_refs already exists, skip creating.")
        return

    print("Creating table message_resource_refs ...")
    cur.execute(
        """
        CREATE TABLE message_resource_refs (
            id INTEGER PRIMARY KEY NOT NULL,
            message_id INTEGER NOT NULL,
            media_asset_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def create_indexes(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    indexes = [
        (
            "uq_media_assets_asset_type_storage_key",
            """
            CREATE UNIQUE INDEX uq_media_assets_asset_type_storage_key
            ON media_assets (asset_type, storage_key)
            """,
        ),
        (
            "idx_media_assets_asset_type",
            """
            CREATE INDEX idx_media_assets_asset_type
            ON media_assets (asset_type)
            """,
        ),
        (
            "idx_media_assets_uploaded_by_user_id",
            """
            CREATE INDEX idx_media_assets_uploaded_by_user_id
            ON media_assets (uploaded_by_user_id)
            """,
        ),
        (
            "idx_media_assets_status_expires_at",
            """
            CREATE INDEX idx_media_assets_status_expires_at
            ON media_assets (status, expires_at)
            """,
        ),
        (
            "idx_media_assets_sha256",
            """
            CREATE INDEX idx_media_assets_sha256
            ON media_assets (sha256)
            """,
        ),
        (
            "uq_user_avatar_assets_user_id_active",
            """
            CREATE UNIQUE INDEX uq_user_avatar_assets_user_id_active
            ON user_avatar_assets (user_id)
            WHERE is_deleted = 0
            """,
        ),
        (
            "idx_user_avatar_assets_media_asset_id",
            """
            CREATE INDEX idx_user_avatar_assets_media_asset_id
            ON user_avatar_assets (media_asset_id)
            """,
        ),
        (
            "uq_user_sticker_library_user_asset",
            """
            CREATE UNIQUE INDEX uq_user_sticker_library_user_asset
            ON user_sticker_library_items (user_id, media_asset_id)
            """,
        ),
        (
            "idx_user_sticker_library_user_id_created_at",
            """
            CREATE INDEX idx_user_sticker_library_user_id_created_at
            ON user_sticker_library_items (user_id, created_at)
            """,
        ),
        (
            "uq_message_resource_refs_message_asset",
            """
            CREATE UNIQUE INDEX uq_message_resource_refs_message_asset
            ON message_resource_refs (message_id, media_asset_id)
            """,
        ),
        (
            "idx_message_resource_refs_media_asset_id",
            """
            CREATE INDEX idx_message_resource_refs_media_asset_id
            ON message_resource_refs (media_asset_id)
            """,
        ),
    ]

    for index_name, sql in indexes:
        if index_exists(conn, index_name):
            print(f"Index {index_name} already exists, skip creating.")
            continue

        print(f"Creating index {index_name} ...")
        cur.execute(sql)

    conn.commit()


def create_updated_at_triggers(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    triggers = [
        (
            "trg_media_assets_updated_at",
            """
            CREATE TRIGGER trg_media_assets_updated_at
            AFTER UPDATE ON media_assets
            FOR EACH ROW
            BEGIN
                UPDATE media_assets
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.id;
            END;
            """,
        ),
        (
            "trg_user_avatar_assets_updated_at",
            """
            CREATE TRIGGER trg_user_avatar_assets_updated_at
            AFTER UPDATE ON user_avatar_assets
            FOR EACH ROW
            BEGIN
                UPDATE user_avatar_assets
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.id;
            END;
            """,
        ),
    ]

    for trigger_name, sql in triggers:
        if trigger_exists(conn, trigger_name):
            print(f"Trigger {trigger_name} already exists, skip creating.")
            continue

        print(f"Creating trigger {trigger_name} ...")
        cur.execute(sql)

    conn.commit()


def user_has_active_avatar_relation(conn: sqlite3.Connection, user_id: int) -> bool:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1
        FROM user_avatar_assets
        WHERE user_id = ? AND is_deleted = 0
        LIMIT 1
        """,
        (user_id,),
    )
    return cur.fetchone() is not None


def migrate_user_avatars(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        print("Table users does not exist, skip avatar migration.")
        return

    avatar_key_info = get_column_info(conn, "users", "avatar_key")
    if avatar_key_info is None:
        print("Column users.avatar_key does not exist, skip avatar migration.")
        return

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, avatar_key
        FROM users
        WHERE avatar_key IS NOT NULL
          AND TRIM(avatar_key) != ''
        ORDER BY id
        """
    )
    rows = cur.fetchall()

    if not rows:
        print("No legacy avatar_key data found, skip avatar migration.")
        return

    print(f"Found {len(rows)} users with legacy avatar_key, migrating avatars ...")

    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN TRANSACTION")

    migrated_count = 0
    skipped_count = 0

    try:
        for user_id, avatar_key in rows:
            if user_has_active_avatar_relation(conn, user_id):
                skipped_count += 1
                continue

            avatar_key = avatar_key.strip()

            cur.execute(
                """
                INSERT INTO media_assets (
                    asset_type,
                    storage_key,
                    mime_type,
                    file_size,
                    width,
                    height,
                    duration_seconds,
                    sha256,
                    uploaded_by_user_id,
                    status,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "avatar",
                    avatar_key,
                    infer_mime_type_from_key(avatar_key),
                    0,
                    None,
                    None,
                    None,
                    None,
                    user_id,
                    "active",
                    None,
                ),
            )
            media_asset_id = cur.lastrowid

            cur.execute(
                """
                INSERT INTO user_avatar_assets (
                    user_id,
                    media_asset_id,
                    is_deleted
                )
                VALUES (?, ?, ?)
                """,
                (
                    user_id,
                    media_asset_id,
                    0,
                ),
            )

            migrated_count += 1

        conn.commit()
        print(
            f"Avatar migration completed. migrated={migrated_count}, skipped={skipped_count}"
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        create_media_assets_table(conn)
        create_user_avatar_assets_table(conn)
        create_user_sticker_library_items_table(conn)
        create_message_resource_refs_table(conn)

        create_indexes(conn)
        create_updated_at_triggers(conn)

        migrate_user_avatars(conn)

        print("Resource domain migration completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()