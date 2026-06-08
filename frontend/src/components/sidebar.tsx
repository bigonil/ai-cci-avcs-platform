// frontend/src/components/sidebar.tsx
import { NavLink } from 'react-router-dom'
import type { ReactNode } from 'react'
import { LayoutDashboard, AlertTriangle, ClipboardList, ShieldCheck } from 'lucide-react'

interface NavItem {
  path: string
  label: string
  icon: ReactNode
  badge?: number
  badgeColor?: string
}

const NAV_ITEMS: NavItem[] = [
  { path: '/', label: 'Dashboard', icon: <LayoutDashboard size={15} /> },
  {
    path: '/incoherences',
    label: 'Incoerenze',
    icon: <AlertTriangle size={15} />,
    badge: undefined,
    badgeColor: 'rgba(239,68,68,.2)',
  },
  {
    path: '/hitl',
    label: 'Coda HITL',
    icon: <ClipboardList size={15} />,
    badge: undefined,
    badgeColor: 'rgba(234,179,8,.15)',
  },
  { path: '/audit', label: 'Audit Trail', icon: <ShieldCheck size={15} /> },
]

export function Sidebar() {
  return (
    <aside
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--sidebar-bg)',
        borderRight: '1px solid var(--sidebar-border)',
        backdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        height: '100vh',
      }}
    >
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid rgba(129,140,248,0.1)', display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 32, height: 32, background: 'linear-gradient(135deg, #818cf8, #a78bfa)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, boxShadow: '0 0 20px rgba(129,140,248,0.3)', flexShrink: 0 }}>
          ⚡
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#f1f5f9', letterSpacing: '0.3px' }}>CCI / AVCS</div>
          <div style={{ fontSize: 9, color: 'rgba(165,180,252,0.5)', letterSpacing: '1px', textTransform: 'uppercase', marginTop: 1 }}>Coherence Engine</div>
        </div>
      </div>

      {/* Status */}
      <div style={{ margin: '12px 16px 0' }}>
        <div style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 6, padding: '6px 10px', display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'rgba(74,222,128,0.9)' }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', boxShadow: '0 0 8px #22c55e', animation: 'pulse 2s infinite' }} />
          Sistema operativo
        </div>
      </div>

      {/* Nav */}
      <nav aria-label="Navigazione principale" style={{ padding: '16px 8px 0', flex: 1 }}>
        <div style={{ fontSize: 9, color: 'var(--text-dim)', letterSpacing: '1.5px', textTransform: 'uppercase', padding: '0 8px 6px' }}>Navigazione</div>
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 13,
              fontWeight: 500,
              color: isActive ? '#a5b4fc' : 'var(--text-secondary)',
              background: isActive ? 'rgba(129,140,248,0.15)' : 'transparent',
              boxShadow: isActive ? 'inset 3px 0 0 #818cf8' : 'none',
              textDecoration: 'none',
              marginBottom: 2,
              transition: 'all 0.15s',
            })}
          >
            {item.icon}
            <span style={{ flex: 1 }}>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid rgba(129,140,248,0.1)', fontSize: 9, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>v0.1.0 · hera_it</span>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.5} }
      `}</style>
    </aside>
  )
}
