import React, { useState } from 'react'
import { api } from '../api.js'

export default function NewPuzzleModal({ onClose }) {
  const [name, setName] = useState('')
  const [author, setAuthor] = useState('')
  const [size, setSize] = useState(13)
  const [words, setWords] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const create = async () => {
    setBusy(true)
    setError('')
    try {
      const wordList = words.split(/[\n,;]+/).map((w) => w.trim()).filter(Boolean)
      const res = await api.createPuzzle({ name: name || 'Untitled crossword', size: Number(size), words: wordList, author })
      if (res.unplacedWords.length || res.unrecognisedWords.length) {
        setResult(res)
      } else {
        window.location.hash = `#/puzzle/${res.puzzle.id}`
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {result ? (
          <>
            <h2>Puzzle created</h2>
            {result.unplacedWords.length > 0 && (
              <>
                <p>Some words could not be placed:</p>
                <ul>{result.unplacedWords.map((u) => <li key={u.word}><b>{u.word}</b> — {u.reason}</li>)}</ul>
              </>
            )}
            {result.unrecognisedWords.length > 0 && (
              <p className="muted">Not in the UKACD dictionary (included anyway where possible):{' '}
                {result.unrecognisedWords.join(', ')}</p>
            )}
            <div className="modal-actions">
              <button className="primary" onClick={() => { window.location.hash = `#/puzzle/${result.puzzle.id}` }}>
                Open puzzle
              </button>
            </div>
          </>
        ) : (
          <>
            <h2>New Puzzle</h2>
            <label>Title
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Cryptic No 1" />
            </label>
            <label>Author
              <input value={author} onChange={(e) => setAuthor(e.target.value)} placeholder="Setter name" />
            </label>
            <label>Grid size
              <select value={size} onChange={(e) => setSize(e.target.value)}>
                <option value={9}>9 × 9</option>
                <option value={11}>11 × 11</option>
                <option value={13}>13 × 13</option>
                <option value={15}>15 × 15</option>
              </select>
            </label>
            <label>Desired words (one per line or comma-separated)
              <textarea rows={5} value={words} onChange={(e) => setWords(e.target.value)} placeholder={'RATCHET\nEARWIG'} />
            </label>
            {error && <p className="error">{error}</p>}
            <div className="modal-actions">
              <button onClick={onClose} disabled={busy}>Cancel</button>
              <button className="primary" onClick={create} disabled={busy}>
                {busy ? 'Generating…' : 'Generate grid'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
