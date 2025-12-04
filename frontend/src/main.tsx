import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import ErrorBoundary from './ErrorBoundary.tsx'

console.log('✅ main.tsx is executing')

// 添加全局错误处理
window.addEventListener('error', (event) => {
  console.error('❌ Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('❌ Unhandled promise rejection:', event.reason);
});

const rootElement = document.getElementById('root');
console.log('✅ Root element found:', rootElement);

if (!rootElement) {
  throw new Error('Root element not found');
}

console.log('⏳ About to render App component...');

createRoot(rootElement).render(
  <StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)

console.log('✅ React app mounted successfully')
