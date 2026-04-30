import sqlite3
from pathlib import Path


def ensure_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def get_column_info(conn: sqlite3.Connection, table: str, column: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
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

        normalized_role = str(user_type).strip().lower()

        cur.execute(
            """
            UPDATE room_members
            SET role = ?
            WHERE room_id = ? AND user_id = ?
            """,
            (normalized_role, room_id, user_id),
        )
        updated += 1

    conn.commit()

    print("backfilled room_members.role rows:", updated)
    print("skipped (already has role):", skipped_has_role)
    print("skipped (no user_type):", skipped_no_user_type)


def normalize_role_case(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE room_members
        SET role = LOWER(TRIM(role))
        WHERE role IS NOT NULL AND TRIM(role) <> ''
        """
    )
    updated = cur.rowcount
    conn.commit()

    print("normalized room_members.role rows:", updated)


def rebuild_room_members(conn: sqlite3.Connection) -> None:
    """
    Rebuild room_members to ensure:
    - joined_at defaults to CURRENT_TIMESTAMP
    - user_type is nullable
    - role is NOT NULL and normalized to lowercase
    """
    cur = conn.cursor()

    print("Rebuilding room_members ...")

    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("BEGIN TRANSACTION")

    try:
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
            SELECT
                room_id,
                user_id,
                COALESCE(joined_at, CURRENT_TIMESTAMP),
                user_type,
                LOWER(TRIM(role))
            FROM room_members
            """
        )

        cur.execute("DROP TABLE room_members")
        cur.execute("ALTER TABLE room_members_new RENAME TO room_members")

        conn.commit()
        print("room_members rebuilt successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.execute("PRAGMA foreign_keys=ON")


def room_members_needs_rebuild(conn: sqlite3.Connection) -> bool:
    user_type_info = get_column_info(conn, "room_members", "user_type")
    joined_at_info = get_column_info(conn, "room_members", "joined_at")
    role_info = get_column_info(conn, "room_members", "role")

    user_type_not_nullable = user_type_info is not None and user_type_info[3] == 1
    joined_at_missing_default = joined_at_info is None or joined_at_info[4] != "CURRENT_TIMESTAMP"
    role_notnull_missing = role_info is None or role_info[3] != 1

    return user_type_not_nullable or joined_at_missing_default or role_notnull_missing


def rebuild_rooms(conn: sqlite3.Connection) -> None:
    """
    Rebuild rooms to ensure:
    - created_at defaults to CURRENT_TIMESTAMP
    - is_public defaults to 0
    - visibility is NOT NULL with default 'private'
    - join_audit_mode is NOT NULL with default 'manual_review'
    - preserve config / owner / name / id
    - remove legacy is_active field if still present
    - if old is_public exists, backfill visibility from it:
        is_public = 1 -> public
        else -> private
    """
    cur = conn.cursor()

    print("Rebuilding rooms ...")

    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("BEGIN TRANSACTION")

    try:
        cur.execute(
            """
            CREATE TABLE rooms_new (
                id INTEGER PRIMARY KEY NOT NULL,
                name VARCHAR NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER NOT NULL,
                is_public BOOLEAN NOT NULL DEFAULT 0,
                visibility VARCHAR(16) NOT NULL DEFAULT 'private',
                join_audit_mode VARCHAR(32) NOT NULL DEFAULT 'manual_review',
                config VARCHAR
            )
            """
        )

        cols = {row[1] for row in cur.execute("PRAGMA table_info(rooms)").fetchall()}

        has_is_public = "is_public" in cols
        has_config = "config" in cols
        has_visibility = "visibility" in cols
        has_join_audit_mode = "join_audit_mode" in cols

        # is_public select expression
        if has_is_public:
            is_public_expr = "COALESCE(is_public, 0)"
        else:
            is_public_expr = "0"

        # visibility select expression
        # 优先保留已存在的 visibility；否则从 is_public 回填；再否则默认 private
        if has_visibility:
            visibility_expr = """
                COALESCE(
                    NULLIF(TRIM(visibility), ''),
                    CASE WHEN COALESCE(is_public, 0) = 1 THEN 'public' ELSE 'private' END
                )
            """ if has_is_public else """
                COALESCE(NULLIF(TRIM(visibility), ''), 'private')
            """
        else:
            visibility_expr = """
                CASE WHEN COALESCE(is_public, 0) = 1 THEN 'public' ELSE 'private' END
            """ if has_is_public else "'private'"

        # join_audit_mode select expression
        # 若旧表已有该字段，优先保留；否则统一默认 manual_review
        if has_join_audit_mode:
            join_audit_mode_expr = "COALESCE(NULLIF(TRIM(join_audit_mode), ''), 'manual_review')"
        else:
            join_audit_mode_expr = "'manual_review'"

        # config select expression
        if has_config:
            config_expr = "config"
        else:
            config_expr = "NULL"

        select_sql = f"""
            INSERT INTO rooms_new (
                id,
                name,
                created_at,
                owner_id,
                is_public,
                visibility,
                join_audit_mode,
                config
            )
            SELECT
                id,
                name,
                COALESCE(created_at, CURRENT_TIMESTAMP),
                owner_id,
                {is_public_expr},
                {visibility_expr},
                {join_audit_mode_expr},
                {config_expr}
            FROM rooms
        """

        cur.execute(select_sql)

        cur.execute("DROP TABLE rooms")
        cur.execute("ALTER TABLE rooms_new RENAME TO rooms")

        conn.commit()
        print("rooms rebuilt successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.execute("PRAGMA foreign_keys=ON")


def rooms_needs_rebuild(conn: sqlite3.Connection) -> bool:
    created_at_info = get_column_info(conn, "rooms", "created_at")
    is_public_info = get_column_info(conn, "rooms", "is_public")
    visibility_info = get_column_info(conn, "rooms", "visibility")
    join_audit_mode_info = get_column_info(conn, "rooms", "join_audit_mode")
    is_active_exists = ensure_column_exists(conn, "rooms", "is_active")

    created_at_missing_default = created_at_info is None or created_at_info[4] != "CURRENT_TIMESTAMP"

    is_public_missing_default = is_public_info is None or is_public_info[4] != "0"
    is_public_nullable = is_public_info is not None and is_public_info[3] != 1

    visibility_missing = visibility_info is None
    visibility_nullable = visibility_info is not None and visibility_info[3] != 1
    visibility_missing_default = visibility_info is None or visibility_info[4] != "'private'"

    join_audit_mode_missing = join_audit_mode_info is None
    join_audit_mode_nullable = join_audit_mode_info is not None and join_audit_mode_info[3] != 1
    join_audit_mode_missing_default = (
        join_audit_mode_info is None or join_audit_mode_info[4] != "'manual_review'"
    )

    return (
        is_active_exists
        or created_at_missing_default
        or is_public_missing_default
        or is_public_nullable
        or visibility_missing
        or visibility_nullable
        or visibility_missing_default
        or join_audit_mode_missing
        or join_audit_mode_nullable
        or join_audit_mode_missing_default
    )


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        if ensure_column_exists(conn, "room_members", "role"):
            print("Column room_members.role already exists.")
        else:
            print("Adding column room_members.role ...")
            add_role_column(conn)
            print("Added column room_members.role.")

        backfill_role_from_user_type(conn)
        normalize_role_case(conn)

        if room_members_needs_rebuild(conn):
            rebuild_room_members(conn)
        else:
            print("room_members already matches target schema, skip rebuilding.")

        if rooms_needs_rebuild(conn):
            rebuild_rooms(conn)
        else:
            print("rooms already matches target schema, skip rebuilding.")

        print("Room domain migration completed.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()