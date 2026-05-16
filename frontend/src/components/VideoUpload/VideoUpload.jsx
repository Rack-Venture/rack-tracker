import { useState, useEffect } from 'react'
import style from './VideoUpload.module.css'

function formatDuration(seconds) {
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${String(s).padStart(2, '0')}`
}

function detectVideoMeta(file) {
    return new Promise((resolve) => {
        const url = URL.createObjectURL(file)
        const video = document.createElement('video')
        video.preload = 'metadata'
        video.muted = true
        video.src = url

        video.addEventListener('error', () => {
            URL.revokeObjectURL(url)
            resolve({ duration: null, fps: null })
        })

        video.addEventListener('loadedmetadata', () => {
            const duration = video.duration

            if (!video.requestVideoFrameCallback) {
                URL.revokeObjectURL(url)
                resolve({ duration, fps: null })
                return
            }

            const times = []
            function onFrame(_, meta) {
                times.push(meta.mediaTime)
                if (times.length < 8) {
                    video.requestVideoFrameCallback(onFrame)
                } else {
                    video.pause()
                    const intervals = times.slice(1).map((t, i) => t - times[i])
                    const avg = intervals.reduce((a, b) => a + b) / intervals.length
                    const fps = Math.round(1 / avg)
                    URL.revokeObjectURL(url)
                    resolve({ duration, fps: fps >= 1 && fps <= 300 ? fps : null })
                }
            }

            video.requestVideoFrameCallback(onFrame)
            video.play().catch(() => {
                URL.revokeObjectURL(url)
                resolve({ duration, fps: null })
            })
        })
    })
}

/**
 * 동영상 파일 선택 영역 컴포넌트.
 *
 * @param {Object} props
 * @param {File|null} props.file - 현재 선택된 파일. null이면 안내 텍스트 표시.
 * @param {Function} [props.onFileSelect] - 파일 선택 시 File 객체를 인자로 호출.
 * @returns {JSX.Element}
 */
export default function VideoUpload({ file, onFileSelect }) {
    const [videoMeta, setVideoMeta] = useState(null)

    useEffect(() => {
        if (!file) {
            setVideoMeta(null)
            return
        }

        let cancelled = false
        setVideoMeta(null)

        detectVideoMeta(file).then((meta) => {
            if (!cancelled) setVideoMeta(meta)
        })

        return () => { cancelled = true }
    }, [file])

    function handleChange(e) {
        const selected = e.target.files[0]
        if (selected) onFileSelect?.(selected)
    }

    function handleDragOver(e) {
        e.preventDefault()
    }

    function handleDrop(e) {
        e.preventDefault()
        const dropped = e.dataTransfer.files[0]
        if (dropped) onFileSelect?.(dropped)
    }

    return (
        <label
            id="uploadAreaTarget"
            className={`${style.uploadArea} ${file ? style.selected : ''}`}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
        >
            <input
                type="file"
                accept="video/mp4,video/quicktime"
                className={style.input}
                onChange={handleChange}
            />
            {file ? (
                <svg className={style.icon} width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                    <path d="M7 16l7 7L25 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
            ) : (
                <svg className={style.icon} width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
                    <path d="M16 22V10M16 10L11 15M16 10L21 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M6 26h20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                </svg>
            )}
            <span className={style.label} title={file ? file.name : undefined}>
                {file ? file.name : 'Upload Workout Video'}
            </span>
            {file && videoMeta ? (
                <div className={style.meta}>
                    <span className={style.metaChip}>
                        {videoMeta.duration != null ? formatDuration(videoMeta.duration) : '--:--'}
                    </span>
                    <span className={style.metaChip}>
                        {videoMeta.fps != null ? `${videoMeta.fps} FPS` : '-- FPS'}
                    </span>
                </div>
            ) : (
                <span className={style.sub}>
                    {file ? 'Reading metadata...' : 'MP4, MOV (Max. 50MB)'}
                </span>
            )}
        </label>
    )
}
