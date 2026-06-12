const BASE = '/api'

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* ignore */ }
    throw new Error(detail)
  }
  return res.json()
}

export const api = {
  listPuzzles: () => req('/puzzles'),
  createPuzzle: (body) => req('/puzzles', { method: 'POST', body: JSON.stringify(body) }),
  getPuzzle: (id) => req(`/puzzles/${id}`),
  updatePuzzle: (id, puzzle) => req(`/puzzles/${id}`, { method: 'PUT', body: JSON.stringify({ puzzle }) }),
  deletePuzzle: (id) => req(`/puzzles/${id}`, { method: 'DELETE' }),
  rejectWord: (id, body) => req(`/puzzles/${id}/reject-word`, { method: 'POST', body: JSON.stringify(body) }),
  rebuild: (id) => req(`/puzzles/${id}/rebuild`, { method: 'POST' }),
  getBanList: () => req('/ban-list'),
  addBanWord: (word) => req('/ban-list', { method: 'POST', body: JSON.stringify({ word }) }),
  removeBanWord: (word) => req(`/ban-list/${encodeURIComponent(word)}`, { method: 'DELETE' }),
  exportJsonUrl: (id) => `${BASE}/puzzles/${id}/export/json`,
  exportPdfUrl: (id) => `${BASE}/puzzles/${id}/export/pdf`,
}
