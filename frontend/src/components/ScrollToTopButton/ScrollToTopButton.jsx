import { useEffect, useState } from 'react'
import style from './ScrollToTopButton.module.css'

export default function ScrollToTopButton() {
    const [visible, setVisible] = useState(false)

    useEffect(() => {
        const check = () => {
            const coreDemo = document.getElementById('coreDemo')
            if (!coreDemo) return
            setVisible(coreDemo.getBoundingClientRect().top < 0)
        }

        window.addEventListener('scroll', check, { passive: true })
        return () => window.removeEventListener('scroll', check)
    }, [])

    const handleClick = () => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
    }

    return (
        <button
            type="button"
            className={`${style.button} ${visible ? style.visible : ''}`}
            onClick={handleClick}
            aria-label="Scroll to top"
        >
            <svg
                className={style.icon}
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                aria-hidden="true"
            >
                <path
                    d="M12 19V5M5 12l7-7 7 7"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </svg>
        </button>
    )
}
