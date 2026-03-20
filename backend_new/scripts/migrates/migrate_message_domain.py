import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def get_column_info(conn: sqlite3.Connection, table: str, column: str):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        if row[1] == column:
            return row
    return None


def message_table_needs_rebuild(conn: sqlite3.Connection) -> bool:
    created_at_info = get_column_info(conn, "messages", "created_at")
    return created_at_info is None or created_at_info[4] != "CURRENT_TIMESTAMP"


def rebuild_messages_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    print("Rebuilding messages ...")

    cur.execute("PRAGMA foreign_keys=OFF")
    cur.execute("BEGIN TRANSACTION")

    try:
        cur.execute(
            """
            CREATE TABLE messages_new (
                id INTEGER PRIMARY KEY NOT NULL,
                content VARCHAR NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INTEGER,
                room_id INTEGER NOT NULL
            )
            """
        )

        cur.execute(
            """
            INSERT INTO messages_new (id, content, created_at, user_id, room_id)
            SELECT id, content, COALESCE(created_at, CURRENT_TIMESTAMP), user_id, room_id
            FROM messages
            """
        )

        cur.execute("DROP TABLE messages")
        cur.execute("ALTER TABLE messages_new RENAME TO messages")

        conn.commit()
        print("messages rebuilt successfully.")
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
        if not table_exists(conn, "messages"):
            print("Table messages does not exist, skip migration.")
            return

        if message_table_needs_rebuild(conn):
            rebuild_messages_table(conn)
        else:
            print("messages already matches target schema, skip rebuilding.")

        print("Message domain migration completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()