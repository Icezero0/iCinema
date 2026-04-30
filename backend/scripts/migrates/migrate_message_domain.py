import json
import sqlite3
from pathlib import Path


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


def normalize_legacy_text(text: str | None) -> str:
    if text is None:
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def build_json_content_from_legacy_text(text: str | None) -> str:
    normalized = normalize_legacy_text(text)
    payload = {
        "segments": [
            {
                "type": "text",
                "text": normalized,
            }
        ]
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def create_messages_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    if table_exists(conn, "messages"):
        print("Table messages already exists, skip creating.")
        return

    print("Creating table messages ...")
    cur.execute(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY NOT NULL,
            content TEXT NOT NULL,
            sender_user_id INTEGER,
            room_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def messages_table_needs_rebuild(conn: sqlite3.Connection) -> bool:
    if not table_exists(conn, "messages"):
        return False

    id_info = get_column_info(conn, "messages", "id")
    content_info = get_column_info(conn, "messages", "content")
    created_at_info = get_column_info(conn, "messages", "created_at")
    updated_at_info = get_column_info(conn, "messages", "updated_at")
    sender_user_id_info = get_column_info(conn, "messages", "sender_user_id")
    room_id_info = get_column_info(conn, "messages", "room_id")

    if id_info is None:
        return True
    if content_info is None:
        return True
    if created_at_info is None or (created_at_info[4] or "").upper() != "CURRENT_TIMESTAMP":
        return True
    if updated_at_info is None or (updated_at_info[4] or "").upper() != "CURRENT_TIMESTAMP":
        return True
    if sender_user_id_info is None:
        return True
    if room_id_info is None:
        return True

    return False


def rebuild_messages_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    print("Rebuilding messages ...")

    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("BEGIN TRANSACTION")

    try:
        cur.execute(
            """
            CREATE TABLE messages_new (
                id INTEGER PRIMARY KEY NOT NULL,
                content TEXT NOT NULL,
                sender_user_id INTEGER,
                room_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute(
            """
            SELECT id, content, created_at, user_id, room_id
            FROM messages
            ORDER BY id
            """
        )
        rows = cur.fetchall()

        insert_sql = """
            INSERT INTO messages_new (
                id,
                content,
                sender_user_id,
                room_id,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """

        for row in rows:
            message_id, legacy_content, created_at, user_id, room_id = row

            new_content = build_json_content_from_legacy_text(legacy_content)

            safe_created_at = created_at
            if safe_created_at is None:
                cur.execute("SELECT CURRENT_TIMESTAMP")
                safe_created_at = cur.fetchone()[0]

            cur.execute(
                insert_sql,
                (
                    message_id,
                    new_content,
                    user_id,
                    room_id,
                    safe_created_at,
                    safe_created_at,
                ),
            )

        cur.execute("DROP TABLE messages")
        cur.execute("ALTER TABLE messages_new RENAME TO messages")

        conn.commit()
        print("messages rebuilt successfully.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys=ON")


def ensure_messages_indexes_and_triggers(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    if not index_exists(conn, "idx_messages_room_id_id"):
        print("Creating index idx_messages_room_id_id ...")
        cur.execute(
            """
            CREATE INDEX idx_messages_room_id_id
            ON messages (room_id, id)
            """
        )

    if not index_exists(conn, "idx_messages_sender_user_id"):
        print("Creating index idx_messages_sender_user_id ...")
        cur.execute(
            """
            CREATE INDEX idx_messages_sender_user_id
            ON messages (sender_user_id)
            """
        )

    if not trigger_exists(conn, "trg_messages_updated_at"):
        print("Creating trigger trg_messages_updated_at ...")
        cur.execute(
            """
            CREATE TRIGGER trg_messages_updated_at
            AFTER UPDATE ON messages
            FOR EACH ROW
            BEGIN
                UPDATE messages
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = OLD.id;
            END;
            """
        )

    conn.commit()


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        if not table_exists(conn, "messages"):
            create_messages_table(conn)
            ensure_messages_indexes_and_triggers(conn)
            print("Message domain migration completed.")
            return

        if messages_table_needs_rebuild(conn):
            rebuild_messages_table(conn)

        ensure_messages_indexes_and_triggers(conn)
        print("Message domain migration completed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()