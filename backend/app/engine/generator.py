"""Crossword fill engine: slot extraction, numbering, backtracking fill."""
import random
import time
from collections import Counter
from dataclasses import dataclass, field

from .dictionary import Dictionary, normalise
from .templates import make_grid

MAX_CANDIDATES_PER_LEVEL = 60
FILL_TIME_LIMIT = 8.0  # seconds per attempt
ATTEMPTS = 6


@dataclass
class Slot:
    id: str
    number: int
    direction: str  # "across" | "down"
    row: int
    col: int
    length: int
    cells: list[tuple[int, int]] = field(default_factory=list)


def extract_slots(grid: list[list[bool]]) -> list[Slot]:
    """Find word slots (white runs >= 3) and assign standard crossword numbering."""
    n = len(grid)

    def starts_across(r, c):
        return grid[r][c] and (c == 0 or not grid[r][c - 1]) and c + 2 < n and grid[r][c + 1] and grid[r][c + 2]

    def starts_down(r, c):
        return grid[r][c] and (r == 0 or not grid[r - 1][c]) and r + 2 < n and grid[r + 1][c] and grid[r + 2][c]

    slots = []
    number = 0
    for r in range(n):
        for c in range(n):
            sa, sd = starts_across(r, c), starts_down(r, c)
            if sa or sd:
                number += 1
            if sa:
                length = 0
                while c + length < n and grid[r][c + length]:
                    length += 1
                slots.append(Slot(f"{number}-across", number, "across", r, c, length,
                                  [(r, c + i) for i in range(length)]))
            if sd:
                length = 0
                while r + length < n and grid[r + length][c]:
                    length += 1
                slots.append(Slot(f"{number}-down", number, "down", r, c, length,
                                  [(r + i, c) for i in range(length)]))
    return slots


def orphan_cells(grid: list[list[bool]], slots: list[Slot]) -> set[tuple[int, int]]:
    covered = {cell for s in slots for cell in s.cells}
    n = len(grid)
    return {(r, c) for r in range(n) for c in range(n) if grid[r][c] and (r, c) not in covered}


class FillResult:
    def __init__(self, grid, slots, assignment, unplaced):
        self.grid = grid
        self.slots = slots
        self.assignment = assignment  # slot.id -> word
        self.unplaced = unplaced      # [(word, reason)]


def _pattern(letters: dict[tuple[int, int], str], slot: Slot) -> list[str | None]:
    return [letters.get(cell) for cell in slot.cells]


def _backtrack(unfilled: list[Slot], letters: dict, assignment: dict, dictionary: Dictionary,
               excluded: set[str], rng: random.Random, deadline: float) -> bool:
    if not unfilled:
        return True
    if time.monotonic() > deadline:
        return False
    # most-constrained slot first
    scored = []
    for s in unfilled:
        cands = dictionary.matches(_pattern(letters, s), excluded | set(assignment.values()))
        scored.append((len(cands), s, cands))
        if not cands:
            return False
    scored.sort(key=lambda t: t[0])
    _, slot, cands = scored[0]
    rest = [s for s in unfilled if s.id != slot.id]
    # prefer common words: order by frequency rank with jitter for variety;
    # words absent from the frequency list sort last
    cands.sort(key=lambda w: dictionary.rank_of(w) + rng.randint(0, 5000))
    for word in cands[:MAX_CANDIDATES_PER_LEVEL]:
        placed = []
        ok = True
        for cell, ch in zip(slot.cells, word):
            if cell in letters:
                if letters[cell] != ch:
                    ok = False
                    break
            else:
                letters[cell] = ch
                placed.append(cell)
        if ok:
            assignment[slot.id] = word
            if _backtrack(rest, letters, assignment, dictionary, excluded, rng, deadline):
                return True
            del assignment[slot.id]
        for cell in placed:
            del letters[cell]
    return False


def _place_word(slot: Slot, word: str, letters: dict, assignment: dict) -> list[tuple[int, int]] | None:
    placed = []
    for cell, ch in zip(slot.cells, word):
        if cell in letters:
            if letters[cell] != ch:
                for p in placed:
                    del letters[p]
                return None
        else:
            letters[cell] = ch
            placed.append(cell)
    assignment[slot.id] = word
    return placed


