"""
auth.py — parent accounts, gated with a signed httpOnly session cookie.

Prototype-grade, on purpose: this earns its name "gated" (nothing reaches the
app or the scorer without a session) but is not hardened for real deployment.
No email verification, no password reset, no rate-limit persistence across
restarts, no CSRF token (SameSite=Lax cookies cover the common case, not all of
it). See server/README.md before this goes near real users.
"""

import os
import re
import time

import bcrypt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field

import db

router = APIRouter()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# --------------------------------------------------------------------------
# brute-force slowdown — in-memory, resets on restart. A real deployment needs
# this backed by something that survives a restart and is shared across workers.
# --------------------------------------------------------------------------
_attempts = {}                 # email -> [timestamps of recent failures]
MAX_ATTEMPTS = 8
WINDOW_S = 15 * 60


def _too_many_attempts(email):
    now = time.time()
    hist = [t for t in _attempts.get(email, []) if now - t < WINDOW_S]
    _attempts[email] = hist
    return len(hist) >= MAX_ATTEMPTS


def _record_failure(email):
    _attempts.setdefault(email, []).append(time.time())


def _clear_failures(email):
    _attempts.pop(email, None)


# --------------------------------------------------------------------------
# password hashing
# --------------------------------------------------------------------------

def hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain, hashed):
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# --------------------------------------------------------------------------
# request/response models
# --------------------------------------------------------------------------

class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    consent_service: bool
    consent_training: bool = False


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class ChildBody(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    age_years: int | None = Field(default=None, ge=1, le=18)


def current_parent(request: Request):
    """Raises 401 if there is no valid session. Import and depend on this
    wherever a route needs a signed-in parent."""
    pid = request.session.get("parent_id")
    if not pid:
        raise HTTPException(status_code=401, detail="Sign in required.")
    parent = db.get_parent(pid)
    if not parent:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Sign in required.")
    return parent


def require_child(request: Request, child_id: int):
    """A parent may only touch their own children's data."""
    parent = current_parent(request)
    if not db.child_belongs_to(child_id, parent["id"]):
        raise HTTPException(status_code=404, detail="No such child.")
    return parent


# --------------------------------------------------------------------------
# routes
# --------------------------------------------------------------------------

@router.post("/auth/signup")
def signup(body: SignupBody, request: Request):
    if not body.consent_service:
        raise HTTPException(
            status_code=400,
            detail="Service-data consent is required before any session data can be collected.",
        )
    if db.get_parent_by_email(body.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    parent_id = db.create_parent(
        body.email, hash_password(body.password), body.consent_training
    )
    request.session["parent_id"] = parent_id
    return {"ok": True, "email": body.email.lower()}


@router.post("/auth/login")
def login(body: LoginBody, request: Request):
    email = body.email.lower()
    if _too_many_attempts(email):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")

    parent = db.get_parent_by_email(email)
    if not parent or not verify_password(body.password, parent["password_hash"]):
        _record_failure(email)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    _clear_failures(email)
    request.session["parent_id"] = parent["id"]
    return {"ok": True, "email": parent["email"]}


@router.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request):
    pid = request.session.get("parent_id")
    if not pid:
        return {"signed_in": False}
    parent = db.get_parent(pid)
    if not parent:
        request.session.clear()
        return {"signed_in": False}
    return {
        "signed_in": True,
        "email": parent["email"],
        "consent_training": bool(parent["consent_training"]),
        "children": db.list_children(parent["id"]),
    }


@router.get("/children")
def get_children(request: Request):
    parent = current_parent(request)
    return db.list_children(parent["id"])


@router.post("/children")
def add_child(body: ChildBody, request: Request):
    parent = current_parent(request)
    child_id = db.create_child(parent["id"], body.name, body.age_years)
    return db.get_child(child_id)


@router.get("/progress/{child_id}")
def get_progress(child_id: int, request: Request):
    require_child(request, child_id)
    p = db.get_progress(child_id)
    if p is None:
        raise HTTPException(status_code=404, detail="No progress record.")
    return p


class ProgressBody(BaseModel):
    stars: int = 0
    xp: int = 0
    levels: dict = Field(default_factory=dict)
    badges: list = Field(default_factory=list)
    reward: dict = Field(default_factory=dict)
    last_done: str | None = None


@router.put("/progress/{child_id}")
def put_progress(child_id: int, body: ProgressBody, request: Request):
    require_child(request, child_id)
    db.put_progress(child_id, body.stars, body.xp, body.levels, body.badges,
                    body.reward, body.last_done)
    return {"ok": True}


@router.post("/sessions/{child_id}")
def post_session(child_id: int, request: Request, payload: dict):
    require_child(request, child_id)
    db.add_practice_session(child_id, payload)
    return {"ok": True}


@router.get("/sessions/{child_id}")
def get_sessions(child_id: int, request: Request):
    require_child(request, child_id)
    return db.list_practice_sessions(child_id)


def secret_key():
    """Stable across restarts (so sessions survive a redeploy) without ever
    committing a secret. Prefer an explicit env var in anything beyond a
    prototype."""
    env = os.environ.get("MIRA_SECRET_KEY")
    if env:
        return env
    path = os.path.join(os.path.dirname(__file__), ".secret")
    if os.path.exists(path):
        return open(path, encoding="utf-8").read().strip()
    key = os.urandom(32).hex()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(key)
    os.chmod(path, 0o600)
    return key
