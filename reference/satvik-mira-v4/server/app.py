"""
app.py — the Mira scoring service, gated behind real (prototype-grade) accounts.

  GET  /                     landing page — public
  POST /auth/signup|login|logout, GET /auth/me     — see auth.py
  GET|POST /children, GET|PUT /progress/{id}, GET|POST /sessions/{id}  — see auth.py
  POST /score                 requires a signed-in parent
  GET  /health                device, model, tier, stated limits — public
  GET  /app                   the Mira app — requires a session, else redirects to "/"

Run:  ./run.sh        (or: uvicorn app:app --host 127.0.0.1 --port 8000)
"""

import contextlib
import os
import pathlib
import time

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import auth
import db
import insights
import policy
import scorer

try:
    from dotenv import load_dotenv
    load_dotenv(pathlib.Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

ROOT = pathlib.Path(__file__).resolve().parent.parent


@contextlib.asynccontextmanager
async def lifespan(app):
    db.init()
    t0 = time.time()
    print("[mira] loading %s ..." % policy.MODEL_ID)
    st = scorer.load()
    print("[mira] ready on %s in %.1fs (tier=%s)"
          % (st["device"], time.time() - t0, policy.SCORER_TIER))
    yield


app = FastAPI(title="Mira scorer", version="0.2.0", lifespan=lifespan)

# Same-origin is the normal case (the frontend is mounted below), but allow the
# common "app on one dev port, opened via a different port" case too. Wildcard
# origins cannot carry credentials per the CORS spec, so this uses a narrow
# regex instead of "*" — cookie auth needs allow_credentials=True.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"],
)

# Signed, httpOnly session cookie (Starlette sets httponly unconditionally).
# MIRA_COOKIE_SECURE=1 in any deployment behind TLS.
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.secret_key(),
    session_cookie="mira_session",
    same_site="lax",
    https_only=os.environ.get("MIRA_COOKIE_SECURE", "0") == "1",
    max_age=60 * 60 * 24 * 30,                      # 30 days
)

app.include_router(auth.router)


@app.middleware("http")
async def no_cache(request: Request, call_next):
    """Every response is revalidate-before-use.

    Found by testing, not by inspection: without this, a plain browser fetch()
    or dynamic import() of an app JS module could silently be served from the
    browser's ordinary HTTP cache with no revalidation at all — Starlette's
    StaticFiles sets Last-Modified/ETag but no Cache-Control, so there was
    nothing forcing a check back with the server. A code fix could then sit
    unreachable in a running browser tab indefinitely. This app is also
    session-gated, so API responses are user-specific and should not be cached
    ambiently either. `no-cache` still allows a fast conditional (304) request,
    it just stops the browser from skipping the network round trip outright.
    """
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-cache")
    return response


@app.get("/health")
def health():
    st = scorer.state()
    return {
        "ok": bool(st.get("loaded")),
        "model": st.get("model_id", policy.MODEL_ID),
        "device": st.get("device"),
        "tier": policy.SCORER_TIER,
        "description": policy.SCORER_DESCRIPTION,
        "expected_auc": policy.EXPECTED_AUC,
        "expected_pcc": policy.EXPECTED_PCC,
        "calibrated": False,
        "flag_threshold": policy.FLAG_THRESHOLD,
        "confidence_kind": policy.CONFIDENCE_KIND,
        "min_snr_db": policy.MIN_SNR_DB,
        "withheld_phonemes": policy.WITHHELD_PHONEMES,
    }


@app.post("/score")
async def score(
    request: Request,
    audio: UploadFile = File(...),
    prompt_word: str = Form(...),
    speaker_age_years: str = Form(None),
):
    auth.current_parent(request)                   # 401s without a session

    raw = await audio.read()
    if not raw:
        return JSONResponse({"status": "retry", "reason": "empty_audio"}, status_code=200)

    age = None
    if speaker_age_years not in (None, "", "null"):
        try:
            age = int(float(speaker_age_years))
        except ValueError:
            age = None

    t0 = time.time()
    try:
        result = scorer.score_utterance(raw, prompt_word, age)
    except ValueError as exc:
        return JSONResponse({"status": "retry", "reason": "bad_audio", "detail": str(exc)},
                            status_code=200)
    except Exception as exc:                      # noqa: BLE001
        # Never invent a score. Surface the failure.
        return JSONResponse({"error": "scoring failed", "detail": str(exc)}, status_code=500)

    if isinstance(result, dict) and "provenance" in result:
        result["provenance"]["latency_ms"] = int((time.time() - t0) * 1000)
    return result


