"""Symmetric cryptic grid template generation.

Grids start from the classic lattice convention: cells are white when the row
or column index is even; odd/odd cells are black. Extra black squares are then
inserted on the full-length even rows/columns to break them into word-sized
runs. Splits at odd offsets give odd-length lights; splits at even offsets
give even-length lights (and also affect the crossing line, so generated
grids are validated and re-rolled until sound). All insertions preserve
180-degree rotational symmetry.
"""
import random
from collections import deque

# Split patterns: for a line of length n, positions to blacken.
# Every resulting segment is >= 3 in the line itself; interactions with
# crossing lines are handled by validate().
SPLITS = {
    9: [{3}, {5}, {4}, set()],
    11: [{5}, {3, 7}, {4}, {6}, set()],
    13: [{5}, {7}, {3, 9}, {6}, {4, 8}, {3}, {9}, set()],
    15: [{7}, {3, 11}, {5, 9}, {4, 10}, {6}, {8}, {5}, {9}, set()],
}

SUPPORTED_SIZES = sorted(SPLITS)


def _line_patterns(n: int, rng: random.Random) -> dict[int, set[int]]:
    """Choose a black-square pattern for each even line index, symmetric under rotation."""
    options = SPLITS[n]
    self_sym = [p for p in options if p == {n - 1 - x for x in p}]
    patterns: dict[int, set[int]] = {}
    for r in range(0, n, 2):
        if r in patterns:
            continue
        mirror = n - 1 - r
        if r == mirror:
            patterns[r] = rng.choice(self_sym) if self_sym else set()
        else:
            p = rng.choice(options)
            patterns[r] = p
            patterns[mirror] = {n - 1 - x for x in p}
    return patterns


def _runs(line: list[bool]) -> list[int]:
    runs, count = [], 0
    for cell in line:
        if cell:
            count += 1
        elif count:
            runs.append(count)
            count = 0
    if count:
        runs.append(count)
    return runs


def validate(grid: list[list[bool]]) -> bool:
    """No 2-length runs, no orphan cells, and the white cells are connected."""
    n = len(grid)
    in_word = [[False] * n for _ in range(n)]
    lines = [[(r, c) for c in range(n)] for r in range(n)] + \
            [[(r, c) for r in range(n)] for c in range(n)]
    for line in lines:
        count = 0
        for i, (r, c) in enumerate(line + [(-1, -1)]):
            white = (r >= 0) and grid[r][c]
            if white:
                count += 1
            else:
                if count == 2:
                    return False
                if count >= 3:
                    for rr, cc in line[i - count:i]:
                        in_word[rr][cc] = True
                count = 0
    whites = [(r, c) for r in range(n) for c in range(n) if grid[r][c]]
    if any(not in_word[r][c] for r, c in whites):
        return False
    # connectivity
    seen = {whites[0]}
    queue = deque([whites[0]])
    while queue:
        r, c = queue.popleft()
        for nr, nc in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
            if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] and (nr, nc) not in seen:
                seen.add((nr, nc))
                queue.append((nr, nc))
    return len(seen) == len(whites)


def make_grid(size: int, seed: int = 0, max_tries: int = 300) -> list[list[bool]]:
    """Return a size x size boolean grid; True = white cell."""
    if size not in SPLITS:
        raise ValueError(f"Unsupported grid size {size}; supported: {SUPPORTED_SIZES}")
    rng = random.Random(seed)
    for _ in range(max_tries):
        grid = [[(r % 2 == 0 or c % 2 == 0) for c in range(size)] for r in range(size)]
        for r, cols in _line_patterns(size, rng).items():
            for c in cols:
                grid[r][c] = False
        for c, rows in _line_patterns(size, rng).items():
            for r in rows:
                grid[r][c] = False
        if validate(grid):
            return grid
    raise RuntimeError(f"Could not build a valid {size}x{size} template")
