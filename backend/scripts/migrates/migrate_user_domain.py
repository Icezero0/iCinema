import sqlite3
from pathlib import Path


def ensure_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True if column exists, else False."""
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


def add_avatar_key_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("ALTER TABLE users ADD COLUMN avatar_key TEXT")
    conn.commit()


def extract_filename(avatar_path: str) -> str | None:
    p = (avatar_path or "").strip()
    if not p:
        return None
    p = p.replace("\\", "/")
    fname = p.split("/")[-1].strip()
    return fname or None


def get_indexes(conn: sqlite3.Connection, table: str) -> list[tuple]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA index_list({table})")
    return cur.fetchall()


def get_index_columns(conn: sqlite3.Connection, index_name: str) -> list[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA index_info({index_name})")
    rows = cur.fetchall()
    return [row[2] for row in rows]


def username_has_unique_constraint(conn: sqlite3.Connection) -> bool:
    indexes = get_indexes(conn, "users")
    for row in indexes:
        index_name = row[1]
        is_unique = row[2]
        if not is_unique:
            continue

        cols = get_index_columns(conn, index_name)
        if cols == ["username"]:
            return True
    return False


def created_at_missing_default(conn: sqlite3.Connection) -> bool:
    info = get_column_info(conn, "users", "created_at")
    if info is None:
        return True
    default = info[4]
    return default != "CURRENT_TIMESTAMP"


def rebuild_users_table(conn: sqlite3.Connection) -> None:
    """
    Rebuild users table to:
    - remove UNIQUE constraint from username
    - ensure created_at defaults to CURRENT_TIMESTAMP
    - keep email unique
    - keep avatar_key column
    - preserve existing data
    """
    cur = conn.cursor()

    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("BEGIN TRANSACTION")

    try:
        cur.execute(
            """
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                username VARCHAR(64),
                hashed_password VARCHAR(255) NOT NULL,
                avatar_path VARCHAR(255),
                avatar_key VARCHAR(255),
                auto_accept BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            INSERT INTO users_new (
                id,
                email,
                username,
                hashed_password,
                avatar_path,
                avatar_key,
                auto_accept,
                created_at
            )
            SELECT
                id,
                email,
                username,
                hashed_password,
                avatar_path,
                avatar_key,
                COALESCE(auto_accept, 0),
                COALESCE(created_at, CURRENT_TIMESTAMP)
            FROM users
            """
        )

        cur.execute("DROP TABLE users")
        cur.execute("ALTER TABLE users_new RENAME TO users")

        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email)")
        cur.execute("CREATE INDEX IF NOT EXISTS ix_users_id ON users (id)")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.execute("PRAGMA foreign_keys=ON")


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        if ensure_column_exists(conn, "users", "avatar_key"):
            print("Column users.avatar_key already exists.")
        else:
            print("Adding column users.avatar_key ...")
            add_avatar_key_column(conn)
            print("Added column users.avatar_key.")

        cur = conn.cursor()
        cur.execute("SELECT id, avatar_path, avatar_key FROM users")
        rows = cur.fetchall()

        updated = 0
        skipped_has_key = 0
        skipped_no_path = 0
        skipped_bad_path = 0

        for uid, avatar_path, avatar_key in rows:
            if avatar_key and str(avatar_key).strip():
                skipped_has_key += 1
                continue

            if not avatar_path or not str(avatar_path).strip():
                skipped_no_path += 1
                continue

            fname = extract_filename(str(avatar_path))
            if not fname:
                skipped_bad_path += 1
                continue

            cur.execute(
                "UPDATE users SET avatar_key = ? WHERE id = ?",
                (fname, uid),
            )
            updated += 1

        conn.commit()

        print("migrated rows:", updated)
        print("skipped (already has avatar_key):", skipped_has_key)
        print("skipped (no avatar_path):", skipped_no_path)
        print("skipped (bad avatar_path):", skipped_bad_path)

        needs_rebuild = username_has_unique_constraint(conn) or created_at_missing_default(conn)
        if needs_rebuild:
            print("Rebuilding users table to normalize constraints/defaults ...")
            rebuild_users_table(conn)
            print("Rebuilt users table successfully.")
        else:
            print("users table constraints/defaults already match target, skip rebuilding.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()