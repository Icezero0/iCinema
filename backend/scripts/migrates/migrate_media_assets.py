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


def drop_table_if_exists(conn: sqlite3.Connection, table: str) -> None:
    if not table_exists(conn, table):
        return
    cur = conn.cursor()
    print(f"Dropping table {table} ...")
    cur.execute(f"DROP TABLE {table}")
    conn.commit()


def drop_index_if_exists(conn: sqlite3.Connection, index: str) -> None:
    if not index_exists(conn, index):
        return
    cur = conn.cursor()
    print(f"Dropping index {index} ...")
    cur.execute(f"DROP INDEX {index}")
    conn.commit()


def add_column_if_missing(
    conn: sqlite3.Connection,
    *,
    table: str,
    column: str,
    ddl: str,
) -> bool:
    """
    Return True if the column is added in this run, else False.
    ddl example: "sort_order INTEGER NOT NULL DEFAULT 0"
    """
    if not table_exists(conn, table):
        print(f"Table {table} does not exist, skip adding column {column}.")
        return False

    if get_column_info(conn, table, column) is not None:
        print(f"Column {table}.{column} already exists, skip adding.")
        return False

    cur = conn.cursor()
    print(f"Adding column {table}.{column} ...")
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    conn.commit()
    return True


def is_text_decl_type(decl_type: str | None) -> bool:
    if not decl_type:
        return False
    upper = decl_type.strip().upper()
    return "CHAR" in upper or "TEXT" in upper or "CLOB" in upper


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
            sort_order INTEGER NOT NULL DEFAULT 0,
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


def cleanup_legacy_emojis_table(conn: sqlite3.Connection) -> None:
    """
    外部 emoji 作为真相源后，本地 emojis 主表不再需要。
    如果之前错误地建过，直接删掉。
    """
    if table_exists(conn, "emojis"):
        print("Legacy table emojis exists, dropping it ...")
        drop_table_if_exists(conn, "emojis")
    else:
        print("Table emojis does not exist, skip cleanup.")


