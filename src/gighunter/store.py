import sqlite3
from pathlib import Path

from gighunter.models import Gig

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_gigs (
    key        TEXT PRIMARY KEY,
    source     TEXT NOT NULL,
    title      TEXT NOT NULL,
    url        TEXT NOT NULL,
    first_seen TEXT NOT NULL
)
"""


class SeenStore:
    """Dedupe table: a gig is notified at most once."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def filter_new(self, gigs: list[Gig]) -> list[Gig]:
        return [g for g in gigs if not self._is_seen(g.key)]

    def mark_seen(self, gig: Gig) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO seen_gigs VALUES (?, ?, ?, ?, ?)",
            (gig.key, gig.source.value, gig.title, str(gig.url),
             gig.fetched_at.isoformat()),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def _is_seen(self, key: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_gigs WHERE key = ?", (key,)
        ).fetchone()
        return row is not None
