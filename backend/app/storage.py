"""Puzzle persistence: one JSON file per puzzle + SQLite index + global ban list."""
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

DATA_DIR = os.environ.get("DATA_DIR", "/data/puzzles")
DB_PATH = os.environ.get("DB_PATH", os.path.join(DATA_DIR, "index.db"))

_lock = threading.Lock()


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init():
    os.makedirs(DATA_DIR, exist_ok=True)
    with _lock, _conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS puzzles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cols INTEGER NOT NULL,
            rows INTEGER NOT NULL,
            word_count INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        conn.execute("CREATE TABLE IF NOT EXISTS ban_list (word TEXT PRIMARY KEY)")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _puzzle_path(puzzle_id: str) -> str:
    # puzzle ids are UUIDs we generate; guard against path tricks anyway
    safe = "".join(ch for ch in puzzle_id if ch.isalnum() or ch == "-")
    return os.path.join(DATA_DIR, f"{safe}.json")


def list_puzzles() -> list[dict]:
    with _lock, _conn() as conn:
        rows = conn.execute("SELECT * FROM puzzles ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def load_puzzle(puzzle_id: str) -> dict | None:
    path = _puzzle_path(puzzle_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_puzzle(puzzle: dict):
    puzzle["appMeta"]["updatedAt"] = now_iso()
    path = _puzzle_path(puzzle["id"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(puzzle, f, indent=2)
    os.replace(tmp, path)
    with _lock, _conn() as conn:
        conn.execute("""INSERT INTO puzzles (id, name, cols, rows, word_count, status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET name=excluded.name, cols=excluded.cols, rows=excluded.rows,
              word_count=excluded.word_count, status=excluded.status, updated_at=excluded.updated_at""",
            (puzzle["id"], puzzle["name"], puzzle["dimensions"]["cols"], puzzle["dimensions"]["rows"],
             len(puzzle["entries"]), puzzle["appMeta"]["status"],
             puzzle["appMeta"]["createdAt"], puzzle["appMeta"]["updatedAt"]))


def delete_puzzle(puzzle_id: str) -> bool:
    path = _puzzle_path(puzzle_id)
    existed = os.path.exists(path)
    if existed:
        os.remove(path)
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM puzzles WHERE id = ?", (puzzle_id,))
    return existed


def get_ban_list() -> list[str]:
    with _lock, _conn() as conn:
        rows = conn.execute("SELECT word FROM ban_list ORDER BY word").fetchall()
    return [r["word"] for r in rows]


def add_banned_word(word: str):
    with _lock, _conn() as conn:
        conn.execute("INSERT OR IGNORE INTO ban_list (word) VALUES (?)", (word,))


def remove_banned_word(word: str) -> bool:
    with _lock, _conn() as conn:
        cur = conn.execute("DELETE FROM ban_list WHERE word = ?", (word,))
    return cur.rowcount > 0
