import { NavLink } from 'react-router-dom'

/**
 * Three plain links. The backend/LLM status lives in the footer - ordinary
 * users do not need it in their face.
 */

const LINKS = [
  { to: '/', label: 'Find my schemes', end: true },
  { to: '/schemes', label: 'All schemes' },
  { to: '/ask', label: 'Ask a question' },
]

export default function Navbar({ backendDown }) {
  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <NavLink to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            GS
          </span>
          <span>Scheme Assistant</span>
        </NavLink>

        <nav className="nav-links">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        {backendDown && <span className="status-pill warn">Backend offline</span>}
      </div>
    </header>
  )
}