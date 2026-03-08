import sqlite3
from pathlib import Path


def ensure_column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Return True if column exists, else False."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cur.fetchall()]  # row[1] = column name
    return column in cols


def add_avatar_key_column(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("ALTER TABLE users ADD COLUMN avatar_key TEXT")
    conn.commit()


def extract_filename(avatar_path: str) -> str | None:
    # e.g. "/avatars/xxx.jpg" -> "xxx.jpg"
    p = (avatar_path or "").strip()
    if not p:
        return None
    # 兼容 Windows 反斜杠
    p = p.replace("\\", "/")
    fname = p.split("/")[-1].strip()
    return fname or None


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        # 1) Ensure column exists
        if ensure_column_exists(conn, "users", "avatar_key"):
            print("Column users.avatar_key already exists.")
        else:
            print("Adding column users.avatar_key ...")
            add_avatar_key_column(conn)
            print("Added column users.avatar_key.")

        # 2) Migrate data (only fill empty avatar_key)
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

    finally:
        conn.close()


if __name__ == "__main__":
    main()