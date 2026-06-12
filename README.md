# Crossword Composer

A self-hosted web app for composing classical cryptic crosswords: generate a
symmetric grid around your desired words, swap/reject/lock words, write clues,
and export a print-ready PDF. Installable as a PWA on phone or desktop.

Live (LAN/Tailscale only): https://cc.samsdiner.duckdns.org

## Features

- Grid generation (9/11/13/15) with 180° rotational symmetry, filled from the
  UKACD cryptics dictionary with frequency-ranked word choice
- Tap a word on the grid to edit its clue, reject it, ban it, replace it, or
  lock it (locked words survive all redesigns)
- Full-board **Rebuild** keeping locked words and their clues; client-side
  **Undo** for the last 5 grid changes
- Clue-list-only mode with inline editing for fast clue writing
- Automatic status: draft → complete (all clues written) → published (PDF exported)
- Exports: puzzle JSON and single-page A4 PDF (grid + clues)

## Running

```bash
docker compose up -d --build
# UI on http://localhost:8410
```

The backend takes ~10s to start (loads 1.4M frequency ranks). Puzzles persist
on the `puzzles` named volume.

## Export / data format

Puzzles are stored and exported as JSON in a **Guardian-derived format** — not
an open standard (see SPEC.md §4 "Format provenance"). If interoperability is
ever needed, target **ipuz** (deferred for now); `.puz` and JPZ were considered
and rejected.

## Documentation

- `SPEC.md` — product spec, data model, decisions log (kept up to date as built)
- `CLAUDE.md` — developer/successor guide: architecture map, build/test/deploy
  workflow, infra notes

## Word list licences

- `backend/data/UKACD.txt` — UK Advanced Cryptics Dictionary (J. Ross Beresford),
  distributed under its original BSD-style licence (header retained in the file)
- `backend/data/en_full.txt` — frequency list from
  [hermitdave/FrequencyWords](https://github.com/hermitdave/FrequencyWords)
  (OpenSubtitles-derived), CC-BY-SA
