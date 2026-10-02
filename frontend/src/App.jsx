import { useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar.jsx'
import Footer from './components/Footer.jsx'
import Find from './pages/Find.jsx'
import Browse from './pages/Browse.jsx'
import Chat from './pages/Chat.jsx'
import SchemeDetail from './pages/SchemeDetail.jsx'
import NotFound from './pages/NotFound.jsx'
import api from './api/client.js'

/**
 * App shell. The whole product is one page; the other routes exist so a user
 * can share a scheme link or jump straight to the search list.
 */
export default function App() {
  const [meta, setMeta] = useState(null)
  const [backendDown, setBackendDown] = useState(false)

  useEffect(() => {
    let active = true
    api
      .getMeta()
      .then((data) => active && setMeta(data))
      .catch(() => active && setBackendDown(true))
    return () => {
      active = false
    }
  }, [])

  return (
    <>
      <Navbar backendDown={backendDown} />

      {backendDown && (
        <div className="note note-warn container">
          <strong>We cannot reach the server.</strong> Start it with{' '}
          <code>uvicorn backend.main:app --reload --port 8000</code> and reload this page.
        </div>
      )}

      <Routes>
        <Route path="/" element={<Find disclaimer={meta?.disclaimer} />} />
        <Route path="/schemes" element={<Browse />} />
        <Route path="/ask" element={<Chat />} />
        <Route path="/schemes/:id" element={<SchemeDetail />} />
        {/* old links still work */}
        <Route path="/browse" element={<Navigate to="/schemes" replace />} />
        <Route path="/chat" element={<Navigate to="/ask" replace />} />
        <Route path="/profile" element={<Navigate to="/" replace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>

      <Footer meta={meta} />
    </>
  )
}