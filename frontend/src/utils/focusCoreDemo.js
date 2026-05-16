export function focusCoreDemo() {
    const section = document.getElementById('coreDemo')
    const panel = document.getElementById('analysisSettingsPanel')

    if (section) {
        const sectionTop = window.scrollY + section.getBoundingClientRect().top

        window.scrollTo({
            top: Math.max(0, sectionTop),
            behavior: 'smooth',
        })
    }

    if (panel) {
        panel.focus({ preventScroll: true })
    }

    const upload = document.getElementById('uploadAreaTarget')
    if (upload) {
        upload.classList.remove('upload-impulse')
        void upload.offsetWidth
        upload.classList.add('upload-impulse')
        upload.addEventListener('animationend', () => upload.classList.remove('upload-impulse'), { once: true })
    }
}
