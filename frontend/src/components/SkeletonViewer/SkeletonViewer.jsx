import { useRef, useState, useEffect, useCallback } from 'react'
import { useVideoSync } from './hooks/useVideoSync.js'
import style from './SkeletonViewer.module.css'

export default function SkeletonViewer({
    videoFile,
    skeletonData,
    vizConfig,
    barPlacementMode,
    status,
    jobProgress,
    errorMessage,
}) {
    const videoRef = useRef(null)
    const canvasRef = useRef(null)
    const viewportRef = useRef(null)

    const [videoURL, setVideoURL] = useState(null)
    const [isPlaying, setIsPlaying] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [canvasReady, setCanvasReady] = useState(false)
    const [skeletonHidden, setSkeletonHidden] = useState(false)
    const [canvasStyle, setCanvasStyle] = useState({ top: 0, left: 0, width: '100%', height: '100%' })

    const updateCanvasRect = useCallback(() => {
        const video = videoRef.current
        const viewport = viewportRef.current
        if (!video || !viewport || !video.videoWidth || !video.videoHeight) return

        const containerW = viewport.clientWidth
        const containerH = viewport.clientHeight
        const videoAspect = video.videoWidth / video.videoHeight
        const containerAspect = containerW / containerH

        let renderedW, renderedH
        if (videoAspect > containerAspect) {
            renderedW = containerW
            renderedH = containerW / videoAspect
        } else {
            renderedH = containerH
            renderedW = containerH * videoAspect
        }

        setCanvasStyle({
            top: (containerH - renderedH) / 2,
            left: (containerW - renderedW) / 2,
            width: renderedW,
            height: renderedH,
        })
    }, [])

    useEffect(() => {
        const viewport = viewportRef.current
        if (!viewport) return
        const ro = new ResizeObserver(updateCanvasRect)
        ro.observe(viewport)
        return () => ro.disconnect()
    }, [updateCanvasRect])

    useEffect(() => {
        if (!videoFile) {
            setVideoURL(null)
            return
        }

        const url = URL.createObjectURL(videoFile)
        setVideoURL(url)
        setIsPlaying(false)
        setCurrentTime(0)
        setDuration(0)
        setCanvasReady(false)

        return () => URL.revokeObjectURL(url)
    }, [videoFile])

    const handleLoadedMetadata = useCallback(() => {
        const video = videoRef.current
        const canvas = canvasRef.current
        if (!video || !canvas) return
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        setDuration(video.duration)
        setCanvasReady(true)
        updateCanvasRect()
    }, [updateCanvasRect])

    const mergedVizConfig = {
        ...vizConfig,
        showSkeleton: vizConfig?.showSkeleton && !skeletonHidden,
    }

    useVideoSync({
        videoRef,
        canvasRef,
        skeletonData: canvasReady ? skeletonData : null,
        vizConfig: mergedVizConfig,
        barPlacementMode,
    })

    function handleTimeUpdate() {
        setCurrentTime(videoRef.current?.currentTime ?? 0)
    }

    function handleVideoEnd() {
        setIsPlaying(false)
    }

    function togglePlay() {
        const video = videoRef.current
        if (!video) return

        if (video.paused) {
            video.play()
            setIsPlaying(true)
        } else {
            video.pause()
            setIsPlaying(false)
        }
    }

    function handleScrub(event) {
        const time = parseFloat(event.target.value)
        if (videoRef.current) {
            videoRef.current.currentTime = time
        }
        setCurrentTime(time)
    }

    const isDone = status === 'completed'
    const isLoading = ['uploading', 'queued', 'extracting', 'analyzing', 'generating_feedback'].includes(status)
    const frameIndex = skeletonData?.frames?.length
        ? Math.min(Math.round(currentTime * skeletonData.fps), skeletonData.frames.length - 1)
        : 0
    const totalFrames = skeletonData?.frames?.length ?? 0
    const durationMs = skeletonData?.durationMs ?? (duration * 1000)
    const currentTimestampMs = currentTime * 1000

    const repBoundaries = vizConfig.showRepBoundaries
        ? (skeletonData?.repSegments ?? []).flatMap((segment, index) => ([
            {
                id: `rep-start-${index}`,
                label: `Rep ${segment.repIndex ?? index + 1} start`,
                position: durationMs > 0 ? (segment.startMs / durationMs) * 100 : 0,
                type: 'rep',
            },
            {
                id: `rep-bottom-${index}`,
                label: `Rep ${segment.repIndex ?? index + 1} bottom`,
                position: durationMs > 0 ? (segment.bottomMs / durationMs) * 100 : 0,
                type: 'repBottom',
            },
        ]))
        : []

    const timelineMarkers = (skeletonData?.timelineMarkers ?? []).filter(marker => {
        if (marker.kind === 'issue' && !vizConfig.showIssueMarkers) return false
        if (marker.kind === 'event' && !vizConfig.showEventMarkers) return false
        return true
    })

    const activeMarkers = timelineMarkers.filter(marker => Math.abs(marker.timestampMs - currentTimestampMs) < 500)

    return (
        <div className={style.container}>
            <div className={style.viewport} ref={viewportRef}>
                {isDone && (
                    <div className={style.frameInfoOverlay}>
                        FRAME: {String(frameIndex + 1).padStart(4, '0')} / {String(totalFrames).padStart(4, '0')}
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
                            {jobProgress?.stage ? `${jobProgress.stage}...` : 'Analyzing...'}
                        </p>
                    </div>
                ) : status === 'error' ? (
                    <div className={style.stateOverlay}>
                        <p className={`${style.stateText} ${style.errorText}`}>
                            {errorMessage || 'Analysis failed. Please try again.'}
                        </p>
                    </div>
                ) : (
                    <div className={style.stateOverlay}>
                        <div className={style.placeholderIcon}>
                            <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                                <circle cx="24" cy="24" r="23" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5"/>
                                <path d="M19 16l14 8-14 8V16z" fill="rgba(255,255,255,0.3)"/>
                            </svg>
                        </div>
                        <p className={style.stateText}>Upload a video to begin</p>
                        <p className={style.stateSubText}>Results will appear here after analysis</p>
                    </div>
                )}
            </div>

            <div className={style.controls}>
                <div className={style.controlMeta}>
                    <span className={style.timelineLabel}>TIMELINE CONTROL</span>
                    {isDone && <span className={style.analysisActive}>ANALYSIS ACTIVE</span>}
                </div>
                <div className={style.controlMain}>
                    <div className={style.timelineBarWrap}>
                        <input
                            type="range"
                            className={style.scrubber}
                            min={0}
                            max={duration || 1}
                            step={skeletonData ? 1 / skeletonData.fps : 0.033}
                            value={currentTime}
                            onChange={handleScrub}
                            disabled={!isDone}
                            style={{ '--progress': duration ? `${(currentTime / duration) * 100}%` : '0%' }}
                        />
                        <div className={style.markerTrack}>
                            {repBoundaries.map(marker => (
                                <span
                                    key={marker.id}
                                    className={`${style.marker} ${marker.type === 'repBottom' ? style.markerBottom : style.markerRep}`}
                                    style={{ left: `${marker.position}%` }}
                                    title={marker.label}
                                />
                            ))}
                            {timelineMarkers.map(marker => (
                                <span
                                    key={marker.id}
                                    className={`${style.marker} ${marker.kind === 'issue' ? style.markerIssue : style.markerEvent}`}
                                    style={{ left: `${marker.position}%` }}
                                    title={marker.message ?? marker.label}
                                />
                            ))}
                        </div>
                    </div>
                    <div className={style.actionButtons}>
                        <button
                            className={`${style.actionBtn} ${!isPlaying ? style.actionBtnActive : ''}`}
                            onClick={togglePlay}
                            disabled={!isDone}
                        >
                            {isPlaying ? 'PAUSE' : 'PLAY'}
                        </button>
                        <button
                            className={`${style.actionBtn} ${style.actionBtnWide} ${skeletonHidden ? style.actionBtnActive : ''}`}
                            onClick={() => setSkeletonHidden(value => !value)}
                            disabled={!isDone}
                        >
                            {skeletonHidden ? 'SHOW SKELETON' : 'HIDE SKELETON'}
                        </button>
                    </div>
                </div>
                {(activeMarkers.length > 0 || jobProgress?.stage) && (
                    <div className={style.annotationBar}>
                        {jobProgress?.stage && !isDone && (
                            <span className={style.annotationChip}>
                                Stage: {jobProgress.stage}
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
        </div>
    )
}
