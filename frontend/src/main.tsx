import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import App from './App.tsx'
import { AuthProvider } from './contexts/AuthContext.tsx'
import { installAuthFetchInterceptor } from './services/api.ts'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

installAuthFetchInterceptor()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ConfigProvider locale={zhCN}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ConfigProvider>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

