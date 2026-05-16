import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import 'pretendard/dist/web/static/pretendard-subset.css'
import './Styles/reset.css'
import './Styles/main.css'


createRoot(document.getElementById('root')).render(
    <StrictMode>
        <App />
    </StrictMode>,
)