@app.post("/insights")
async def get_insights(request: Request, payload: dict = Body(...)):
    """Turns session history the app already has into a parent-facing note,
    plus a guarded pick of which words the next level should weight toward.

    Ported from the upstream fork's server/insights.py verbatim — the
    analysis/narration/word-selection logic is untouched. The only addition
    is the auth gate below: the fork has no accounts of its own, so this
    endpoint was open; here it requires the same signed-in-parent session
    /score already does, for consistency. The request body still carries the
    session history itself (core/rewards.js's store.sessions, oldest first)
    rather than a server-side lookup, matching the fork's original contract:
    {"child_name": str|None, "target_phone": str, "sessions": [...],
    "word_bank": [{"index": int, "text": str, "position": str, "phones": [...]}, ...]}.
    Never scores anything itself; ordinary arithmetic plus an optional,
    verified LLM sentence (Groq, falls back to a template with no API key)
    and an optional, guardrailed word selection on top.
    """
    auth.current_parent(request)                   # 401s without a session

    sessions = payload.get("sessions") or []
    target_phone = payload.get("target_phone") or "s"
    child_name = payload.get("child_name")
    word_bank = payload.get("word_bank") or []

    analysis = insights.compute_analysis(sessions, target_phone)
    text, source = insights.narrate(analysis, child_name)
    next_words, selection_source = (
        insights.select_next_words(analysis, word_bank) if word_bank else ([], "rule")
    )
    return {
        "text": text, "source": source,
        "next_words": next_words, "selection_source": selection_source,
        "analysis": analysis,
    }


# --------------------------------------------------------------------------
# static: landing page (public) + app (gated)
# --------------------------------------------------------------------------
# server/ (and its virtualenv, and any model artifacts) is never mounted.

for sub in ("core", "views", "design"):
    d = ROOT / sub
    if d.is_dir():
        app.mount("/app/%s" % sub, StaticFiles(directory=str(d)), name="app-%s" % sub)

_APP_FILES = {
    "app.css": ("app.css", "text/css"),
    "sw.js": ("sw.js", "application/javascript"),
    "manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "icon.svg": ("icon.svg", "image/svg+xml"),
    "icon-maskable.svg": ("icon-maskable.svg", "image/svg+xml"),
}
_LANDING_FILES = {
    "landing.css": ("landing.css", "text/css"),
    "landing.js": ("landing.js", "application/javascript"),
    "icon.svg": ("icon.svg", "image/svg+xml"),
    "icon-maskable.svg": ("icon-maskable.svg", "image/svg+xml"),
    "manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
}


def _signed_in(request: Request) -> bool:
    return bool(request.session.get("parent_id"))


def _file_response(name, media):
    f = ROOT / name
    if not f.is_file():
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(str(f), media_type=media)  # no_cache middleware covers headers


@app.get("/")
def landing():
    return _file_response("landing.html", "text/html")


# The /app* routes MUST be registered before the generic "/{name}" catch-all
# below — Starlette matches routes in registration order, and a single-segment
# wildcard registered first would swallow "/app" as name="app" (verified: this
# was a real 404 in testing before the reorder).

@app.get("/app")
def app_no_slash():
    # index.html and the JS modules it imports use paths relative to the
    # document ("./views/kid.js", "../core/rewards.js" from inside a view).
    # Those only resolve correctly if the browser's address bar ends in a
    # trailing slash — without this redirect, a bare "/app" hit would serve
    # the same HTML at a URL where "./views/kid.js" resolves to "/views/kid.js"
    # (no /app prefix) and 404s, breaking the app on first load.
    return RedirectResponse(url="/app/", status_code=307)


@app.get("/app/")
@app.get("/app/index.html")
def app_entry(request: Request):
    if not _signed_in(request):
        return RedirectResponse(url="/?auth=1", status_code=302)
    return _file_response("index.html", "text/html")


@app.get("/app/{name}")
def app_asset(name: str, request: Request):
    entry = _APP_FILES.get(name)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    # sw.js and the manifest are needed to install the PWA before signing in
    # (browsers register a service worker from a page that may itself gate
    # content); the HTML entry point is still the real access boundary.
    return _file_response(*entry)


@app.get("/{name}")
def landing_asset(name: str):
    entry = _LANDING_FILES.get(name)
    if entry:
        return _file_response(*entry)
    raise HTTPException(status_code=404, detail="Not found")
