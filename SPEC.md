# Crossword Composer — Product Specification

## Overview

A containerised web application for creating classical cryptic crossword puzzles. The app guides a user from grid generation through word placement, clue authoring, and final export.

---

## 1. Grid Generation

### Input Parameters
- **Grid size** — e.g. `9x9`, `13x13`, `15x15` (standard cryptic sizes)
- **Desired words** — a user-supplied list of words to include in the puzzle

### Behaviour
- The app attempts to fit all desired words into a valid crossword grid, following classical cryptic conventions:
  - Rotational symmetry (180°)
  - No unchecked squares (every letter belongs to both an across and a down word, or is checked by at least one crossing)
  - Minimum word length (typically 3+ letters)
  - Standard black-square patterns
- If not all desired words can be placed, the app should indicate which words could not be included and why

---

## 2. Word Management

### Review & Rejection
- After grid generation, the user sees the populated grid with all placed words
- Each word can be individually **rejected**
- Rejecting a word triggers a **redesign** of affected grid sections to find a replacement
- The user can suggest a **replacement word**; if it fits the current grid geometry it is slotted in, otherwise a partial redesign is performed

### Ban List
- Words can be added to a persistent **ban list**
- Banned words are never proposed by the algorithm during generation or redesign
- The ban list is editable from a settings/preferences area

---

## 3. Clue Authoring

### Clue Entry Interface
- Once the grid is finalised, the user enters **clue authoring mode**
- Each word (across and down) is listed with:
  - Its number, direction, and answer
  - A text field for the clue
  - An optional field for the surface reading / annotation
- Clues are saved automatically as they are entered
- The interface should support toggling between the grid view and the clue list view

---

## 4. Data Model

### Storage Format
- Puzzles are stored as **JSON documents**, based on the Guardian crossword JSON format
- Each puzzle is a single `.json` file identified by a UUID
- An index file (or lightweight SQLite DB) tracks puzzle metadata for the front page listing

### Guardian-compatible Schema

The core puzzle object mirrors the Guardian format, with additional fields for app-specific state:

```jsonc
{
  // --- Guardian-compatible fields ---
  "id": "uuid-v4",                        // internal UUID (Guardian uses "crosswords/quick-cryptic/45")
  "number": 45,
  "name": "Quick cryptic crossword No 45",
  "creator": {
    "name": "Author Name",
    "webUrl": ""
  },
  "date": 1738972800000,                  // Unix ms timestamp
  "webPublicationDate": 1738972806000,
  "dimensions": {
    "cols": 11,
    "rows": 11
  },
  "crosswordType": "quick-cryptic",       // or "cryptic", "quick", etc.
  "solutionAvailable": true,
  "entries": [
    {
      "id": "1-across",
      "number": 1,
      "humanNumber": "1",
      "direction": "across",              // "across" | "down"
      "length": 7,
      "position": { "x": 0, "y": 0 },    // 0-indexed col/row of first letter
      "solution": "RATCHET",
      "clue": "Wild chatter has teeth on edge (7)",
      "group": ["1-across"],              // for multi-part clues
      "separatorLocations": {}            // e.g. {",": [6]} for "SCHOOL,RUN"
    }
    // ... more entries
  ],
  "instructions": "",                     // optional setter notes shown to solver

  // --- App-specific fields (not in Guardian format) ---
  "appMeta": {
    "status": "draft",                    // "draft" | "clues_complete" | "exported"
    "createdAt": "2025-02-08T00:00:00Z",
    "updatedAt": "2025-02-08T12:00:00Z",
    "banListSnapshot": ["WORD1", "WORD2"],
    "exportHistory": [
      { "format": "pdf", "exportedAt": "2025-02-09T10:00:00Z" },
      { "format": "json", "exportedAt": "2025-02-09T10:01:00Z" }
    ]
  }
}
```

**Key schema notes:**
- `position` uses `{x, y}` where `x` = column (left→right), `y` = row (top→bottom), both 0-indexed
- Black squares are implicit — any cell not covered by an entry is black
- `separatorLocations` marks hyphens/commas within multi-word answers (e.g. `SCHOOL RUN` → `{",": [6]}`)
- `group` supports linked clues that span multiple entries (e.g. "1, 14-across")
- The Guardian `pdf` field is omitted; our app generates its own PDF on demand

