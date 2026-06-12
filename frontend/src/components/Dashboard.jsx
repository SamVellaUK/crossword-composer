import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import NewPuzzleModal from './NewPuzzleModal.jsx'

const STATUS_LABELS = {
  draft: 'Draft',
  complete: 'Complete',
  published: 'Published',
  // legacy values from earlier versions
  clues_complete: 'Complete',
  exported: 'Published',
}

export default function Dashboard() {
  const [puzzles, setPuzzles] = useState(null)
  const [showNew, setShowNew] = useState(false)
  const [error, setError] = useState('')

  const refresh = () => api.listPuzzles().then(setPuzzles).catch((e) => setError(e.message))
  useEffect(() => { refresh() }, [])

  const onDelete = async (p) => {
    if (!window.confirm(`Delete "${p.name}"? This cannot be undone.`)) return
    try { await api.deletePuzzle(p.id); refresh() } catch (e) { setError(e.message) }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Your puzzles</h1>
        <button className="primary" onClick={() => setShowNew(true)}>+ New Puzzle</button>
      </div>
      {error && <p className="error">{error}</p>}
      {puzzles === null ? <p className="muted">Loading…</p> : puzzles.length === 0 ? (
        <p className="muted">No puzzles yet. Create your first one.</p>
      ) : (
        <div className="cards">
          {puzzles.map((p) => (
            <div className="card" key={p.id}>
              <h3><a href={`#/puzzle/${p.id}`}>{p.name}</a></h3>
              <p className="meta">
                {p.cols}×{p.rows} · {p.word_count} words ·{' '}
                <span className={`status status-${p.status}`}>{STATUS_LABELS[p.status] || p.status}</span>
              </p>
              <p className="meta muted">Updated {new Date(p.updated_at).toLocaleString()}</p>
              <div className="card-actions">
                <a className="btn" href={`#/puzzle/${p.id}`}>Open</a>
                <a className="btn" href={api.exportJsonUrl(p.id)} download>JSON</a>
                <a className="btn" href={api.exportPdfUrl(p.id)} download>PDF</a>
                <button className="btn danger" onClick={() => onDelete(p)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {showNew && <NewPuzzleModal onClose={() => setShowNew(false)} />}
    </div>
  )
}