def create_user_emoji_usages_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    if table_exists(conn, "user_emoji_usages"):
        print("Table user_emoji_usages already exists, skip creating.")
        return

    print("Creating table user_emoji_usages ...")
    cur.execute(
        """
        CREATE TABLE user_emoji_usages (
            id INTEGER PRIMARY KEY NOT NULL,
            user_id INTEGER NOT NULL,
            provider VARCHAR NOT NULL DEFAULT 'qface',
            emoji_id VARCHAR NOT NULL,
            last_used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def rebuild_user_emoji_usages_table(conn: sqlite3.Connection) -> None:
    """
    将旧版 user_emoji_usages 纠正为：
    - provider VARCHAR NOT NULL DEFAULT 'qface'
    - emoji_id VARCHAR NOT NULL
    并合并重复数据，保留最新 last_used_at。
    """
    print("Rebuilding table user_emoji_usages to external-emoji schema ...")
    cur = conn.cursor()

    old_has_provider = get_column_info(conn, "user_emoji_usages", "provider") is not None
    old_emoji_id_info = get_column_info(conn, "user_emoji_usages", "emoji_id")
    old_has_emoji_id = old_emoji_id_info is not None
    old_has_last_used_at = get_column_info(conn, "user_emoji_usages", "last_used_at") is not None
    old_has_created_at = get_column_info(conn, "user_emoji_usages", "created_at") is not None
    old_has_updated_at = get_column_info(conn, "user_emoji_usages", "updated_at") is not None

    conn.execute("BEGIN TRANSACTION")
    try:
        cur.execute(
            """
            CREATE TABLE user_emoji_usages__new (
                id INTEGER PRIMARY KEY NOT NULL,
                user_id INTEGER NOT NULL,
                provider VARCHAR NOT NULL DEFAULT 'qface',
                emoji_id VARCHAR NOT NULL,
                last_used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        if old_has_emoji_id:
            provider_expr = "provider" if old_has_provider else "'qface'"
            last_used_at_expr = "last_used_at" if old_has_last_used_at else "CURRENT_TIMESTAMP"
            created_at_expr = "created_at" if old_has_created_at else "CURRENT_TIMESTAMP"
            updated_at_expr = "updated_at" if old_has_updated_at else "CURRENT_TIMESTAMP"

            cur.execute(
                f"""
                INSERT INTO user_emoji_usages__new (
                    user_id,
                    provider,
                    emoji_id,
                    last_used_at,
                    created_at,
                    updated_at
                )
                SELECT
                    user_id,
                    provider,
                    emoji_id,
                    MAX(last_used_at) AS last_used_at,
                    MIN(created_at) AS created_at,
                    MAX(updated_at) AS updated_at
                FROM (
                    SELECT
                        user_id AS user_id,
                        {provider_expr} AS provider,
                        CAST(emoji_id AS TEXT) AS emoji_id,
                        {last_used_at_expr} AS last_used_at,
                        {created_at_expr} AS created_at,
                        {updated_at_expr} AS updated_at
                    FROM user_emoji_usages
                    WHERE user_id IS NOT NULL
                      AND emoji_id IS NOT NULL
                )
                GROUP BY user_id, provider, emoji_id
                """
            )

        cur.execute("DROP TABLE user_emoji_usages")
        cur.execute("ALTER TABLE user_emoji_usages__new RENAME TO user_emoji_usages")
        conn.commit()
        print("user_emoji_usages rebuild completed.")
    except Exception:
        conn.rollback()
        raise


def ensure_user_emoji_usages_table(conn: sqlite3.Connection) -> None:
    """
    幂等保证 user_emoji_usages 表结构正确。
    """
    if not table_exists(conn, "user_emoji_usages"):
        create_user_emoji_usages_table(conn)
        return

    provider_info = get_column_info(conn, "user_emoji_usages", "provider")
    emoji_id_info = get_column_info(conn, "user_emoji_usages", "emoji_id")

    needs_rebuild = False

    if provider_info is None:
        needs_rebuild = True
    if emoji_id_info is None:
        needs_rebuild = True
    elif not is_text_decl_type(emoji_id_info[2]):
        needs_rebuild = True

    if not needs_rebuild:
        print("Table user_emoji_usages schema is already correct, skip rebuild.")
        return

    rebuild_user_emoji_usages_table(conn)


def cleanup_legacy_user_emoji_usage_indexes(conn: sqlite3.Connection) -> None:
    """
    旧错误设计的唯一索引是 (user_id, emoji_id)，
    新设计要改成 (user_id, provider, emoji_id)。
    """
    drop_index_if_exists(conn, "uq_user_emoji_usages_user_emoji")


def deduplicate_user_sticker_library_items(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "user_sticker_library_items"):
        print("Table user_sticker_library_items does not exist, skip deduplication.")
        return

    # 如果唯一索引已经存在，理论上不会再有重复
    if index_exists(conn, "uq_user_sticker_library_user_asset"):
        print(
            "Index uq_user_sticker_library_user_asset already exists, "
            "skip sticker library deduplication."
        )
        return

    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT 1
            FROM user_sticker_library_items
            GROUP BY user_id, media_asset_id
            HAVING COUNT(*) > 1
        )
        """
    )
    duplicate_groups = int(cur.fetchone()[0] or 0)

    if duplicate_groups == 0:
        print("No duplicate sticker library rows found, skip deduplication.")
        return

    print(
        f"Found {duplicate_groups} duplicate user sticker library groups, deduplicating ..."
    )

    conn.execute("BEGIN TRANSACTION")
    try:
        # 保留最新一条（id 最大），删除其余重复项
        cur.execute(
            """
            DELETE FROM user_sticker_library_items
            WHERE id NOT IN (
                SELECT keep_id
                FROM (
                    SELECT MAX(id) AS keep_id
                    FROM user_sticker_library_items
                    GROUP BY user_id, media_asset_id
                )
            )
            """
        )
        conn.commit()
        print("Sticker library deduplication completed.")
    except Exception:
        conn.rollback()
        raise


def backfill_user_sticker_sort_order(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "user_sticker_library_items"):
        print("Table user_sticker_library_items does not exist, skip sort_order backfill.")
        return

    if get_column_info(conn, "user_sticker_library_items", "sort_order") is None:
        print("Column user_sticker_library_items.sort_order does not exist, skip backfill.")
        return

    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT user_id
        FROM user_sticker_library_items
        ORDER BY user_id
        """
    )
    user_rows = cur.fetchall()

    if not user_rows:
        print("No sticker library rows found, skip sort_order backfill.")
        return

    print("Backfilling user_sticker_library_items.sort_order ...")

    conn.execute("BEGIN TRANSACTION")
    try:
        for (user_id,) in user_rows:
            cur.execute(
                """
                SELECT id
                FROM user_sticker_library_items
                WHERE user_id = ?
                ORDER BY datetime(created_at) ASC, id ASC
                """,
                (user_id,),
            )
            rows = cur.fetchall()

            # 越新的 sort_order 越大，从而列表按 sort_order DESC 时越靠前
            for sort_order, (row_id,) in enumerate(rows, start=1):
                cur.execute(
                    """
                    UPDATE user_sticker_library_items
                    SET sort_order = ?
                    WHERE id = ?
                    """,
                    (sort_order, row_id),
                )

        conn.commit()
        print("sort_order backfill completed.")
    except Exception:
        conn.rollback()
        raise


