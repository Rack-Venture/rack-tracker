import { useEffect, useRef } from 'react'
import { computeJointLoad } from '../utils/computeJointLoad.js'
import { drawAngles, drawBarPass, drawBarPassDot, drawBarPassSegment, drawCoP, drawEventMarkers, drawGroundVector, drawIssueMarkers, drawJointLoad, drawPathTrace, drawRepOverlay, drawSkeleton } from '../utils/drawSkeleton.js'

export function useVideoSync({ videoRef, canvasRef, skeletonData, vizConfig, barPlacementMode }) {
    const rafRef = useRef(null)
    const vizConfigRef = useRef(vizConfig)
    const barPlacementModeRef = useRef(barPlacementMode)

    // 오프스크린 캔버스 — bar pass 누적 드로잉용
    const barTrailCanvasRef = useRef(null)
    const lastBarFrameIndexRef = useRef(-1)

    useEffect(() => {
        vizConfigRef.current = vizConfig
    }, [vizConfig])

    useEffect(() => {
        barPlacementModeRef.current = barPlacementMode
    }, [barPlacementMode])

    useEffect(() => {
        const video = videoRef.current
        const canvas = canvasRef.current
        if (!video || !canvas || !skeletonData) return

        const fps = skeletonData.fps
        const frames = skeletonData.frames

        // skeletonData 교체 시 오프스크린 캔버스 초기화
        const trailCanvas = document.createElement('canvas')
        trailCanvas.width = canvas.width
        trailCanvas.height = canvas.height
        barTrailCanvasRef.current = trailCanvas
        lastBarFrameIndexRef.current = -1

        function renderFrame() {
            const ctx = canvas.getContext('2d')
            const config = vizConfigRef.current
            const currentTimeMs = video.currentTime * 1000
            const frameIndex = Math.min(
                Math.round(video.currentTime * fps),
                frames.length - 1
            )
            const frame = frames[frameIndex]
            const metrics = skeletonData.frameMetricsByIndex?.[frameIndex] ?? null
            const needsTrail = config.showPathTrace || config.showCoP
            const trail = needsTrail
                ? frames.slice(Math.max(0, frameIndex - 30), frameIndex + 1)
                : null

            // ── Bar pass 오프스크린 누적 ──────────────────────────────
            if (config.showBarPass) {
                const trailCtx = barTrailCanvasRef.current?.getContext('2d')
                const lastIdx = lastBarFrameIndexRef.current
                const w = canvas.width
                const h = canvas.height
                const placement = barPlacementModeRef.current

                if (trailCtx) {
                    if (frameIndex < lastIdx) {
                        // 뒤로 스크럽: 전체 재드로잉
                        trailCtx.clearRect(0, 0, w, h)
                        drawBarPass(trailCtx, frames, frameIndex, w, h, placement)
                    } else if (frameIndex > lastIdx) {
                        // 앞으로 진행: 새 구간만 누적
                        const segFrom = lastIdx < 0 ? 0 : lastIdx
                        drawBarPassSegment(trailCtx, frames, segFrom, frameIndex, w, h, placement)
                    }
                    lastBarFrameIndexRef.current = frameIndex
                }
            }
            // ─────────────────────────────────────────────────────────

            ctx.clearRect(0, 0, canvas.width, canvas.height)

            // 오프스크린 trail 합성
            if (config.showBarPass && barTrailCanvasRef.current) {
                ctx.drawImage(barTrailCanvasRef.current, 0, 0)
            }

            if (frame?.landmarks) {
                if (config.showPathTrace && trail?.length) {
                    drawPathTrace(ctx, trail, canvas.width, canvas.height)
                }
                if (config.showGroundVector) {
                    drawGroundVector(ctx, frame.landmarks, canvas.width, canvas.height)
                }
                if (config.showCoP && trail?.length) {
                    drawCoP(ctx, trail, canvas.width, canvas.height)
                }
                if (config.showBarPass) {
                    drawBarPassDot(ctx, frame, canvas.width, canvas.height, barPlacementModeRef.current)
                }
                if (config.showSkeleton) {
                    drawSkeleton(ctx, frame.landmarks, canvas.width, canvas.height, {
                        showJointLabels: config.showJointLabels,
                        showConfidenceTint: config.showConfidenceTint,
                    })
                }
                if (config.showAngleOverlay && metrics?.jointAngles) {
                    drawAngles(ctx, frame.landmarks, metrics.jointAngles, canvas.width, canvas.height)
                }
                if (config.showJointLoad && metrics?.jointAngles) {
                    const jointLoad = computeJointLoad(metrics.jointAngles)
                    drawJointLoad(ctx, frame.landmarks, jointLoad, canvas.width, canvas.height)
                }
            }

            const MARKER_WINDOW_MS = 600
            const markers = skeletonData.timelineMarkers ?? []

            if (config.showIssueMarkers) {
                const activeIssues = markers.filter(
                    m => m.kind === 'issue' && Math.abs(m.timestampMs - currentTimeMs) < MARKER_WINDOW_MS
                )
                if (activeIssues.length) {
                    drawIssueMarkers(ctx, activeIssues, canvas.width, canvas.height)
                }
            }

            if (config.showEventMarkers) {
                const activeEvents = markers.filter(
                    m => m.kind === 'event' && Math.abs(m.timestampMs - currentTimeMs) < MARKER_WINDOW_MS
                )
                if (activeEvents.length) {
                    drawEventMarkers(ctx, activeEvents, canvas.width, canvas.height)
                }
            }

            if (config.showRepBoundaries && skeletonData.repSegments?.length) {
                const segments = skeletonData.repSegments
                const totalReps = segments.length
                let repShown = false
                for (let i = 0; i < segments.length; i++) {
                    const seg = segments[i]
                    const endMs = segments[i + 1]?.startMs ?? seg.endMs ?? Infinity
                    if (currentTimeMs >= seg.startMs && currentTimeMs < endMs) {
                        const phase = seg.bottomMs != null && currentTimeMs >= seg.bottomMs
                            ? 'ascent'
                            : 'descent'
                        drawRepOverlay(ctx, i, totalReps, phase, canvas.width, canvas.height)
                        repShown = true
                        break
                    }
                }
                if (!repShown) {
                    const lastSeg = segments[totalReps - 1]
                    if (lastSeg.endMs != null && currentTimeMs >= lastSeg.endMs) {
                        drawRepOverlay(ctx, totalReps, totalReps, 'ascent', canvas.width, canvas.height)
                    }
                }
            }

            if (!video.paused && !video.ended) {
                rafRef.current = requestAnimationFrame(renderFrame)
            }
        }

        function startRenderLoop() {
            if (rafRef.current) return
            rafRef.current = requestAnimationFrame(() => {
                rafRef.current = null
                renderFrame()
            })
        }

        function renderOnce() {
            if (rafRef.current) {
                cancelAnimationFrame(rafRef.current)
                rafRef.current = null
            }
            renderFrame()
        }

        renderOnce()
        video.addEventListener('play', startRenderLoop)
        video.addEventListener('timeupdate', renderOnce)
        video.addEventListener('seeked', renderOnce)
        video.addEventListener('loadeddata', renderOnce)
        video.addEventListener('pause', renderOnce)
        video.addEventListener('ended', renderOnce)

        return () => {
            if (rafRef.current) {
                cancelAnimationFrame(rafRef.current)
                rafRef.current = null
            }
            video.removeEventListener('play', startRenderLoop)
            video.removeEventListener('timeupdate', renderOnce)
            video.removeEventListener('seeked', renderOnce)
            video.removeEventListener('loadeddata', renderOnce)
            video.removeEventListener('pause', renderOnce)
            video.removeEventListener('ended', renderOnce)
            lastBarFrameIndexRef.current = -1
        }
    }, [videoRef, canvasRef, skeletonData])
}
