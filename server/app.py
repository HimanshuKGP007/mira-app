"""
app.py — the Mira scoring service.

  POST /score    multipart: audio (wav), prompt_word, speaker_age_years
  GET  /health   device, model, tier, stated limits
  GET  /         the Mira frontend, served from the same origin

Run:  ./run.sh        (or: uvicorn app:app --host 127.0.0.1 --port 8000)
"""

import contextlib
import pathlib
import time

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import policy
import scorer

FRONTEND = pathlib.Path(__file__).resolve().parent.parent


@contextlib.asynccontextmanager
async def lifespan(app):
    t0 = time.time()
    print("[mira] loading %s ..." % policy.MODEL_ID)
    st = scorer.load()
    print("[mira] ready on %s in %.1fs (tier=%s)"
          % (st["device"], time.time() - t0, policy.SCORER_TIER))
    yield


app = FastAPI(title="Mira scorer", version="0.1.0", lifespan=lifespan)

# Same-origin is the normal case (the frontend is mounted below), but allow a
# split origin for development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


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
    audio: UploadFile = File(...),
    prompt_word: str = Form(...),
    speaker_age_years: str = Form(None),
):
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


# --------------------------------------------------------------------------
# static frontend
# --------------------------------------------------------------------------
# Mount the asset directories explicitly rather than the whole project root:
# `server/` lives inside it and contains the virtualenv (and, later, any model
# artifacts), none of which should be reachable over HTTP.

for sub in ("core", "views"):
    d = FRONTEND / sub
    if d.is_dir():
        app.mount("/%s" % sub, StaticFiles(directory=str(d)), name=sub)

_ROOT_FILES = {
    "": ("index.html", "text/html"),
    "index.html": ("index.html", "text/html"),
    "app.css": ("app.css", "text/css"),
    "sw.js": ("sw.js", "application/javascript"),
    "manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "icon.svg": ("icon.svg", "image/svg+xml"),
    "icon-maskable.svg": ("icon-maskable.svg", "image/svg+xml"),
}


@app.get("/{path:path}")
def frontend(path: str):
    from fastapi.responses import FileResponse, PlainTextResponse
    entry = _ROOT_FILES.get(path)
    if not entry:
        return PlainTextResponse("Not found", status_code=404)
    name, media = entry
    f = FRONTEND / name
    if not f.is_file():
        return PlainTextResponse("Not found", status_code=404)
    # sw.js must not be cached by the browser or updates never land
    headers = {"Cache-Control": "no-cache"} if name == "sw.js" else None
    return FileResponse(str(f), media_type=media, headers=headers)