def ensure_user_sticker_library_sort_order(conn: sqlite3.Connection) -> None:
    added = add_column_if_missing(
        conn,
        table="user_sticker_library_items",
        column="sort_order",
        ddl="sort_order INTEGER NOT NULL DEFAULT 0",
    )
    if added:
        backfill_user_sticker_sort_order(conn)


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
            "idx_user_sticker_library_user_id_sort_order_created_at",
            """
            CREATE INDEX idx_user_sticker_library_user_id_sort_order_created_at
            ON user_sticker_library_items (user_id, sort_order, created_at)
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
        (
            "uq_user_emoji_usages_user_provider_emoji",
            """
            CREATE UNIQUE INDEX uq_user_emoji_usages_user_provider_emoji
            ON user_emoji_usages (user_id, provider, emoji_id)
            """,
        ),
        (
            "idx_user_emoji_usages_user_id_last_used_at",
            """
            CREATE INDEX idx_user_emoji_usages_user_id_last_used_at
            ON user_emoji_usages (user_id, last_used_at)
            """,
        ),
        (
            "idx_user_emoji_usages_emoji_id",
            """
            CREATE INDEX idx_user_emoji_usages_emoji_id
            ON user_emoji_usages (emoji_id)
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
        (
            "trg_user_emoji_usages_updated_at",
            """
            CREATE TRIGGER trg_user_emoji_usages_updated_at
            AFTER UPDATE ON user_emoji_usages
            FOR EACH ROW
            BEGIN
                UPDATE user_emoji_usages
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

        # 外部 emoji 作为真相源，不再保留本地 emojis 主表
        cleanup_legacy_emojis_table(conn)

        # 幂等保证 user_emoji_usages 结构正确
        ensure_user_emoji_usages_table(conn)

        # 先处理历史数据，再补唯一索引
        deduplicate_user_sticker_library_items(conn)

        # 幂等补字段；只有这次新增时才会回填
        ensure_user_sticker_library_sort_order(conn)

        # 删除旧的错误唯一索引，避免和新设计冲突
        cleanup_legacy_user_emoji_usage_indexes(conn)

        create_indexes(conn)
        create_updated_at_triggers(conn)

        migrate_user_avatars(conn)

        print("Resource domain migration completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()