def generate(size: int, desired_words: list[str], banned: set[str], dictionary: Dictionary,
             seed: int | None = None) -> FillResult:
    """Generate a filled grid, placing as many desired words as possible."""
    base_seed = seed if seed is not None else random.randrange(1 << 30)
    desired = []
    seen = set()
    for w in desired_words:
        nw = normalise(w)
        if nw and nw not in seen:
            seen.add(nw)
            desired.append(nw)
    desired.sort(key=len, reverse=True)  # so .pop() drops the shortest first
    excluded = {normalise(b) for b in banned}

    best = None  # (placed_count, FillResult)
    dropped: list[str] = []
    for attempt in range(ATTEMPTS):
        rng = random.Random(base_seed + attempt * 7919)
        # pick the template (out of several rolls) whose slot lengths cover
        # the most desired words
        want = sorted(len(w) for w in desired)
        grid, slots, best_cover = None, None, -1
        for roll in range(20):
            g = make_grid(size, seed=base_seed + attempt * 101 + roll)
            sl = extract_slots(g)
            available = Counter(s.length for s in sl)
            cover = 0
            taken = Counter()
            for L in want:
                if taken[L] < available.get(L, 0):
                    taken[L] += 1
                    cover += 1
            if cover > best_cover:
                grid, slots, best_cover = g, sl, cover
            if cover == len(want):
                break
        deadline = time.monotonic() + FILL_TIME_LIMIT

        letters: dict[tuple[int, int], str] = {}
        assignment: dict[str, str] = {}
        unplaced: list[tuple[str, str]] = []

        # Place desired words greedily, longest first
        for word in sorted(desired, key=len, reverse=True):
            if word in excluded:
                unplaced.append((word, "word is on the ban list"))
                continue
            candidates = [s for s in slots if s.length == len(word) and s.id not in assignment]
            if not candidates:
                unplaced.append((word, f"no available slot of length {len(word)} in this grid"))
                continue
            rng.shuffle(candidates)
            placed = False
            for s in candidates:
                if _place_word(s, word, letters, assignment) is not None:
                    placed = True
                    break
            if not placed:
                unplaced.append((word, "conflicts with crossing letters of already-placed words"))

        for w in dropped:
            unplaced.append((w, "dropped: grid could not be completed with this word included"))

        remaining = [s for s in slots if s.id not in assignment]
        if _backtrack(remaining, letters, assignment, dictionary, excluded, rng, deadline):
            result = FillResult(grid, slots, dict(assignment), unplaced)
            if not unplaced:
                return result
            placed_count = len(desired) - len(unplaced)
            if best is None or placed_count > best[0]:
                best = (placed_count, result)
        elif attempt >= ATTEMPTS // 2 and desired:
            # Fill keeps failing; relax by dropping the shortest desired word
            dropped.append(desired.pop())
        # loop retries with a new template/seed

    if best:
        return best[1]
    raise RuntimeError("Could not generate a complete grid; try fewer or shorter desired words.")


def refill_slots(grid: list[list[bool]], slots: list[Slot], fixed: dict[str, str],
                 dictionary: Dictionary, excluded: set[str],
                 desired: dict[str, str] | None = None,
                 seed: int | None = None) -> dict[str, str] | None:
    """Refill a grid keeping `fixed` (slot.id -> word) assignments.

    `desired` optionally pins specific new words to specific slots.
    Returns full assignment or None if impossible.
    """
    rng = random.Random(seed if seed is not None else random.randrange(1 << 30))
    letters: dict[tuple[int, int], str] = {}
    assignment: dict[str, str] = {}
    slot_by_id = {s.id: s for s in slots}

    for sid, word in fixed.items():
        if _place_word(slot_by_id[sid], word, letters, assignment) is None:
            return None
    if desired:
        for sid, word in desired.items():
            if _place_word(slot_by_id[sid], word, letters, assignment) is None:
                return None

    remaining = [s for s in slots if s.id not in assignment]
    deadline = time.monotonic() + FILL_TIME_LIMIT
    if _backtrack(remaining, letters, assignment, dictionary, excluded, rng, deadline):
        return assignment
    return None
