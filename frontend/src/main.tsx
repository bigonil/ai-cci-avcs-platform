// frontend/src/main.tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import './index.css'
import { App } from './app'
import { Dashboard } from './pages/dashboard'
import { Incoherences } from './pages/incoherences'
import { IncoherenceDetail } from './pages/incoherence-detail'
import { HitlQueue } from './pages/hitl-queue'
import { HitlAction } from './pages/hitl-action'
import { Audit } from './pages/audit'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'incoherences', element: <Incoherences /> },
      { path: 'incoherences/:id', element: <IncoherenceDetail /> },
      { path: 'hitl', element: <HitlQueue /> },
      { path: 'hitl/:actionId', element: <HitlAction /> },
      { path: 'audit', element: <Audit /> },
    ],
  },
])

const root = document.getElementById('root')
if (!root) throw new Error('Root element not found')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </StrictMode>
)
