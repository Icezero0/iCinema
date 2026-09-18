import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


def test_catalog_upgrade_preserves_existing_schema_and_can_downgrade(tmp_path):
    database = tmp_path / "migration.db"
    env = {**os.environ, "ALEMBIC_DATABASE_URL": f"sqlite:///{database.as_posix()}"}
    root = Path(__file__).resolve().parents[2]

    def migrate(*args):
        result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=root,
                                env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stderr

    migrate("upgrade", "b19f06a8c321")
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO users (email, username, hashed_password, auto_accept) VALUES (?, ?, ?, 0)",
                   ("migration@example.invalid", "migration-test", "not-a-real-password"))
    migrate("upgrade", "c27a9d40e612")
    with sqlite3.connect(database) as db:
        db.execute("""INSERT INTO catalog_contents
            (title, aliases, category, region, content_type, description, status, disabled, disabled_reason, version)
            VALUES ('Existing content', '', 'japanese_animation', 'JP', 'tv', '', 'draft', 0, '', 1)""")
    migrate("upgrade", "e49c1f620834")
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT code FROM catalog_categories").fetchall() == [("japanese_animation",)]
        assert db.execute("SELECT username FROM users").fetchone() == ("migration-test",)
        assert db.execute("SELECT title, category, region FROM catalog_contents").fetchone() == ("Existing content", "japanese_animation", "JP")
        assert db.execute("SELECT COUNT(*) FROM catalog_audits").fetchone() == (0,)
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("""INSERT INTO catalog_episodes
            (id, content_id, title, season, kind, number, sort_order, disabled, disabled_reason)
            VALUES (1, 1, 'First episode', 1, 'episode', 1, 0, 0, '')""")
        db.execute("""INSERT INTO catalog_lines
            (id, content_id, name, source_key, line_key, sort_order, disabled, disabled_reason)
            VALUES (1, 1, 'Manual line', 'manual', 'one', 0, 0, '')""")
        db.execute("""INSERT INTO catalog_playbacks
            (id, content_id, episode_id, line_id, url, media_type, source_label, disabled, disabled_reason)
            VALUES (1, 1, 1, 1, 'https://example.invalid/test.mp4', 'direct', '', 0, '')""")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE catalog_playbacks SET content_id=999 WHERE id=1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("""INSERT INTO catalog_playbacks
                (content_id, episode_id, line_id, url, media_type, source_label, disabled, disabled_reason)
                VALUES (1, 1, 1, 'https://example.invalid/other.mp4', 'direct', '', 0, '')""")
    with sqlite3.connect(database) as db:
        db.execute("""INSERT INTO catalog_episodes
            (id, content_id, title, season, kind, number, sort_order, disabled, disabled_reason)
            VALUES (2, 1, 'Conflicting old season', 2, 'episode', 1, 1, 0, '')""")
    failed = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=root,
                            env=env, capture_output=True, text=True, timeout=60)
    assert failed.returncode != 0 and "duplicate episode numbers across seasons" in failed.stderr
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT version_num FROM alembic_version").fetchone() == ("e49c1f620834",)
        assert db.execute("SELECT id, season FROM catalog_episodes ORDER BY id").fetchall() == [(1, 1), (2, 2)]
        assert db.execute("SELECT COUNT(*) FROM catalog_playbacks").fetchone() == (1,)
        db.execute("DELETE FROM catalog_episodes WHERE id=2")
    migrate("upgrade", "head")
    with sqlite3.connect(database) as db:
        assert "season" not in {row[1] for row in db.execute("PRAGMA table_info(catalog_episodes)")}
        assert db.execute("SELECT id, content_id, title, number FROM catalog_episodes").fetchone() == (1, 1, "First episode", 1)
        assert db.execute("SELECT id, episode_id, line_id, url FROM catalog_playbacks").fetchone() == (1, 1, 1, "https://example.invalid/test.mp4")
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT code, upstream_category, category FROM catalog_providers").fetchone() == ("jinying", 25, "japanese_animation")
        assert db.execute("SELECT play_from FROM catalog_providers").fetchone() == ("jinyingm3u8",)
        db.execute("INSERT INTO catalog_sources (provider_id, upstream_id, content_id, snapshot) VALUES (1, 123, 1, '{}')")
    migrate("check")
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO catalog_episodes (id, content_id, title, kind, number, sort_order, disabled, disabled_reason) VALUES (3, 1, 'Recap', 'episode', 1.51, 1.51, 0, '')")
        db.execute("INSERT INTO catalog_playbacks (id, content_id, episode_id, line_id, url, media_type, source_label, disabled, disabled_reason) VALUES (3, 1, 3, 1, 'https://example.invalid/recap.m3u8', 'hls', '', 0, '')")
    rejected = subprocess.run([sys.executable, "-m", "alembic", "downgrade", "c83a5da64278"], cwd=root,
                              env=env, capture_output=True, text=True, timeout=60)
    assert rejected.returncode != 0 and "Fractional episodes exist" in rejected.stderr
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT number, sort_order FROM catalog_episodes WHERE id=3").fetchone() == (1.51, 1.51)
        assert db.execute("SELECT COUNT(*) FROM catalog_playbacks").fetchone() == (2,)
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        db.execute("DELETE FROM catalog_playbacks WHERE id=3")
        db.execute("DELETE FROM catalog_episodes WHERE id=3")
    migrate("downgrade", "f50d2a731945")
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM catalog_playbacks").fetchone() == (1,)
        assert db.execute("SELECT title FROM catalog_contents").fetchone() == ("Existing content",)
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='catalog_sources'").fetchall()
    migrate("upgrade", "head")
    # Reverting just stage 2 must keep all stage 1 resources and audit history.
    migrate("downgrade", "d38b0e51f723")
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT title FROM catalog_contents").fetchone() == ("Existing content",)
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='catalog_playbacks'").fetchall()
    migrate("upgrade", "head")
    migrate("check")
    migrate("downgrade", "b19f06a8c321")
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT username FROM users").fetchone() == ("migration-test",)
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='catalog_contents'").fetchall()
    migrate("upgrade", "head")
