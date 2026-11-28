"""Database engine, sessions and the FTS5 keyword index."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

FTS_DDL = (
    "CREATE VIRTUAL TABLE IF NOT EXISTS search_fts USING fts5("
    "content, kind UNINDEXED, ref_id UNINDEXED, video_id UNINDEXED, series_id UNINDEXED, "
    "tokenize = 'unicode61 remove_diacritics 2')"
)


class Database:
    def __init__(self, url: str):
        connect_args = {"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, connect_args=connect_args)
        if url.startswith("sqlite"):
            event.listen(self.engine, "connect", _sqlite_pragmas)
        self._factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_all(self) -> None:
        Base.metadata.create_all(self.engine)
        with self.engine.begin() as conn:
            conn.execute(text(FTS_DDL))
            if self.engine.dialect.name == "sqlite":
                _add_missing_columns(conn)

    @contextmanager
    def session(self) -> Iterator[Session]:
        """One transaction: commit on success, roll back on any error."""
        s = self._factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()


# Columns added after the first release. create_all() does not alter existing tables, so databases
# made by an older version get them here (SQLite ADD COLUMN keeps all existing rows).
ADDED_COLUMNS = {
    "videos": [
        ("source_type", "VARCHAR(16) NOT NULL DEFAULT 'youtube'"),
        ("media_path", "TEXT"),
        ("source_url", "TEXT"),
    ],
}


def _add_missing_columns(conn) -> None:
    for table, cols in ADDED_COLUMNS.items():
        have = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
        for name, ddl in cols:
            if name not in have:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def _sqlite_pragmas(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=30000")
    cur.close()
