# Mira — Speech Practice

Mira is a kid-facing speech practice app ("Snake Sound Trail") with live
pronunciation scoring, plus parent/clinician views. One process serves
everything: a FastAPI backend does the scoring and also hosts the static
frontend, so there's nothing to configure separately.

- `index.html`, `app.css`, `core/`, `views/` — the frontend (vanilla JS, no build step)
- `server/` — the FastAPI scoring service (see [server/README.md](server/README.md) for the API and how the scorer works)

## Quick start

```bash
./start-mira.command
```

That's the whole thing — double-click it in Finder, or run it from a
terminal. First run creates a Python virtualenv, installs dependencies
(~2 GB of wheels), and downloads the acoustic model (~1.26 GB) into
`~/.cache/huggingface`; that only happens once. Every run after that starts
in well under 10 seconds and opens `http://localhost:8000` in your browser
automatically.

If you'd rather run it manually or on a different port:

```bash
cd server
PORT=9000 ./run.sh
```

### Keeping it up to date

`server/run.sh` checks `server/requirements.txt` on every launch and only
reinstalls dependencies when that file has actually changed, so pulling
updates and re-running is just:

```bash
git pull
./start-mira.command
```

## Setting up on a new machine

This repo is self-contained — clone it and run `./start-mira.command`.
Requirements: Python 3.10+ and network access for the first-run downloads
(dependencies + acoustic model). No API keys or external services needed.
