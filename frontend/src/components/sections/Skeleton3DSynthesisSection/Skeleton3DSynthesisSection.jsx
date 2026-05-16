import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import {
    createStreamingSynthesisJob,
    getSynthesisJobStatus,
    getSynthesisResult,
    getSynthesisSkeleton3D,
} from '../../../api/analysisClient.js'
import { adaptSkeleton3DPage } from '../../../features/analysis-session/adapters.js'
import SectionContainer from '../../SectionContainer/SectionContainer.jsx'
import ThreeJSSkeleton from './ThreeJSSkeleton.jsx'
import style from './Skeleton3DSynthesisSection.module.css'

const KEY_JOINTS = [
    [0,  'Nose'],
    [11, 'L. Shoulder'],
    [12, 'R. Shoulder'],
    [13, 'L. Elbow'],
    [14, 'R. Elbow'],
    [23, 'L. Hip'],
    [24, 'R. Hip'],
    [25, 'L. Knee'],
    [26, 'R. Knee'],
    [27, 'L. Ankle'],
    [28, 'R. Ankle'],
]

function getFrame(skeleton, timeMs) {
    if (!skeleton?.frames?.length) return null
    const fps = skeleton.fps || 30
    const idx = Math.max(0, Math.min(
        Math.round((timeMs / 1000) * fps),
        skeleton.frames.length - 1,
    ))
    return skeleton.frames[idx] ?? null
}

function synthesizeFrames(fA, fB, f3D, mode) {
    if (mode === 'a-only') return fA ?? null
    if (mode === 'b-only') return fB ?? null
    return f3D ?? null
}

function inferCameraIdFromVideoInfo(videoInfo) {
    const candidates = [
        videoInfo?.cameraId,
        videoInfo?.cameraBinding?.sourceCameraId,
        videoInfo?.cameraBinding?.calibrationCameraId,
        videoInfo?.displayName,
        videoInfo?.videoSrc,
        videoInfo?.sourcePath,
    ].filter(Boolean)

    for (const candidate of candidates) {
        const match = String(candidate).match(/(?:^|[_\\/-])(\d{2}_\d{2})(?=[_.\\/-]|$)/)
        if (match?.[1]) return match[1]
    }

    return null
}

function sleep(ms, signal) {
    return new Promise((resolve, reject) => {
        const timeoutId = window.setTimeout(resolve, ms)
        signal?.addEventListener('abort', () => {
            window.clearTimeout(timeoutId)
            reject(new DOMException('Aborted', 'AbortError'))
        }, { once: true })
    })
}

function formatMs(ms) {
    if (!ms) return '0.0s'
    return `${(ms / 1000).toFixed(1)}s`
}

function formatVis(val) {
    if (val == null) return '—'
    return val.toFixed(2)
}

