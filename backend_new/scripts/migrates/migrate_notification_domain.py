import sqlite3
from pathlib import Path


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def drop_notifications_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS notifications")
    conn.commit()


def create_notifications_table(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_user_id INTEGER NOT NULL,
            actor_user_id INTEGER NULL,
            notification_type VARCHAR(32) NOT NULL,
            related_type VARCHAR(64) NULL,
            related_id INTEGER NULL,
            is_read BOOLEAN NOT NULL DEFAULT 0,
            read_at DATETIME NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(recipient_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(actor_user_id) REFERENCES users(id) ON DELETE SET NULL
        )
        """
    )

    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_recipient_user_id
        ON notifications (recipient_user_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_actor_user_id
        ON notifications (actor_user_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_notification_type
        ON notifications (notification_type)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_related_type
        ON notifications (related_type)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_related_id
        ON notifications (related_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_is_read
        ON notifications (is_read)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_created_at
        ON notifications (created_at)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_related_type_related_id
        ON notifications (related_type, related_id)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_recipient_user_id_created_at
        ON notifications (recipient_user_id, created_at)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notifications_recipient_user_id_is_read_created_at
        ON notifications (recipient_user_id, is_read, created_at)
        """
    )

    conn.commit()


def main() -> None:
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA foreign_keys = ON")

        print("Rebuilding notifications table...")

        if table_exists(conn, "notifications"):
            print("Table notifications exists, dropping old table...")
            drop_notifications_table(conn)
            print("Dropped old notifications table.")
        else:
            print("Table notifications does not exist, skip drop.")

        print("Creating new notifications table...")
        create_notifications_table(conn)
        print("Created new notifications table.")

    finally:
        conn.close()


if __name__ == "__main__":
    main()