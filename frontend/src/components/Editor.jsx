import React, { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import GridView from './GridView.jsx'

function AutoTextarea({ value, onChange, placeholder, className }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${el.scrollHeight}px`
    }
  }, [value])
  return (
    <textarea ref={ref} rows={1} className={className} value={value}
              placeholder={placeholder} onChange={onChange} />
  )
}

// letters fixed by crossing words, per cell of the entry (null = unchecked)
function crossLetters(puzzle, entry) {
  const letters = {}
  for (const e of puzzle.entries) {
    if (e.id === entry.id) continue
    for (let i = 0; i < e.length; i++) {
      const y = e.position.y + (e.direction === 'down' ? i : 0)
      const x = e.position.x + (e.direction === 'across' ? i : 0)
      letters[`${y},${x}`] = e.solution[i]
    }
  }
  return Array.from({ length: entry.length }, (_, i) => {
    const y = entry.position.y + (entry.direction === 'down' ? i : 0)
    const x = entry.position.x + (entry.direction === 'across' ? i : 0)
    return letters[`${y},${x}`] || null
  })
}

export default function Editor({ puzzleId }) {
  const [puzzle, setPuzzle] = useState(null)
  const [clueListOnly, setClueListOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [replacing, setReplacing] = useState(false)
  const [replacement, setReplacement] = useState('')
  const [saveState, setSaveState] = useState('saved')
  const saveTimer = useRef(null)
  const puzzleRef = useRef(null)
  puzzleRef.current = puzzle

  useEffect(() => {
    api.getPuzzle(puzzleId).then(setPuzzle).catch((e) => setError(e.message))
  }, [puzzleId])

  useEffect(() => { setReplacing(false); setReplacement('') }, [selectedId])

  const scheduleSave = useCallback(() => {
    setSaveState('saving')
    clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(async () => {
      try {
        await api.updatePuzzle(puzzleId, puzzleRef.current)
        setSaveState('saved')
      } catch (e) {
        setSaveState('error')
        setError(e.message)
      }
    }, 600)
  }, [puzzleId])

  const setEntryField = (entryId, field, value) => {
    setPuzzle((p) => ({
      ...p,
      entries: p.entries.map((e) => (e.id === entryId ? { ...e, [field]: value } : e)),
    }))
    scheduleSave()
  }

  const [history, setHistory] = useState([]) // last 5 grid-changing actions

  const pushHistory = (snapshot, bannedWord) =>
    setHistory((h) => [...h.slice(-4), { snapshot, bannedWord }])

  const reject = async (entry, ban, repl) => {
    setBusy(true)
    setError('')
    const snapshot = JSON.parse(JSON.stringify(puzzleRef.current))
    try {
      const updated = await api.rejectWord(puzzleId, {
        entryId: entry.id,
        ban,
        replacement: repl || null,
      })
      pushHistory(snapshot, ban ? entry.solution : null)
      setPuzzle(updated)
      setReplacing(false)
      setReplacement('')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const rebuild = async () => {
    if (!window.confirm('Rebuild the whole board with a new grid? Locked words (and their clues) are kept; everything else is regenerated.')) return
    setBusy(true)
    setError('')
    const snapshot = JSON.parse(JSON.stringify(puzzleRef.current))
    try {
      const res = await api.rebuild(puzzleId)
      pushHistory(snapshot, null)
      setPuzzle(res.puzzle)
      setSelectedId(null)
      if (res.unplacedWords.length) {
        setError('Could not keep: ' + res.unplacedWords.map((u) => `${u.word} (${u.reason})`).join('; '))
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const undo = async () => {
    const last = history[history.length - 1]
    if (!last) return
    setBusy(true)
    setError('')
    try {
      const restored = await api.updatePuzzle(puzzleId, last.snapshot)
      if (last.bannedWord) await api.removeBanWord(last.bannedWord).catch(() => {})
      setPuzzle(restored)
      setSelectedId(null)
      setHistory((h) => h.slice(0, -1))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !puzzle) return <p className="error">{error}</p>
  if (!puzzle) return <p className="muted">Loading…</p>

  const selected = puzzle.entries.find((e) => e.id === selectedId) || null

  const clueFields = (e) => (
    <div className="clue-fields">
      <AutoTextarea
        className="clue-input"
        value={e.clue || ''}
        placeholder="Clue"
        onChange={(ev) => setEntryField(e.id, 'clue', ev.target.value)}
      />
      <input
        className="annotation"
        value={e.annotation || ''}
        placeholder="Annotation / surface notes"
        onChange={(ev) => setEntryField(e.id, 'annotation', ev.target.value)}
      />
    </div>
  )

  return (
    <div className="page editor">
      <div className="page-head">
        <h1>{puzzle.name}</h1>
        <div className="head-actions">
          <span className={`save-state ${saveState}`}>
            {saveState === 'saving' ? 'Saving…' : saveState === 'error' ? 'Save failed' : 'Saved'}
          </span>
          <button className="btn sm" disabled={busy || history.length === 0} onClick={undo}>
            Undo{history.length ? ` (${history.length})` : ''}
          </button>
          <button className="btn sm" disabled={busy} onClick={rebuild}>
            {busy ? 'Working…' : 'Rebuild'}
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}

      <label className="checkbox-row">
        <input type="checkbox" checked={clueListOnly} onChange={(e) => setClueListOnly(e.target.checked)} />
        Clue list only
      </label>

      {clueListOnly ? (
        <div className="editor-body clue-mode">
          <div className="grid-pane">
            <GridView puzzle={puzzle} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
          <div className="clue-scroll">
            {[['Across', 'across'], ['Down', 'down']].map(([label, dir]) => (
              <section key={dir}>
                <h2>{label}</h2>
                <ul className="clue-only-list">
                  {puzzle.entries.filter((e) => e.direction === dir).map((e) => (
                    <li key={e.id} className={selectedId === e.id ? 'hl' : ''}
                        onClick={() => setSelectedId(e.id)}>
                      <b>{e.humanNumber}.</b>
                      <AutoTextarea
                        className="clue-input inline"
                        value={e.clue || ''}
                        placeholder={`Clue (${e.length})`}
                        onChange={(ev) => setEntryField(e.id, 'clue', ev.target.value)}
                      />
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      ) : (
        <div className="editor-body">
          <div className="grid-pane">
            <GridView puzzle={puzzle} selectedId={selectedId} onSelect={setSelectedId} />
          </div>
          <div className="word-pane">
            {!selected ? (
              <p className="muted hint">Tap a word in the grid to edit its clue or swap it out.
                Tap a crossing square again to switch between across and down.</p>
            ) : (
              <div className="word-panel">
                <div className="word-panel-head">
                  <h2>{selected.humanNumber} {selected.direction}</h2>
                  <span className="answer big">{selected.solution}</span>
                  <span className="muted">({selected.length})</span>
                  {selected.locked && <span className="lock-badge">locked</span>}
                </div>
                {clueFields(selected)}
                <div className="entry-actions">
                  {busy ? <span className="muted">Redesigning…</span> : selected.locked ? (
                    <>
                      <button className="btn sm" onClick={() => setEntryField(selected.id, 'locked', false)}>Unlock</button>
                      <span className="muted">Locked words are kept during redesigns.</span>
                    </>
                  ) : (
                    <>
                      <button className="btn sm" onClick={() => setEntryField(selected.id, 'locked', true)}>Lock</button>
                      <button className="btn sm" onClick={() => reject(selected, false)}>Reject</button>
                      <button className="btn sm" onClick={() => reject(selected, true)}>Reject + ban</button>
                      <button className="btn sm" onClick={() => { setReplacing(!replacing); setReplacement('') }}>Replace…</button>
                    </>
                  )}
                </div>
                {replacing && !busy && (() => {
                  const cross = crossLetters(puzzle, selected)
                  const typed = replacement.replace(/[^A-Z]/g, '')
                  const remaining = selected.length - typed.length
                  const reshuffles = typed.split('').some((ch, i) => cross[i] && cross[i] !== ch)
                  return (
                    <>
                      <div className="replace-row">
                        <input
                          value={replacement}
                          maxLength={selected.length}
                          placeholder={`${selected.length} letters`}
                          onChange={(ev) => setReplacement(ev.target.value.toUpperCase().replace(/[^A-Z]/g, ''))}
                        />
                        <button className="btn sm primary"
                                disabled={typed.length !== selected.length}
                                onClick={() => reject(selected, false, typed)}>Go</button>
                      </div>
                      <div className="replace-meta">
                        {remaining > 0
                          ? <span className="muted">{remaining} letter{remaining === 1 ? '' : 's'} left</span>
                          : <span className="ok">✓ correct length</span>}
                        {reshuffles && (
                          <span className="warn">⚠ changes crossing letters — part of the puzzle will be reshuffled</span>
                        )}
                      </div>
                    </>
                  )
                })()}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
