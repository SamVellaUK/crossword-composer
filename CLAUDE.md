# Crossword Composer — Claude working notes

Web app for composing cryptic crosswords. Product spec: `SPEC.md` (kept up to date —
read it first; it documents both intent and as-built behaviour).

## Architecture

- `backend/` — Python 3.12 / FastAPI
  - `app/main.py` — all API routes; status derivation (`_compute_status`); lock rules
  - `app/storage.py` — one JSON file per puzzle in `/data/puzzles` + SQLite index + ban list
  - `app/pdf.py` — WeasyPrint single-page PDF export
  - `app/engine/templates.py` — symmetric grid templates (lattice + split patterns +
    validator). Supported sizes: 9/11/13/15 only. 9x9 cannot host 7-letter words.
  - `app/engine/generator.py` — slot extraction/numbering, backtracking fill,
    desired-word placement, `refill_slots` (used by reject-word redesign)
  - `app/engine/dictionary.py` — loads UKACD + frequency ranks at startup (~5s)
  - `data/UKACD.txt` — UK Advanced Cryptics Dictionary, ~249k entries, latin-1,
    licence header at top (loader skips until `----` line). Keep the header: licence
    requires it.
  - `data/en_full.txt` — word frequency list (hermitdave/FrequencyWords, OpenSubtitles,
    CC-BY-SA). UKACD has NO frequency info; this is what keeps obscure words out of fills.
- `frontend/` — React 18 + Vite PWA, no router lib (hash routing in `App.jsx`),
  no state lib. Served by Nginx which proxies `/api/` -> `backend:8000/` (prefix stripped;
  backend routes have NO /api prefix).
  - `src/components/Editor.jsx` — the main screen: tap-word-on-grid interaction,
    clue editing (auto-grow textareas), lock/reject/replace, undo (client-side
    snapshot stack, last 5), rebuild
- `docker-compose.yml` — frontend (port 8410) + backend + named `puzzles` volume

## Data format

Puzzle JSON is **Guardian-derived, not an open standard** (see SPEC.md §4). App-specific
additions: `appMeta`, per-entry `annotation` and `locked`. Status (`draft`/`complete`/
`published`) is always derived server-side — never set it manually. If export
interoperability is requested, implement **ipuz** (deferred decision, SPEC.md §10).

## Build / test / deploy workflow

No Node on the dev box — frontend builds happen inside Docker.

```bash
# local engine/API tests (venv at /tmp/cwc-venv has fastapi+weasyprint+httpx)
cd backend && UKACD_PATH=data/UKACD.txt python3 -c "..."   # engine only, no deps

# build + local smoke test
docker build -t ghcr.io/samvellauk/crossword-composer-backend:latest ./backend
docker build -t ghcr.io/samvellauk/crossword-composer-frontend:latest ./frontend
docker compose up -d   # then hit http://localhost:8410/api/health
docker compose down

# release
docker push ghcr.io/samvellauk/crossword-composer-backend:latest
docker push ghcr.io/samvellauk/crossword-composer-frontend:latest
dockge update crossword-composer    # pulls + redeploys on the home server
```

Backend takes ~10s to come up (loads 1.4M frequency ranks); don't panic at one 502.

## Deployment / infra

- Live: **https://cc.samsdiner.duckdns.org** (and http://192.168.1.133:8410 direct)
- Dockge stack `crossword-composer` on home server 192.168.1.133 (`dockge` CLI; see
  user-level CLAUDE.md). No SSH access to that server from the dev box.
- GHCR images are private; the server's docker daemon is already logged in.
  Package visibility cannot be changed via the GitHub REST API (UI only).
- TLS terminated by nginx-proxy-manager stack (wildcard `*.samsdiner.duckdns.org`).
- LAN DNS = `dnsmasq` Dockge stack: one `--address=/<sub>.samsdiner.duckdns.org/100.64.182.74`
  line per service in the compose `command`. **Gotcha:** editing the compose does
  nothing until `dockge deploy dnsmasq` — a stale container silently REFUSES new names.

## Conventions

- User (Sam) drops UI feedback as phone screenshots into `screenshots/` (gitignored).
- Reply to Sam via `telegram-send` when finishing significant work.
- The service worker is network-first, so a browser refresh picks up new deploys.
- Don't commit unless asked.
