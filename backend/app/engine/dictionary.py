"""UKACD dictionary loading and pattern-matching index."""
import os
import re
from collections import defaultdict

NON_ALPHA = re.compile(r"[^A-Z]")


def normalise(word: str) -> str:
    """Uppercase and strip everything except A-Z (drops spaces/hyphens/accents crudely)."""
    w = word.strip().upper()
    # transliterate a few common accented chars before stripping
    for src, dst in [("À", "A"), ("Á", "A"), ("Â", "A"), ("Ä", "A"), ("É", "E"), ("È", "E"),
                     ("Ê", "E"), ("Ë", "E"), ("Î", "I"), ("Ï", "I"), ("Í", "I"), ("Ô", "O"),
                     ("Ö", "O"), ("Ó", "O"), ("Û", "U"), ("Ü", "U"), ("Ú", "U"), ("Ç", "C"),
                     ("Ñ", "N")]:
        w = w.replace(src, dst)
    return NON_ALPHA.sub("", w)


UNKNOWN_RANK = 10 ** 9


class Dictionary:
    def __init__(self, path: str, freq_path: str | None = None,
                 min_len: int = 3, max_len: int = 21):
        self.words_by_len: dict[int, list[str]] = defaultdict(list)
        self.all_words: set[str] = set()
        # index: (length, position, letter) -> set of words
        self.index: dict[tuple[int, int, str], set[str]] = defaultdict(set)
        # word -> frequency rank (lower = more common); missing = obscure
        self.rank: dict[str, int] = {}
        self._load(path, min_len, max_len)
        if freq_path and os.path.exists(freq_path):
            self._load_frequencies(freq_path)

    def _load_frequencies(self, path: str):
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                w = normalise(line.split(" ")[0])
                if w and w not in self.rank:
                    self.rank[w] = i

    def rank_of(self, word: str) -> int:
        return self.rank.get(word, UNKNOWN_RANK)

    def _load(self, path: str, min_len: int, max_len: int):
        seen = set()
        in_header = True
        with open(path, encoding="latin-1") as f:
            for line in f:
                if in_header:
                    if line.startswith("----"):
                        in_header = False
                    continue
                w = normalise(line)
                if not (min_len <= len(w) <= max_len) or w in seen:
                    continue
                seen.add(w)
                self.words_by_len[len(w)].append(w)
                self.all_words.add(w)
                for i, ch in enumerate(w):
                    self.index[(len(w), i, ch)].add(w)

    def contains(self, word: str) -> bool:
        return normalise(word) in self.all_words

    def matches(self, pattern: list[str | None], exclude: set[str] | None = None) -> list[str]:
        """Words matching a pattern: list of fixed letters or None per cell."""
        length = len(pattern)
        constraints = [(i, ch) for i, ch in enumerate(pattern) if ch]
        if not constraints:
            pool = self.words_by_len.get(length, [])
            return [w for w in pool if not exclude or w not in exclude]
        # intersect smallest sets first
        sets = sorted((self.index.get((length, i, ch), set()) for i, ch in constraints), key=len)
        result = set(sets[0])
        for s in sets[1:]:
            result &= s
            if not result:
                return []
        if exclude:
            result -= exclude
        return list(result)

    def count_matches(self, pattern: list[str | None], exclude: set[str] | None = None) -> int:
        return len(self.matches(pattern, exclude))


_instance: Dictionary | None = None


def get_dictionary() -> Dictionary:
    global _instance
    if _instance is None:
        data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        path = os.environ.get("UKACD_PATH", os.path.join(data_dir, "UKACD.txt"))
        freq_path = os.environ.get("FREQ_PATH", os.path.join(os.path.dirname(path), "en_full.txt"))
        _instance = Dictionary(path, freq_path=freq_path)
    return _instance