export default function Skeleton3DSynthesisSection({ sessionA, sessionB, synthesisSession = null, onSynthesisJobIdChange, onSynthesisProgressChange }) {
    const [currentTimeMs, setCurrentTimeMs] = useState(0)
    const [isPlaying, setIsPlaying] = useState(false)
    const [synthesisMode, setSynthesisMode] = useState('synthesized')
    const [cameraView, setCameraView] = useState('front')
    const [synthesisState, setSynthesisState] = useState({
        key: null,
        jobId: null,
        status: 'idle',
        progress: null,
        error: null,
        result: null,
        skeleton3D: null,
    })
    const synthesisAbortRef = useRef(null)
    const synthesisKeyRef = useRef(null)

    const externalSkeleton3D = useMemo(() => {
        if (!synthesisSession?.skeleton3d) return null
        return adaptSkeleton3DPage(synthesisSession.skeleton3d)
    }, [synthesisSession?.skeleton3d])

    useEffect(() => {
        if (!externalSkeleton3D) return
        setSynthesisState(prev => ({ ...prev, skeleton3D: externalSkeleton3D }))
    }, [externalSkeleton3D])

    const skeletonA = synthesisSession?.skeletonA ?? sessionA.skeletonPage
    const skeletonB = synthesisSession?.skeletonB ?? sessionB.skeletonPage
    const skeleton3D = synthesisState.skeleton3D
    const hasA = Boolean(skeletonA?.frames?.length)
    const hasB = Boolean(skeletonB?.frames?.length)
    const has3D = Boolean(skeleton3D?.frames?.length)
    const hasAny = has3D || hasA || hasB

    const durationMs = Math.max(
        has3D ? (skeleton3D.durationMs ?? 0) : 0,
        hasA ? (skeletonA.durationMs ?? (skeletonA.frames.length / (skeletonA.fps || 30) * 1000)) : 0,
        hasB ? (skeletonB.durationMs ?? (skeletonB.frames.length / (skeletonB.fps || 30) * 1000)) : 0,
    )

    const frameA = useMemo(() => getFrame(skeletonA, currentTimeMs), [skeletonA, currentTimeMs])
    const frameB = useMemo(() => getFrame(skeletonB, currentTimeMs), [skeletonB, currentTimeMs])
    const frame3D = useMemo(() => getFrame(skeleton3D, currentTimeMs), [skeleton3D, currentTimeMs])
    const synthFrame = useMemo(
        () => synthesizeFrames(frameA, frameB, frame3D, synthesisMode),
        [frameA, frameB, frame3D, synthesisMode],
    )

    const animRef = useRef(null)
    const lastTsRef = useRef(null)

    const stopPlayback = useCallback(() => {
        setIsPlaying(false)
        if (animRef.current) cancelAnimationFrame(animRef.current)
        lastTsRef.current = null
    }, [])

    useEffect(() => {
        const videoPathA = sessionA.videoPath
        const videoPathB = sessionB.videoPath
        if (!videoPathA || !videoPathB) {
            return undefined
        }
        if (synthesisSession?.jobId) return undefined

        const cameraIdA = inferCameraIdFromVideoInfo({ videoSrc: videoPathA }) ?? '00_21'
        const cameraIdB = inferCameraIdFromVideoInfo({ videoSrc: videoPathB }) ?? '00_11'

        const key = `streaming:${videoPathA}:${videoPathB}:${cameraIdA}:${cameraIdB}`
        if (synthesisKeyRef.current === key) {
            return undefined
        }

        synthesisAbortRef.current?.abort()
        const abortController = new AbortController()
        synthesisAbortRef.current = abortController
        synthesisKeyRef.current = key

        setSynthesisState({
            key,
            jobId: null,
            status: 'queued',
            progress: null,
            error: null,
            result: null,
            skeleton3D: null,
        })

        const run = async () => {
            try {
                const created = await createStreamingSynthesisJob({
                    videoPathA,
                    videoPathB,
                    cameraIdA,
                    cameraIdB,
                }, { signal: abortController.signal })
                let statusPayload = null
                while (!abortController.signal.aborted) {
                    statusPayload = await getSynthesisJobStatus(created.jobId, { signal: abortController.signal })
                    setSynthesisState(prev => ({
                        ...prev,
                        key,
                        jobId: created.jobId,
                        status: statusPayload?.status ?? 'queued',
                        progress: statusPayload?.progress ?? null,
                        error: statusPayload?.error ?? null,
                    }))
                    if (statusPayload?.status === 'completed') break
                    if (statusPayload?.status === 'failed') {
                        throw new Error(statusPayload?.error?.message ?? '3D synthesis failed.')
                    }
                    await sleep(500, abortController.signal)
                }
                if (abortController.signal.aborted) return

                const [resultPayload, skeletonPayload] = await Promise.all([
                    getSynthesisResult(created.jobId, { signal: abortController.signal }),
                    getSynthesisSkeleton3D(created.jobId, { signal: abortController.signal }),
                ])
                setSynthesisState(prev => ({
                    ...prev,
                    key,
                    jobId: created.jobId,
                    status: 'completed',
                    progress: statusPayload?.progress ?? prev.progress,
                    error: null,
                    result: resultPayload,
                    skeleton3D: adaptSkeleton3DPage(skeletonPayload),
                }))
            } catch (error) {
                if (error?.name === 'AbortError') return
                setSynthesisState(prev => ({
                    ...prev,
                    key,
                    status: 'error',
                    error: {
                        code: String(error?.status ?? 'synthesis_error'),
                        message: error?.message ?? '3D synthesis failed.',
                    },
                }))
            }
        }

        run()
        return () => abortController.abort()
    }, [
        sessionA.videoPath,
        sessionB.videoPath,
        synthesisSession?.jobId,
    ])

    useEffect(() => {
        const jobId = synthesisSession?.jobId ?? synthesisState.jobId
        const status = synthesisSession?.status ?? synthesisState.status
        if (status === 'completed' && jobId) {
            onSynthesisJobIdChange?.(jobId)
        }
    }, [synthesisState.status, synthesisState.jobId, synthesisSession?.status, synthesisSession?.jobId, onSynthesisJobIdChange])

    useEffect(() => {
        onSynthesisProgressChange?.({
            status: synthesisSession?.status ?? synthesisState.status,
            progress: synthesisSession?.progress ?? synthesisState.progress,
        })
    }, [synthesisState.status, synthesisState.progress, synthesisSession?.status, synthesisSession?.progress, onSynthesisProgressChange])

    useEffect(() => {
        if (!isPlaying) {
            lastTsRef.current = null
            return
        }

        const tick = (ts) => {
            if (lastTsRef.current !== null) {
                const delta = ts - lastTsRef.current
                setCurrentTimeMs(prev => {
                    const next = prev + delta
                    if (next >= durationMs) {
                        stopPlayback()
                        return 0
                    }
                    return next
                })
            }
            lastTsRef.current = ts
            animRef.current = requestAnimationFrame(tick)
        }
        animRef.current = requestAnimationFrame(tick)

        return () => {
            if (animRef.current) cancelAnimationFrame(animRef.current)
        }
    }, [isPlaying, durationMs, stopPlayback])

    const frameIndexA = hasA
        ? Math.min(Math.round((currentTimeMs / 1000) * (skeletonA.fps || 30)), skeletonA.frames.length - 1)
        : null
    const frameIndexB = hasB
        ? Math.min(Math.round((currentTimeMs / 1000) * (skeletonB.fps || 30)), skeletonB.frames.length - 1)
        : null
    const frameIndex3D = has3D
        ? Math.min(Math.round((currentTimeMs / 1000) * (skeleton3D.fps || 30)), skeleton3D.frames.length - 1)
        : null

    const modeOptions = [
        { value: 'a-only',      label: 'Session A Only' },
        { value: 'b-only',      label: 'Session B Only' },
        { value: 'synthesized', label: '3D Synthesis' },
    ]

    const cameraOptions = [
        { value: 'front', label: 'FRONT' },
        { value: 'side',  label: 'SIDE' },
        { value: 'top',   label: 'TOP' },
    ]

    const statusLabel = (session) => {
        if (session.status === 'completed') return 'done'
        if (session.isActive) return session.jobMeta.progress?.stage ?? 'active'
        if (session.status === 'error') return 'error'
        return 'idle'
    }

    const synthesisStatusLabel = () => {
        const status = synthesisSession?.status ?? synthesisState.status
        if (status === 'completed') return 'done'
        if (status === 'error' || status === 'failed') return 'error'
        if (['uploading', 'queued', 'initializing', 'streaming', 'validating_manifest', 'loading_source_artifacts', 'aligning_frames', 'triangulating', 'writing_artifacts', 'evaluating'].includes(status)) {
            return status
        }
        return 'idle'
    }

    return (
        <SectionContainer
            id="skeleton3DSynthesis"
            heading="3D SKELETON SYNTHESIS"
            description="Two video streams are inferred and triangulated in parallel via chunk-based streaming pipeline into a paged skeleton3d.v1 result."
        >
            <div className={style.layout}>
                {/* Three.js canvas column */}
                <div className={style.canvasCol}>
                    <div className={style.canvasWrapper}>
                        <ThreeJSSkeleton
                            synthFrame={synthFrame}
                            cameraView={cameraView}
                        />

                        {/* HUD overlay */}
                        <div className={style.hud}>
                            <span className={style.hudChip} data-mode={synthesisMode}>
                                {synthesisMode === 'a-only' ? 'A ONLY'
                                    : synthesisMode === 'b-only' ? 'B ONLY'
                                        : '3D SYNTH'}
                            </span>
                            {synthesisMode === 'synthesized' && synthFrame && (
                                <span className={style.hudChip} data-source="3d">
                                    3D
                                </span>
                            )}
                            {synthFrame && (
                                <span className={style.hudChip}>
                                    {formatMs(currentTimeMs)} / {formatMs(durationMs)}
                                </span>
                            )}
                        </div>

                        {!hasAny && (
                            <div className={style.emptyOverlay}>
                                <div className={style.emptyIcon} aria-hidden="true">
                                    <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
                                        <circle cx="28" cy="28" r="27" stroke="rgba(0,212,255,0.15)" strokeWidth="1.5"/>
                                        <circle cx="28" cy="20" r="4" stroke="rgba(0,212,255,0.3)" strokeWidth="1.5"/>
                                        <path d="M18 34c0-4 4.5-7 10-7s10 3 10 7" stroke="rgba(0,212,255,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
                                        <path d="M18 34v5M38 34v5M18 36h20" stroke="rgba(0,212,255,0.3)" strokeWidth="1.5" strokeLinecap="round"/>
                                    </svg>
                                </div>
                                <p className={style.emptyText}>Complete both analysis sessions</p>
                                <p className={style.emptySubText}>3D view will appear here</p>
                            </div>
                        )}
                    </div>

                    {/* Playback controls */}
                    <div className={style.timelineBar}>
                        <button
                            className={`${style.timelinePlayBtn} ${isPlaying ? style.timelinePlayBtnActive : ''}`}
                            onClick={() => setIsPlaying(p => !p)}
                            disabled={!hasAny || durationMs === 0}
                        >
                            {isPlaying ? '■' : '▶'}
                        </button>
                        <div className={style.timelineScrubWrap}>
                            <input
                                type="range"
                                className={style.timelineScrubber}
                                min={0}
                                max={durationMs || 1}
                                step={16}
                                value={currentTimeMs}
                                onChange={e => {
                                    stopPlayback()
                                    setCurrentTimeMs(Number(e.target.value))
                                }}
                                disabled={!hasAny}
                                style={{ '--progress': durationMs ? `${(currentTimeMs / durationMs) * 100}%` : '0%' }}
                            />
                        </div>
                        <span className={style.timelineTime}>
                            {formatMs(currentTimeMs)} / {formatMs(durationMs)}
                        </span>
                    </div>
                </div>

                {/* Info / Visualization panel column */}
                <div className={style.infoCol}>
                    <div className={style.infoPanel}>

                        {/* Synthesis mode */}
                        <div className={style.infoSection}>
                            <div className={style.infoSectionTitle}>SYNTHESIS MODE</div>
                            <div className={style.modeGroup}>
                                {modeOptions.map(opt => (
                                    <button
                                        key={opt.value}
                                        className={`${style.modeBtn} ${synthesisMode === opt.value ? style.modeBtnActive : ''}`}
                                        onClick={() => setSynthesisMode(opt.value)}
                                        disabled={
                                            (opt.value === 'a-only' && !hasA)
                                            || (opt.value === 'b-only' && !hasB)
                                            || (opt.value === 'synthesized' && !hasAny)
                                        }
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className={style.divider} />

                        {/* Camera presets */}
                        <div className={style.infoSection}>
                            <div className={style.infoSectionTitle}>CAMERA</div>
                            <div className={style.cameraGroup}>
                                {cameraOptions.map(opt => (
                                    <button
                                        key={opt.value}
                                        className={`${style.cameraBtn} ${cameraView === opt.value ? style.cameraBtnActive : ''}`}
                                        onClick={() => setCameraView(opt.value)}
                                    >
                                        {opt.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className={style.divider} />

                        {/* Session status */}
                        <div className={style.infoSection}>
                            <div className={style.infoSectionTitle}>SESSION STATUS</div>
                            <dl className={style.statusRows}>
                                {[
                                    ['A', sessionA, hasA, skeletonA, frameIndexA],
                                    ['B', sessionB, hasB, skeletonB, frameIndexB],
                                ].map(([label, session, has, skeleton, fi]) => (
                                    <div key={label} className={style.statusRow}>
                                        <dt className={style.statusLabel}>{label}</dt>
                                        <dd className={style.statusValue}>
                                            <span
                                                className={style.statusDot}
                                                data-state={statusLabel(session)}
                                            />
                                            <span className={style.statusText}>
                                                {has
                                                    ? `${skeleton.frames.length} frames · ${(skeleton.fps || 30).toFixed(1)} fps`
                                                    : statusLabel(session)}
                                            </span>
                                        </dd>
                                        {has && fi !== null && (
                                            <dd className={style.statusFrameIdx}>
                                                {String(fi).padStart(4, '0')} / {String(skeleton.frames.length - 1).padStart(4, '0')}
                                            </dd>
                                        )}
                                    </div>
                                ))}
                                <div className={style.statusRow}>
                                    <dt className={style.statusLabel}>3D</dt>
                                    <dd className={style.statusValue}>
                                        <span
                                            className={style.statusDot}
                                            data-state={synthesisStatusLabel()}
                                        />
                                        <span className={style.statusText}>
                                            {has3D
                                                ? `${skeleton3D.frames.length} frames`
                                                : (synthesisSession?.progress ?? synthesisState.progress)?.stage ?? synthesisStatusLabel()}
                                        </span>
                                    </dd>
                                    {has3D && frameIndex3D !== null && (
                                        <dd className={style.statusFrameIdx}>
                                            {String(frameIndex3D).padStart(4, '0')} / {String(skeleton3D.totalFrames - 1).padStart(4, '0')}
                                        </dd>
                                    )}
                                </div>
                            </dl>
                        </div>

                        <div className={style.divider} />

                        {/* Joint visibility table */}
                        <div className={style.infoSection}>
                            <div className={style.infoSectionTitle}>JOINT VISIBILITY</div>
                            <table className={style.jointTable}>
                                <thead>
                                    <tr>
                                        <th className={style.jointTh}>Joint</th>
                                        <th className={style.jointTh}>A</th>
                                        <th className={style.jointTh}>B</th>
                                        <th className={style.jointTh}>Δ</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {KEY_JOINTS.map(([idx, name]) => {
                                        const lmA = frameA?.landmarks?.[idx]
                                        const lmB = frameB?.landmarks?.[idx]
                                        const visA = lmA?.visibility ?? null
                                        const visB = lmB?.visibility ?? null
                                        const delta = (visA != null && visB != null)
                                            ? Math.abs(visA - visB)
                                            : null

                                        const isLowA = visA != null && visA < 0.5
                                        const isLowB = visB != null && visB < 0.5
                                        const isHighDelta = delta != null && delta > 0.2

                                        return (
                                            <tr key={idx} className={style.jointRow}>
                                                <td className={style.jointName}>{name}</td>
                                                <td className={`${style.jointVis} ${isLowA ? style.jointVisLow : ''}`}>
                                                    {formatVis(visA)}
                                                </td>
                                                <td className={`${style.jointVis} ${isLowB ? style.jointVisLow : ''}`}>
                                                    {formatVis(visB)}
                                                </td>
                                                <td className={`${style.jointDelta} ${isHighDelta ? style.jointDeltaHigh : ''}`}>
                                                    {delta != null ? delta.toFixed(2) : '—'}
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>

                    </div>
                </div>
            </div>
        </SectionContainer>
    )
}
