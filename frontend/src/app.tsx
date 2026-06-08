// frontend/src/app.tsx
import { Outlet } from 'react-router-dom'
import { Sidebar } from './components/sidebar'

export function App() {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      <Sidebar />
      <main style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
        <Outlet />
      </main>
    </div>
  )
}
