"""Crossword Composer API."""
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from . import storage
from .engine.dictionary import get_dictionary, normalise
from .engine.generator import Slot, extract_slots, generate, refill_slots
from .pdf import render_pdf

app = FastAPI(title="Crossword Composer")


@app.on_event("startup")
def startup():
    storage.init()
    get_dictionary()  # load UKACD into memory


# ---------- request models ----------

class NewPuzzleRequest(BaseModel):
    name: str = "Untitled crossword"
    size: int = 13
    words: list[str] = Field(default_factory=list)
    author: str = ""


class UpdatePuzzleRequest(BaseModel):
    puzzle: dict


class RejectWordRequest(BaseModel):
    entryId: str
    replacement: str | None = None
    ban: bool = False


class BanWordRequest(BaseModel):
    word: str


# ---------- helpers ----------

def _entries_from_fill(slots: list[Slot], assignment: dict[str, str],
                       old_entries: dict[str, dict] | None = None) -> list[dict]:
    entries = []
    for s in sorted(slots, key=lambda s: (s.number, s.direction)):
        word = assignment[s.id]
        old = (old_entries or {}).get(s.id, {})
        same = old.get("solution") == word
        entries.append({
            "id": s.id,
            "number": s.number,
            "humanNumber": str(s.number),
            "direction": s.direction,
            "length": s.length,
            "position": {"x": s.col, "y": s.row},
            "solution": word,
            "clue": old.get("clue", "") if same else "",
            "annotation": old.get("annotation", "") if same else "",
            "locked": bool(old.get("locked")) if same else False,
            "group": [s.id],
            "separatorLocations": {},
        })
    return entries


def _compute_status(puzzle: dict) -> str:
    """draft -> complete (all clues written) -> published (PDF exported)."""
    history = puzzle["appMeta"].get("exportHistory", [])
    if any(h.get("format") == "pdf" for h in history):
        return "published"
    if puzzle["entries"] and all((e.get("clue") or "").strip() for e in puzzle["entries"]):
        return "complete"
    return "draft"


def _grid_from_puzzle(puzzle: dict) -> tuple[list[list[bool]], list[Slot], dict[str, str]]:
    n = puzzle["dimensions"]["rows"]
    grid = [[False] * n for _ in range(n)]
    for e in puzzle["entries"]:
        x, y = e["position"]["x"], e["position"]["y"]
        for i in range(e["length"]):
            r = y + (i if e["direction"] == "down" else 0)
            c = x + (i if e["direction"] == "across" else 0)
            grid[r][c] = True
    slots = extract_slots(grid)
    assignment = {e["id"]: e["solution"] for e in puzzle["entries"]}
    return grid, slots, assignment


def _load_or_404(puzzle_id: str) -> dict:
    puzzle = storage.load_puzzle(puzzle_id)
    if puzzle is None:
        raise HTTPException(404, "Puzzle not found")
    return puzzle


# ---------- puzzles ----------

@app.get("/puzzles")
def list_puzzles():
    return storage.list_puzzles()


@app.post("/puzzles", status_code=201)
def create_puzzle(req: NewPuzzleRequest):
    dictionary = get_dictionary()
    banned = set(storage.get_ban_list())
    unrecognised = [w for w in req.words if normalise(w) and not dictionary.contains(w)]
    try:
        result = generate(req.size, req.words, banned, dictionary)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(422, str(e))

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    # desired words that made it into the grid start out locked
    desired_placed = {normalise(w) for w in req.words} & set(result.assignment.values())
    entries = _entries_from_fill(result.slots, result.assignment)
    for e in entries:
        if e["solution"] in desired_placed:
            e["locked"] = True
    puzzle = {
        "id": str(uuid.uuid4()),
        "number": 1,
        "name": req.name,
        "creator": {"name": req.author, "webUrl": ""},
        "date": now_ms,
        "webPublicationDate": now_ms,
        "dimensions": {"cols": req.size, "rows": req.size},
        "crosswordType": "cryptic",
        "solutionAvailable": True,
        "entries": entries,
        "instructions": "",
        "appMeta": {
            "status": "draft",
            "createdAt": storage.now_iso(),
            "updatedAt": storage.now_iso(),
            "banListSnapshot": sorted(banned),
            "rejectedWords": [],
            "exportHistory": [],
        },
    }
    storage.save_puzzle(puzzle)
    return {"puzzle": puzzle,
            "unplacedWords": [{"word": w, "reason": r} for w, r in result.unplaced],
            "unrecognisedWords": unrecognised}


@app.get("/puzzles/{puzzle_id}")
def get_puzzle(puzzle_id: str):
    return _load_or_404(puzzle_id)


@app.put("/puzzles/{puzzle_id}")
def update_puzzle(puzzle_id: str, req: UpdatePuzzleRequest):
    existing = _load_or_404(puzzle_id)
    puzzle = req.puzzle
    puzzle["id"] = puzzle_id  # id is immutable
    puzzle.setdefault("appMeta", existing["appMeta"])
    puzzle["appMeta"]["createdAt"] = existing["appMeta"]["createdAt"]
    puzzle["appMeta"]["status"] = _compute_status(puzzle)
    storage.save_puzzle(puzzle)
    return puzzle


@app.delete("/puzzles/{puzzle_id}")
def delete_puzzle(puzzle_id: str):
    if not storage.delete_puzzle(puzzle_id):
        raise HTTPException(404, "Puzzle not found")
    return {"deleted": puzzle_id}


