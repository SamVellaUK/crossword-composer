import React from 'react'

export default function GridView({ puzzle, selectedId, onSelect, showLetters = true }) {
  const { cols, rows } = puzzle.dimensions
  const cells = {}
  const numbers = {}
  const entriesAt = {}
  const selectedCells = new Set()
  const lockedCells = new Set()

  for (const e of puzzle.entries) {
    const { x, y } = e.position
    if (!(`${y},${x}` in numbers)) numbers[`${y},${x}`] = e.humanNumber
    for (let i = 0; i < e.length; i++) {
      const cy = y + (e.direction === 'down' ? i : 0)
      const cx = x + (e.direction === 'across' ? i : 0)
      const key = `${cy},${cx}`
      cells[key] = e.solution[i] || ''
      ;(entriesAt[key] = entriesAt[key] || []).push(e.id)
      if (selectedId === e.id) selectedCells.add(key)
      if (e.locked) lockedCells.add(key)
    }
  }

  const clickCell = (key) => {
    const ids = entriesAt[key]
    if (!ids || !onSelect) return
    // tap again on a crossing cell to switch between across/down
    const idx = ids.indexOf(selectedId)
    onSelect(idx >= 0 ? ids[(idx + 1) % ids.length] : ids[0])
  }

  return (
    <div className="grid" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)`, '--cols': cols }}>
      {Array.from({ length: rows * cols }, (_, i) => {
        const r = Math.floor(i / cols), c = i % cols
        const key = `${r},${c}`
        const letter = cells[key]
        if (letter === undefined) return <div key={key} className="cell black" />
        return (
          <div key={key}
               className={`cell white${lockedCells.has(key) ? ' locked' : ''}${selectedCells.has(key) ? ' hl' : ''}`}
               onClick={() => clickCell(key)}>
            {numbers[key] && <span className="num">{numbers[key]}</span>}
            {showLetters && <span className="letter">{letter}</span>}
          </div>
        )
      })}
    </div>
  )
}
