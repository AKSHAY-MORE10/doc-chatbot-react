"""Parent-document store for parent-document retrieval.

Child chunks (small, precise) are embedded and indexed in Chroma as before.
Their full parent section text is stored here, keyed by parent_id, so the
retriever can look up "the whole section a matching chunk came from" without
re-splitting or re-embedding anything. Plain SQLite (stdlib) is enough since
lookups are always by exact id, never by similarity — no need for another
vector store.
"""

import logging
import sqlite3
import threading
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None
_conn_lock = threading.Lock()


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        with _conn_lock:
            if _conn is None:
                db_path = Path(settings.CHROMA_PATH) / "parents.sqlite3"
                db_path.parent.mkdir(parents=True, exist_ok=True)
                _conn = sqlite3.connect(str(db_path), check_same_thread=False)
                _conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS parents (
                        collection TEXT NOT NULL,
                        parent_id TEXT NOT NULL,
                        text TEXT NOT NULL,
                        PRIMARY KEY (collection, parent_id)
                    )
                    """
                )
                _conn.commit()
                logger.info("Parent store initialised at %s", db_path)
    return _conn


def save_parents(collection: str, parents: dict[str, str]) -> None:
    """Upsert ``{parent_id: text}`` for *collection*."""
    if not parents:
        return
    conn = _get_conn()
    with _conn_lock:
        conn.executemany(
            "INSERT OR REPLACE INTO parents (collection, parent_id, text) VALUES (?, ?, ?)",
            [(collection, pid, text) for pid, text in parents.items()],
        )
        conn.commit()


def get_parents(collection: str, parent_ids: list[str]) -> dict[str, str]:
    """Fetch parent text for the given ids. Missing ids are simply omitted."""
    if not parent_ids:
        return {}
    conn = _get_conn()
    placeholders = ",".join("?" for _ in parent_ids)
    rows = conn.execute(
        f"SELECT parent_id, text FROM parents WHERE collection = ? AND parent_id IN ({placeholders})",
        (collection, *parent_ids),
    ).fetchall()
    return dict(rows)


def delete_collection(collection: str) -> None:
    """Remove all parent records for *collection* (called when a collection is deleted)."""
    conn = _get_conn()
    with _conn_lock:
        conn.execute("DELETE FROM parents WHERE collection = ?", (collection,))
        conn.commit()
