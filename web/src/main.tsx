import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.tsx'
import './index.css'

// Painel de auditoria: dados sempre frescos, polling contínuo mesmo em segundo
// plano (o telão da demo não pode congelar quando ninguém está com foco na aba).
const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 0, refetchIntervalInBackground: true, retry: 1 },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