---

## 5. Front Page / Dashboard

### Puzzle List
- Displays all saved puzzles as cards or rows, showing:
  - Title / working title
  - Grid size
  - Word count
  - Status (Draft / Clues Complete / Exported)
  - Date created / last modified
- Actions per puzzle:
  - **Open** — resume editing
  - **Export JSON** — download the raw JSON document
  - **Export PDF** — generate a single-page print-ready PDF of the puzzle (grid + clues)
  - **Delete**

### New Puzzle
- A prominent "New Puzzle" button opens a dialog for size and initial word list

---

## 6. Frontend — Responsive & Installable

### Responsive Design
- The UI must work on both **desktop** and **mobile** screen sizes
- Grid editing is the most complex view — on mobile, the grid and clue panel should stack vertically; on desktop they sit side by side
- Touch-friendly tap targets throughout (minimum 44px)

### Progressive Web App (PWA)
- The frontend is a PWA so users can **install it from the browser** on any device (Android, iOS, desktop Chrome/Edge)
- Requires:
  - A `manifest.json` with app name, icons, and `display: standalone`
  - A service worker for offline shell caching (puzzle data itself requires the backend)
  - HTTPS is required for PWA install on non-localhost devices — SSL will be terminated by an external Nginx reverse proxy in front of the container

---

## 7. PDF Export

- Single-page layout containing:
  - Puzzle title and author
  - Numbered grid (black and white, print-friendly)
  - Across clues column
  - Down clues column
- Generated server-side (e.g. with a headless renderer or a PDF library)
- File named `<title>-crossword.pdf`

---

## 8. Architecture

### Stack
- **Frontend** — React SPA (PWA), served by Nginx
- **Backend API** — Python / FastAPI
- **Crossword engine** — integrated into the backend (Python constraint-satisfaction library)
- **PDF generation** — WeasyPrint, called server-side
- **Persistence** — JSON files on a named Docker volume; SQLite index for the dashboard listing

### Container Setup
- Single Docker Compose stack:
  - `frontend` — Nginx serving the built React PWA
  - `backend` — FastAPI app (includes engine + PDF generation)
  - Named volume mounted at `/data/puzzles` in the backend container
- The backend API must bind to `0.0.0.0` (not just `127.0.0.1`) so it is reachable from other LAN devices
- Frontend proxies API calls through Nginx to avoid CORS issues

### API Endpoints (outline)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/puzzles` | List all puzzles |
| POST | `/puzzles` | Create new puzzle (size + word list) |
| GET | `/puzzles/:id` | Fetch puzzle JSON |
| PUT | `/puzzles/:id` | Update puzzle (words, clues, metadata) |
| DELETE | `/puzzles/:id` | Delete puzzle |
| POST | `/puzzles/:id/reject-word` | Reject a word, optionally suggest replacement |
| GET | `/puzzles/:id/export/pdf` | Generate and return PDF |
| GET | `/puzzles/:id/export/json` | Download puzzle JSON |
| GET | `/ban-list` | Fetch ban list |
| POST | `/ban-list` | Add word to ban list |
| DELETE | `/ban-list/:word` | Remove word from ban list |

---

## 9. Decisions

- [x] Guardian JSON schema — confirmed from live API, see Section 4
- [x] Backend — **Python + FastAPI** (lightweight, excellent library support for constraint solving and PDF generation)
- [x] Crossword generation algorithm — constraint satisfaction / backtracking (TBD exact library)
- [x] Authentication — **none** (LAN-only, trusted network)
- [x] Hosting — local network only, accessed from other devices on the LAN (not localhost)
- [x] PDF — **WeasyPrint** (Python-native, no headless browser needed, good print CSS support)
- [x] Ban list — **global** across all puzzles

---

## 10. Out of Scope (v1)

- Automatic clue generation (AI-suggested clues)
- Collaborative editing
- Publishing / sharing puzzles publicly
- Mobile-native app
