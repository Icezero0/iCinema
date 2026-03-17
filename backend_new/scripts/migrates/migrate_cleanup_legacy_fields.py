import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def cleanup_users_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "users"):
        print("Table users does not exist, skipped.")
        return

    cols = get_columns(conn, "users")
    if "avatar_path" not in cols:
        print("users table already cleaned (avatar_path not found).")
        return

    print("Cleaning users table: removing avatar_path ...")
    cur = conn.cursor()
    cur.execute("BEGIN")

    try:
        cur.execute(
            """
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(64),
                hashed_password VARCHAR(255) NOT NULL,
                auto_accept BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                avatar_key TEXT
            )
            """
        )

        old_cols = set(cols)

        if "avatar_key" in old_cols:
            cur.execute(
                """
                INSERT INTO users_new (id, email, username, hashed_password, auto_accept, created_at, avatar_key)
                SELECT id, email, username, hashed_password, COALESCE(auto_accept, 0), COALESCE(created_at, CURRENT_TIMESTAMP), avatar_key
                FROM users
                """
            )
        else:
            cur.execute(
                """
                INSERT INTO users_new (id, email, username, hashed_password, auto_accept, created_at, avatar_key)
                SELECT id, email, username, hashed_password, COALESCE(auto_accept, 0), COALESCE(created_at, CURRENT_TIMESTAMP), NULL
                FROM users
                """
            )

        cur.execute("DROP TABLE users")
        cur.execute("ALTER TABLE users_new RENAME TO users")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

        conn.commit()
        print("Cleaned users table successfully.")
    except Exception:
        conn.rollback()
        raise


def cleanup_room_members_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "room_members"):
        print("Table room_members does not exist, skipped.")
        return

    cols = get_columns(conn, "room_members")
    if "user_type" not in cols:
        print("room_members table already cleaned (user_type not found).")
        return

    print("Cleaning room_members table: removing user_type ...")
    cur = conn.cursor()
    cur.execute("BEGIN")

    try:
        cur.execute(
            """
            CREATE TABLE room_members_new (
                room_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                role VARCHAR(16) NOT NULL,
                PRIMARY KEY (room_id, user_id)
            )
            """
        )

        old_cols = set(cols)

        if "role" in old_cols:
            cur.execute(
                """
                INSERT INTO room_members_new (room_id, user_id, joined_at, role)
                SELECT room_id, user_id, COALESCE(joined_at, CURRENT_TIMESTAMP), LOWER(TRIM(role))
                FROM room_members
                """
            )
        else:
            cur.execute(
                """
                INSERT INTO room_members_new (room_id, user_id, joined_at, role)
                SELECT room_id, user_id, COALESCE(joined_at, CURRENT_TIMESTAMP), LOWER(TRIM(user_type))
                FROM room_members
                """
            )

        cur.execute("DROP TABLE room_members")
        cur.execute("ALTER TABLE room_members_new RENAME TO room_members")

        conn.commit()
        print("Cleaned room_members table successfully.")
    except Exception:
        conn.rollback()
        raise


def cleanup_rooms_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, "rooms"):
        print("Table rooms does not exist, skipped.")
        return

    cols = get_columns(conn, "rooms")
    if "is_active" not in cols:
        print("rooms table already cleaned (is_active not found).")
        return

    print("Cleaning rooms table: removing is_active ...")
    cur = conn.cursor()
    cur.execute("BEGIN")

    try:
        cur.execute(
            """
            CREATE TABLE rooms_new (
                id INTEGER PRIMARY KEY NOT NULL,
                name VARCHAR NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                owner_id INTEGER NOT NULL,
                is_public BOOLEAN NOT NULL DEFAULT 0,
                config VARCHAR
            )
            """
        )

        old_cols = set(cols)

        if "is_public" in old_cols and "config" in old_cols:
            cur.execute(
                """
                INSERT INTO rooms_new (id, name, created_at, owner_id, is_public, config)
                SELECT id, name, COALESCE(created_at, CURRENT_TIMESTAMP), owner_id, COALESCE(is_public, 0), config
                FROM rooms
                """
            )
        elif "is_public" in old_cols and "config" not in old_cols:
            cur.execute(
                """
                INSERT INTO rooms_new (id, name, created_at, owner_id, is_public, config)
                SELECT id, name, COALESCE(created_at, CURRENT_TIMESTAMP), owner_id, COALESCE(is_public, 0), NULL
                FROM rooms
                """
            )
        elif "is_public" not in old_cols and "config" in old_cols:
            cur.execute(
                """
                INSERT INTO rooms_new (id, name, created_at, owner_id, is_public, config)
                SELECT id, name, COALESCE(created_at, CURRENT_TIMESTAMP), owner_id, 0, config
                FROM rooms
                """
            )
        else:
            cur.execute(
                """
                INSERT INTO rooms_new (id, name, created_at, owner_id, is_public, config)
                SELECT id, name, COALESCE(created_at, CURRENT_TIMESTAMP), owner_id, 0, NULL
                FROM rooms
                """
            )

        cur.execute("DROP TABLE rooms")
        cur.execute("ALTER TABLE rooms_new RENAME TO rooms")

        conn.commit()
        print("Cleaned rooms table successfully.")
    except Exception:
        conn.rollback()
        raise


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        cleanup_users_table(conn)
        cleanup_room_members_table(conn)
        cleanup_rooms_table(conn)

        print("Legacy fields cleanup completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()