@app.post("/puzzles/{puzzle_id}/reject-word")
def reject_word(puzzle_id: str, req: RejectWordRequest):
    puzzle = _load_or_404(puzzle_id)
    entry = next((e for e in puzzle["entries"] if e["id"] == req.entryId), None)
    if entry is None:
        raise HTTPException(404, "Entry not found")
    if entry.get("locked"):
        raise HTTPException(400, "Word is locked; unlock it first")

    dictionary = get_dictionary()
    rejected_word = entry["solution"]
    rejected = set(puzzle["appMeta"].get("rejectedWords", []))
    rejected.add(rejected_word)
    if req.ban:
        storage.add_banned_word(rejected_word)
    excluded = {normalise(w) for w in storage.get_ban_list()} | {normalise(w) for w in rejected}

    grid, slots, assignment = _grid_from_puzzle(puzzle)
    old_entries = {e["id"]: e for e in puzzle["entries"]}

    replacement = normalise(req.replacement) if req.replacement else None
    if replacement and len(replacement) != entry["length"]:
        raise HTTPException(400, f"Replacement must be {entry['length']} letters")

    # Try keeping everything else fixed first; widen the redesign if that fails.
    # Locked words are never released, even in the wider redesign.
    locked_ids = {e["id"] for e in puzzle["entries"] if e.get("locked")}
    fixed_all = {sid: w for sid, w in assignment.items() if sid != req.entryId}
    crossing_ids = {s.id for s in slots
                    if s.id != req.entryId and any(
                        cell in set(next(x for x in slots if x.id == req.entryId).cells)
                        for cell in s.cells)}
    fixed_partial = {sid: w for sid, w in fixed_all.items()
                     if sid not in crossing_ids or sid in locked_ids}

    new_assignment = None
    for fixed in (fixed_all, fixed_partial):
        desired = {req.entryId: replacement} if replacement else None
        new_assignment = refill_slots(grid, slots, fixed, dictionary, excluded, desired=desired)
        if new_assignment:
            break
    if not new_assignment:
        raise HTTPException(422, "Could not find a valid refill for that section"
                                 + (" with the suggested replacement" if replacement else ""))

    puzzle["entries"] = _entries_from_fill(slots, new_assignment, old_entries)
    if replacement:
        # a word the user asked for by name gets locked, like initial desired words
        for e in puzzle["entries"]:
            if e["id"] == req.entryId:
                e["locked"] = True
    puzzle["appMeta"]["rejectedWords"] = sorted(rejected)
    puzzle["appMeta"]["status"] = _compute_status(puzzle)
    storage.save_puzzle(puzzle)
    return puzzle


@app.post("/puzzles/{puzzle_id}/rebuild")
def rebuild(puzzle_id: str):
    """Regenerate the whole grid from scratch, keeping locked words (and their clues)."""
    puzzle = _load_or_404(puzzle_id)
    dictionary = get_dictionary()
    locked = [e for e in puzzle["entries"] if e.get("locked")]
    excluded = set(storage.get_ban_list()) | set(puzzle["appMeta"].get("rejectedWords", []))
    size = puzzle["dimensions"]["cols"]
    try:
        result = generate(size, [e["solution"] for e in locked], excluded, dictionary)
    except RuntimeError as e:
        raise HTTPException(422, str(e))

    entries = _entries_from_fill(result.slots, result.assignment)
    by_solution = {e["solution"]: e for e in locked}
    for e in entries:
        old = by_solution.get(e["solution"])
        if old:
            e["locked"] = True
            e["clue"] = old.get("clue", "")
            e["annotation"] = old.get("annotation", "")
    puzzle["entries"] = entries
    puzzle["appMeta"]["status"] = _compute_status(puzzle)
    storage.save_puzzle(puzzle)
    return {"puzzle": puzzle,
            "unplacedWords": [{"word": w, "reason": r} for w, r in result.unplaced]}


# ---------- export ----------

@app.get("/puzzles/{puzzle_id}/export/json")
def export_json(puzzle_id: str):
    puzzle = _load_or_404(puzzle_id)
    puzzle["appMeta"].setdefault("exportHistory", []).append(
        {"format": "json", "exportedAt": storage.now_iso()})
    storage.save_puzzle(puzzle)
    fname = f"{puzzle['name'].replace(' ', '-')}.json"
    return JSONResponse(puzzle, headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.get("/puzzles/{puzzle_id}/export/pdf")
def export_pdf(puzzle_id: str):
    puzzle = _load_or_404(puzzle_id)
    pdf_bytes = render_pdf(puzzle)
    puzzle["appMeta"].setdefault("exportHistory", []).append(
        {"format": "pdf", "exportedAt": storage.now_iso()})
    puzzle["appMeta"]["status"] = _compute_status(puzzle)
    storage.save_puzzle(puzzle)
    fname = f"{puzzle['name'].replace(' ', '-')}-crossword.pdf"
    return Response(pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


# ---------- ban list ----------

@app.get("/ban-list")
def get_ban_list():
    return storage.get_ban_list()


@app.post("/ban-list", status_code=201)
def add_ban_word(req: BanWordRequest):
    word = normalise(req.word)
    if not word:
        raise HTTPException(400, "Invalid word")
    storage.add_banned_word(word)
    return storage.get_ban_list()


@app.delete("/ban-list/{word}")
def remove_ban_word(word: str):
    if not storage.remove_banned_word(normalise(word)):
        raise HTTPException(404, "Word not on ban list")
    return storage.get_ban_list()


@app.get("/health")
def health():
    return {"status": "ok", "dictionarySize": len(get_dictionary().all_words)}
