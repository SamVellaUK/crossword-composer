import React, { useEffect, useState } from 'react'
import Dashboard from './components/Dashboard.jsx'
import Editor from './components/Editor.jsx'
import BanList from './components/BanList.jsx'

function parseHash() {
  const h = window.location.hash.replace(/^#\/?/, '')
  if (h.startsWith('puzzle/')) return { page: 'puzzle', id: h.slice(7) }
  if (h === 'settings') return { page: 'settings' }
  return { page: 'home' }
}

export default function App() {
  const [route, setRoute] = useState(parseHash())

  useEffect(() => {
    const onHash = () => setRoute(parseHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <div className="app">
      <header className="topbar">
        <a href="#/" className="brand">Crossword Composer</a>
        <nav>
          <a href="#/" className={route.page === 'home' ? 'active' : ''}>Puzzles</a>
          <a href="#/settings" className={route.page === 'settings' ? 'active' : ''}>Ban list</a>
        </nav>
      </header>
      <main>
        {route.page === 'home' && <Dashboard />}
        {route.page === 'puzzle' && <Editor puzzleId={route.id} />}
        {route.page === 'settings' && <BanList />}
      </main>
    </div>
  )
}
