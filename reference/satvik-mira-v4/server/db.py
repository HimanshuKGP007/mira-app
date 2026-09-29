"""
db.py — SQLite storage for accounts, child profiles and progress.

Prototype-grade, deliberately: stdlib sqlite3, one file, no migrations framework.
Good enough to make progress survive a wiped browser and to demonstrate a real
consent-and-account flow. Not a production auth system — see server/README.md
"Accounts — what this is and isn't" before this goes anywhere near real users.
"""

import json
import os
import sqlite3
import threading
import time

DB_PATH = os.environ.get("MIRA_DB_PATH", os.path.join(os.path.dirname(__file__), "mira.db"))

_local = threading.local()


def _conn():
    c = getattr(_local, "conn", None)
    if c is None:
        c = sqlite3.connect(DB_PATH, check_same_thread=False)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys = ON")
        _local.conn = c
    return c


SCHEMA = """
CREATE TABLE IF NOT EXISTS parents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at REAL NOT NULL,
    consent_service_at REAL NOT NULL,
    consent_training INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS children (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL REFERENCES parents(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    age_years INTEGER,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS progress (
    child_id INTEGER PRIMARY KEY REFERENCES children(id) ON DELETE CASCADE,
    stars INTEGER NOT NULL DEFAULT 0,
    xp INTEGER NOT NULL DEFAULT 0,
    levels_json TEXT NOT NULL DEFAULT '{}',
    badges_json TEXT NOT NULL DEFAULT '[]',
    reward_json TEXT NOT NULL DEFAULT '{}',
    last_done TEXT,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS practice_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    child_id INTEGER NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    at REAL NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_child ON practice_sessions(child_id);
CREATE INDEX IF NOT EXISTS idx_children_parent ON children(parent_id);
"""


def init():
    _conn().executescript(SCHEMA)
    _conn().commit()


# --------------------------------------------------------------------------
# parents
# --------------------------------------------------------------------------

def create_parent(email, password_hash, consent_training):
    now = time.time()
    cur = _conn().execute(
        "INSERT INTO parents (email, password_hash, created_at, consent_service_at, consent_training) "
        "VALUES (?, ?, ?, ?, ?)",
        (email.strip().lower(), password_hash, now, now, int(bool(consent_training))),
    )
    _conn().commit()
    return cur.lastrowid


def get_parent_by_email(email):
    row = _conn().execute(
        "SELECT * FROM parents WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    return dict(row) if row else None


def get_parent(parent_id):
    row = _conn().execute("SELECT * FROM parents WHERE id = ?", (parent_id,)).fetchone()
    return dict(row) if row else None


# --------------------------------------------------------------------------
# children
# --------------------------------------------------------------------------

def create_child(parent_id, name, age_years):
    now = time.time()
    cur = _conn().execute(
        "INSERT INTO children (parent_id, name, age_years, created_at) VALUES (?, ?, ?, ?)",
        (parent_id, name.strip()[:40], age_years, now),
    )
    child_id = cur.lastrowid
    _conn().execute(
        "INSERT INTO progress (child_id, updated_at) VALUES (?, ?)", (child_id, now)
    )
    _conn().commit()
    return child_id


def list_children(parent_id):
    rows = _conn().execute(
        "SELECT * FROM children WHERE parent_id = ? ORDER BY created_at", (parent_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_child(child_id):
    row = _conn().execute("SELECT * FROM children WHERE id = ?", (child_id,)).fetchone()
    return dict(row) if row else None


def child_belongs_to(child_id, parent_id):
    c = get_child(child_id)
    return bool(c) and c["parent_id"] == parent_id


# --------------------------------------------------------------------------
# progress
# --------------------------------------------------------------------------

def get_progress(child_id):
    row = _conn().execute("SELECT * FROM progress WHERE child_id = ?", (child_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["levels"] = json.loads(d.pop("levels_json") or "{}")
    d["badges"] = json.loads(d.pop("badges_json") or "[]")
    d["reward"] = json.loads(d.pop("reward_json") or "{}")
    return d


def put_progress(child_id, stars, xp, levels, badges, reward, last_done):
    _conn().execute(
        "INSERT INTO progress (child_id, stars, xp, levels_json, badges_json, reward_json, last_done, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(child_id) DO UPDATE SET "
        "stars=excluded.stars, xp=excluded.xp, levels_json=excluded.levels_json, "
        "badges_json=excluded.badges_json, reward_json=excluded.reward_json, "
        "last_done=excluded.last_done, updated_at=excluded.updated_at",
        (child_id, stars, xp, json.dumps(levels), json.dumps(badges), json.dumps(reward),
         last_done, time.time()),
    )
    _conn().commit()


# --------------------------------------------------------------------------
# sessions (the honest per-trail records, distinct from the login session)
# --------------------------------------------------------------------------

def add_practice_session(child_id, payload):
    _conn().execute(
        "INSERT INTO practice_sessions (child_id, at, payload_json) VALUES (?, ?, ?)",
        (child_id, time.time(), json.dumps(payload)),
    )
    _conn().commit()


def list_practice_sessions(child_id, limit=30):
    rows = _conn().execute(
        "SELECT payload_json FROM practice_sessions WHERE child_id = ? ORDER BY at DESC LIMIT ?",
        (child_id, limit),
    ).fetchall()
    return [json.loads(r["payload_json"]) for r in rows][::-1]
