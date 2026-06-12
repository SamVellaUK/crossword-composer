import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function BanList() {
  const [words, setWords] = useState([])
  const [newWord, setNewWord] = useState('')
  const [error, setError] = useState('')

  useEffect(() => { api.getBanList().then(setWords).catch((e) => setError(e.message)) }, [])

  const add = async () => {
    if (!newWord.trim()) return
    try {
      setWords(await api.addBanWord(newWord.trim()))
      setNewWord('')
      setError('')
    } catch (e) { setError(e.message) }
  }

  const remove = async (w) => {
    try { setWords(await api.removeBanWord(w)) } catch (e) { setError(e.message) }
  }

  return (
    <div className="page">
      <h1>Ban list</h1>
      <p className="muted">Banned words are never used by the grid generator, in any puzzle.</p>
      {error && <p className="error">{error}</p>}
      <div className="ban-add">
        <input value={newWord} placeholder="Word to ban"
               onChange={(e) => setNewWord(e.target.value.toUpperCase())}
               onKeyDown={(e) => e.key === 'Enter' && add()} />
        <button className="primary" onClick={add}>Ban word</button>
      </div>
      {words.length === 0 ? <p className="muted">No banned words.</p> : (
        <ul className="ban-list">
          {words.map((w) => (
            <li key={w}>{w} <button className="btn sm" onClick={() => remove(w)}>Remove</button></li>
          ))}
        </ul>
      )}
    </div>
  )
}
