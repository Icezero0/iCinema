import sqlite3
from pathlib import Path


TABLE_NAME = "room_join_requests"

TRIGGER_NAME = "trg_room_join_requests_updated_at"


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    )
    return cur.fetchone() is not None


def index_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        (name,),
    )
    return cur.fetchone() is not None


def trigger_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name = ?",
        (name,),
    )
    return cur.fetchone() is not None


def create_table(conn: sqlite3.Connection):
    cur = conn.cursor()

    if table_exists(conn, TABLE_NAME):
        print(f"{TABLE_NAME} exists, dropping...")
        cur.execute(f"DROP TABLE {TABLE_NAME}")

    print(f"Creating {TABLE_NAME} ...")

    cur.execute(
        f"""
        CREATE TABLE {TABLE_NAME} (
            id INTEGER PRIMARY KEY NOT NULL,
            room_id INTEGER NOT NULL,
            initiator_user_id INTEGER NOT NULL,
            target_user_id INTEGER NOT NULL,

            source VARCHAR(16) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'pending',

            room_action VARCHAR(16) NOT NULL DEFAULT 'pending',
            target_action VARCHAR(16) NOT NULL DEFAULT 'pending',

            room_action_by_user_id INTEGER,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
            FOREIGN KEY (initiator_user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (target_user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (room_action_by_user_id) REFERENCES users (id) ON DELETE SET NULL
        )
        """
    )

    print("Table created.")


def create_indexes(conn: sqlite3.Connection):
    if not table_exists(conn, TABLE_NAME):
        return

    indexes = [
        ("ix_rjr_room_id", f"CREATE INDEX ix_rjr_room_id ON {TABLE_NAME} (room_id)"),
        (
            "ix_rjr_initiator",
            f"CREATE INDEX ix_rjr_initiator ON {TABLE_NAME} (initiator_user_id)",
        ),
        (
            "ix_rjr_target",
            f"CREATE INDEX ix_rjr_target ON {TABLE_NAME} (target_user_id)",
        ),
        ("ix_rjr_status", f"CREATE INDEX ix_rjr_status ON {TABLE_NAME} (status)"),
        ("ix_rjr_source", f"CREATE INDEX ix_rjr_source ON {TABLE_NAME} (source)"),
        (
            "ix_rjr_room_action",
            f"CREATE INDEX ix_rjr_room_action ON {TABLE_NAME} (room_action)",
        ),
        (
            "ix_rjr_target_action",
            f"CREATE INDEX ix_rjr_target_action ON {TABLE_NAME} (target_action)",
        ),
        (
            "uq_rjr_pending",
            f"""
            CREATE UNIQUE INDEX uq_rjr_pending
            ON {TABLE_NAME} (room_id, target_user_id)
            WHERE status = 'pending'
            """,
        ),
    ]

    for name, sql in indexes:
        if index_exists(conn, name):
            print(f"Index exists: {name}")
            continue
        print(f"Creating index: {name}")
        conn.execute(sql)


def create_trigger(conn: sqlite3.Connection):
    if not table_exists(conn, TABLE_NAME):
        return

    if trigger_exists(conn, TRIGGER_NAME):
        print(f"Trigger exists: {TRIGGER_NAME}")
        return

    print(f"Creating trigger: {TRIGGER_NAME}")

    conn.execute(
        f"""
        CREATE TRIGGER {TRIGGER_NAME}
        AFTER UPDATE ON {TABLE_NAME}
        FOR EACH ROW
        WHEN NEW.updated_at = OLD.updated_at
        BEGIN
            UPDATE {TABLE_NAME}
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = OLD.id;
        END
        """
    )


def main():
    db = (Path(__file__).resolve().parents[3] / "data" / "iCinema.db").resolve()
    print("DB:", db)

    conn = sqlite3.connect(str(db))
    try:
        conn.execute("PRAGMA foreign_keys=ON")

        create_table(conn)
        create_indexes(conn)
        create_trigger(conn)

        conn.commit()
        print("Migration done.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
