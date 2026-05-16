import { useRef, useState, useEffect, useCallback } from 'react'
import { useVideoSync } from '../../SkeletonViewer/hooks/useVideoSync.js'
import style from './LiveViewPanel.module.css'

export default function LiveViewPanel({
    videoFile,
    skeletonData,
    vizConfig,
    barPlacementMode,
    status,
    jobProgress,
    errorMessage,
    isPlaying,
    seekTarget,
    onTimeUpdate,
    onEnded,
}) {
    const videoRef = useRef(null)
    const canvasRef = useRef(null)
    const viewportRef = useRef(null)

    const [videoURL, setVideoURL] = useState(null)
    const [currentTime, setCurrentTime] = useState(0)
    const [canvasReady, setCanvasReady] = useState(false)
    const [canvasStyle, setCanvasStyle] = useState({ top: 0, left: 0, width: '100%', height: '100%' })

    const updateCanvasRect = useCallback(() => {
        const video = videoRef.current
        const viewport = viewportRef.current
        if (!video || !viewport || !video.videoWidth || !video.videoHeight) return

        const cW = viewport.clientWidth
        const cH = viewport.clientHeight
        const vAspect = video.videoWidth / video.videoHeight
        const cAspect = cW / cH

        let rW, rH
        if (vAspect > cAspect) {
            rW = cW; rH = cW / vAspect
        } else {
            rH = cH; rW = cH * vAspect
        }
        setCanvasStyle({ top: (cH - rH) / 2, left: (cW - rW) / 2, width: rW, height: rH })
    }, [])

    useEffect(() => {
        const viewport = viewportRef.current
        if (!viewport) return
        const ro = new ResizeObserver(updateCanvasRect)
        ro.observe(viewport)
        return () => ro.disconnect()
    }, [updateCanvasRect])

    useEffect(() => {
        if (!videoFile) { setVideoURL(null); return }
        const url = URL.createObjectURL(videoFile)
        setVideoURL(url)
        setCurrentTime(0)
        setCanvasReady(false)
        return () => URL.revokeObjectURL(url)
    }, [videoFile])

    const handleLoadedMetadata = useCallback(() => {
        const video = videoRef.current
        const canvas = canvasRef.current
        if (!video || !canvas) return
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        setCanvasReady(true)
        updateCanvasRect()
        onTimeUpdate?.(0, video.duration)
    }, [updateCanvasRect, onTimeUpdate])

    // External play control
    const isDone = status === 'completed'
    useEffect(() => {
        const video = videoRef.current
        if (!video || !isDone || isPlaying === undefined) return
        if (isPlaying) {
            video.play().catch(() => {})
        } else {
            video.pause()
        }
    }, [isPlaying, isDone])

    // External seek
    useEffect(() => {
        const video = videoRef.current
        if (!video || !seekTarget) return
        video.currentTime = seekTarget.time
        setCurrentTime(seekTarget.time)
    }, [seekTarget])

    function handleTimeUpdate() {
        const t = videoRef.current?.currentTime ?? 0
        const d = videoRef.current?.duration ?? 0
        setCurrentTime(t)
        onTimeUpdate?.(t, d)
    }

    function handleVideoEnd() {
        onEnded?.()
    }

    useVideoSync({
        videoRef,
        canvasRef,
        skeletonData: canvasReady ? skeletonData : null,
        vizConfig,
        barPlacementMode,
    })

    const isLoading = ['uploading', 'queued', 'extracting', 'analyzing', 'generating_feedback'].includes(status)
    const frameIndex = skeletonData?.frames?.length
        ? Math.min(Math.round(currentTime * skeletonData.fps), skeletonData.frames.length - 1)
        : 0
    const totalFrames = skeletonData?.frames?.length ?? 0
    const currentTimestampMs = currentTime * 1000

    const activeMarkers = (skeletonData?.timelineMarkers ?? []).filter(marker => {
        if (marker.kind === 'issue' && !vizConfig?.showIssueMarkers) return false
        if (marker.kind === 'event' && !vizConfig?.showEventMarkers) return false
        return Math.abs(marker.timestampMs - currentTimestampMs) < 500
    })

    return (
        <div className={style.viewport} ref={viewportRef}>
            {isDone && (
                <div className={style.frameOverlay}>
                    {String(frameIndex + 1).padStart(4, '0')} / {String(totalFrames).padStart(4, '0')}
                </div>
            )}

            {isDone && videoURL ? (
                <>
                    <video
                        ref={videoRef}
                        src={videoURL}
                        className={style.video}
                        onLoadedMetadata={handleLoadedMetadata}
                        onTimeUpdate={handleTimeUpdate}
                        onEnded={handleVideoEnd}
                        playsInline
                        muted
                    />
                    <canvas ref={canvasRef} className={style.canvas} style={canvasStyle} />
                </>
            ) : isLoading ? (
                <div className={style.stateOverlay}>
                    <div className={style.spinner} />
                    <p className={style.stateText}>
                        {jobProgress?.stage ? `${jobProgress.stage}…` : 'Analyzing…'}
                    </p>
                </div>
            ) : status === 'error' ? (
                <div className={style.stateOverlay}>
                    <p className={`${style.stateText} ${style.errorText}`}>
                        {errorMessage || 'Analysis failed.'}
                    </p>
                </div>
            ) : (
                <div className={style.stateOverlay}>
                    <div className={style.placeholderIcon}>
                        <svg width="40" height="40" viewBox="0 0 48 48" fill="none">
                            <circle cx="24" cy="24" r="23" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5"/>
                            <path d="M19 16l14 8-14 8V16z" fill="rgba(255,255,255,0.25)"/>
                        </svg>
                    </div>
                    <p className={style.stateText}>Upload a video to begin</p>
                </div>
            )}

            {(activeMarkers.length > 0 || (jobProgress?.stage && !isDone)) && (
                <div className={style.annotationOverlay}>
                    {jobProgress?.stage && !isDone && (
                        <span className={style.annotationChip}>
                            {jobProgress.stage}
                        </span>
                    )}
                    {activeMarkers.map(marker => (
                        <span
                            key={marker.id}
                            className={`${style.annotationChip} ${marker.kind === 'issue' ? style.annotationIssue : ''}`}
                        >
                            {marker.label}
                        </span>
                    ))}
                </div>
            )}
        </div>
    )
}
