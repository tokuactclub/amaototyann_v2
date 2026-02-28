import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

// Global styles
const style = document.createElement('style')
style.textContent = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', sans-serif; color: #333; line-height: 1.5; }
  input, textarea, select, button { font-family: inherit; }
`
document.head.appendChild(style)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
