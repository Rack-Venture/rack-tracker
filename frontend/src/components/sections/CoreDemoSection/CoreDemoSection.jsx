import { useEffect, useId, useRef, useState, useCallback } from 'react'
import Panel from '../../Panel/Panel'
import VideoUpload from '../../VideoUpload/VideoUpload'
import FpsSelector from '../../FpsSelector/FpsSelector'
import Button from '../../Button/Button'
import UploadIcon from '../../../assets/images/icon_ArrowUp.png'
import SettingIcon from '../../../assets/images/icon_setting.png'
import style from './CoreDemoSection.module.css'
import SectionContainer from '../../SectionContainer/SectionContainer'
import { buildProgressSteps, formatStageLabel } from '../../../features/analysis-session/adapters.js'

function formatDuration(ms) {
    if (!ms) return '0.0s'
    return `${(ms / 1000).toFixed(1)}s`
}

function clampNumber(value, min) {
    return Math.max(min, Number(value.toFixed(1)))
}

const ACTIVE_PROGRESS_STATUSES = new Set([
    'uploading',
    'queued',
    'initializing_landmarker',
    'analyzing',
    'computing',
    'generating_feedback',
])

function ListboxField({ label, value, options, onChange }) {
    const [isOpen, setIsOpen] = useState(false)
    const rootRef = useRef(null)
    const listboxId = useId()
    const selectedIndex = options.findIndex((option) => option.value === value)
    const selectedOption = selectedIndex >= 0 ? options[selectedIndex] : options[0]

    useEffect(() => {
        if (!isOpen) return undefined

        const handlePointerDown = (event) => {
            if (!rootRef.current?.contains(event.target)) {
                setIsOpen(false)
            }
        }

        const handleEscape = (event) => {
            if (event.key === 'Escape') {
                setIsOpen(false)
            }
        }

        document.addEventListener('mousedown', handlePointerDown)
        document.addEventListener('keydown', handleEscape)

        return () => {
            document.removeEventListener('mousedown', handlePointerDown)
            document.removeEventListener('keydown', handleEscape)
        }
    }, [isOpen])

    const moveSelection = (direction) => {
        const fallbackIndex = selectedIndex >= 0 ? selectedIndex : 0
        const nextIndex = (fallbackIndex + direction + options.length) % options.length
        onChange(options[nextIndex].value)
    }

    const handleTriggerKeyDown = (event) => {
        if (event.key === 'ArrowDown') {
            event.preventDefault()
            if (!isOpen) {
                setIsOpen(true)
                return
            }
            moveSelection(1)
        }

        if (event.key === 'ArrowUp') {
            event.preventDefault()
            if (!isOpen) {
                setIsOpen(true)
                return
            }
            moveSelection(-1)
        }

        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            setIsOpen(prev => !prev)
        }

        if (event.key === 'Escape') {
            setIsOpen(false)
        }
    }

    return (
        <div className={style.field}>
            <span className={style.fieldLabel}>{label}</span>
            <div className={style.listbox} ref={rootRef}>
                <button
                    type="button"
                    className={`${style.listboxTrigger} ${isOpen ? style.listboxTriggerOpen : ''}`}
                    aria-haspopup="listbox"
                    aria-expanded={isOpen}
                    aria-controls={listboxId}
                    onClick={() => setIsOpen(prev => !prev)}
                    onKeyDown={handleTriggerKeyDown}
                >
                    <span className={style.listboxValue}>{selectedOption?.label ?? ''}</span>
                    <span className={`${style.selectIcon} ${isOpen ? style.selectIconOpen : ''}`} aria-hidden="true" />
                </button>

                {isOpen && (
                    <div className={style.listboxPopover}>
                        <ul id={listboxId} className={style.listboxOptions} role="listbox" aria-label={label}>
                            {options.map((option) => {
                                const isSelected = option.value === value

                                return (
                                    <li key={option.value} role="presentation">
                                        <button
                                            type="button"
                                            role="option"
                                            aria-selected={isSelected}
                                            className={`${style.listboxOption} ${isSelected ? style.listboxOptionSelected : ''}`}
                                            onClick={() => {
                                                onChange(option.value)
                                                setIsOpen(false)
                                            }}
                                        >
                                            <span>{option.label}</span>
                                            {isSelected && <span className={style.listboxCheck} aria-hidden="true">Current</span>}
                                        </button>
                                    </li>
                                )
                            })}
                        </ul>
                    </div>
                )}
            </div>
        </div>
    )
}

function NumberStepperField({ label, value, min, onChange, onStepDown, onStepUp }) {
    return (
        <label className={style.field}>
            <span className={style.fieldLabel}>{label}</span>
            <div className={style.numberField}>
                <input
                    className={`${style.input} ${style.numberInput}`}
                    type="number"
                    min={String(min)}
                    step="0.1"
                    inputMode="decimal"
                    value={value}
                    onChange={(event) => onChange(event.target.value)}
                />
                <div className={style.stepperInline}>
                    <button
                        type="button"
                        className={style.stepperAction}
                        onClick={onStepDown}
                        aria-label={`Decrease ${label.toLowerCase()}`}
                    >
                        -
                    </button>
                    <span className={style.stepperDivider} />
                    <button
                        type="button"
                        className={style.stepperAction}
                        onClick={onStepUp}
                        aria-label={`Increase ${label.toLowerCase()}`}
                    >
                        +
                    </button>
                </div>
            </div>
        </label>
    )
}

function toBenchmarkView(raw) {
    if (!raw) return null
    return {
        requestedDelegate: raw?.run?.requestedDelegate ?? null,
        actualDelegate: raw?.run?.actualDelegate ?? null,
        delegateFallbackApplied: Boolean(raw?.run?.delegateFallbackApplied),
        totalElapsedMs: raw?.timingSummary?.totalElapsedMs ?? null,
        poseDetectedRatio: raw?.qualitySummary?.poseDetectedRatio ?? null,
        avgVisibility: raw?.qualitySummary?.avgVisibility ?? null,
        raw,
    }
}

function formatMs(ms) {
    if (ms == null) return '—'
    if (ms < 1000) return `${Math.round(ms)}ms`
    return `${(ms / 1000).toFixed(2)}s`
}

function formatPct(ratio) {
    if (ratio == null) return '—'
    return `${(ratio * 100).toFixed(1)}%`
}
function formatInteger(value) {
    return Number.isFinite(value) ? Math.round(value).toLocaleString() : '—'
}

function getMetricNumber(...values) {
    for (const value of values) {
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value
        }
    }
    return null
}

function formatThroughput(value, unit) {
    if (!Number.isFinite(value) || value <= 0) return '—'
    const fixed = value >= 100 ? 0 : value >= 10 ? 1 : 2
    return `${value.toFixed(fixed)} ${unit}`
}

function buildPipelineRows(stageDetails, pipelineSummary, processedFrames) {
    const producerFrames = getMetricNumber(stageDetails?.producerFrames, pipelineSummary?.producerFrames)
    const producerChunks = getMetricNumber(stageDetails?.producerChunksProcessed, pipelineSummary?.producerChunksProcessed)
    const poseChunks = getMetricNumber(stageDetails?.poseChunksProcessed, pipelineSummary?.poseChunksProcessed)

    const producerAvgMs = getMetricNumber(stageDetails?.avgChunkReadMs, pipelineSummary?.avgChunkReadMs)
    const producerTotalMs = getMetricNumber(
        pipelineSummary?.totalChunkReadMs,
        producerChunks != null && producerAvgMs != null ? producerChunks * producerAvgMs : null,
    )
    const poseAvgMs = getMetricNumber(stageDetails?.avgChunkInferenceMs, pipelineSummary?.avgChunkInferenceMs)
    const poseTotalMs = getMetricNumber(
        pipelineSummary?.totalChunkInferenceMs,
        poseChunks != null && poseAvgMs != null ? poseChunks * poseAvgMs : null,
    )

    const rows = [
        {
            key: 'frame',
            label: 'Prod',
            title: 'Frame producer — VideoReaderService.iter_frame_chunks()',
            countText: producerFrames != null ? `${formatInteger(producerFrames)} frames` : 'waiting',
            detailText: [
                producerChunks != null ? `${formatInteger(producerChunks)} chunks` : null,
                producerAvgMs != null ? `avg ${formatMs(producerAvgMs)}` : null,
                producerFrames != null && producerTotalMs != null && producerTotalMs > 0
                    ? formatThroughput((producerFrames / producerTotalMs) * 1000, 'fps')
                    : null,
            ].filter(Boolean).join(' · '),
            queueDepth: getMetricNumber(stageDetails?.frameQueueDepth),
            queueMax: getMetricNumber(stageDetails?.frameQueueMax),
            activityCount: producerChunks,
        },
        {
            key: 'pose',
            label: 'Infer',
            title: 'Pose inference — PoseInferenceService.infer_chunk()',
            countText: poseChunks != null ? `${formatInteger(poseChunks)} chunks` : 'waiting',
            detailText: [
                poseAvgMs != null ? `avg ${formatMs(poseAvgMs)}` : null,
                processedFrames != null && poseTotalMs != null && poseTotalMs > 0
                    ? formatThroughput((processedFrames / poseTotalMs) * 1000, 'fps')
                    : null,
            ].filter(Boolean).join(' · '),
            queueDepth: getMetricNumber(stageDetails?.poseQueueDepth),
            queueMax: getMetricNumber(stageDetails?.poseQueueMax),
            activityCount: poseChunks,
        },
    ]

    const maxActivityCount = rows.reduce((max, row) => (
        row.activityCount != null && row.activityCount > 0
            ? Math.max(max, row.activityCount)
            : max
    ), 0)

    return rows.map((row) => {
        const hasWork = (
            (row.activityCount != null && row.activityCount > 0)
            || (row.queueDepth != null && row.queueDepth > 0)
        )
        const activityRatio = maxActivityCount > 0 && row.activityCount != null && row.activityCount > 0
            ? Math.max(0.18, Math.min(1, row.activityCount / maxActivityCount))
            : hasWork
                ? 0.18
                : 0

        return {
            ...row,
            hasWork,
            activityRatio,
        }
    })
}

function TopoNode({ label, count, detail, isLive, isDone, isSkipped }) {
    return (
        <div
            className={style.topoNode}
            data-live={isLive ? 'true' : 'false'}
            data-done={isDone ? 'true' : 'false'}
            data-skipped={isSkipped ? 'true' : 'false'}
        >
            <span className={style.topoNodeLabel}>{label}</span>
            <span className={style.topoNodeCount}>{count}</span>
            {detail && <span className={style.topoNodeDetail}>{detail}</span>}
            <div className={style.topoNodeBar}>
                {isDone
                    ? <div className={style.topoNodeBarDone} />
                    : isLive
                        ? <div className={style.topoNodeBarFlow} />
                        : null
                }
            </div>
        </div>
    )
}

function buildStartupRows(startup) {
    if (!startup) return []

    const rows = [
        ['Startup wall', startup.startupWallMs, null],
        ['Landmarker init', startup.landmarkerInitMs, null],
        ['First chunk read', startup.firstChunkReadMs, null],
        ['First chunk infer', startup.firstChunkInferenceMs, null],
    ].filter(([, value]) => value != null)

    if (Number.isFinite(startup.firstChunkSampleCount)) {
        rows.push([
            'First chunk span',
            startup.firstChunkSampleCount,
            Number.isFinite(startup.firstChunkSourceFrameSpan)
                ? `${formatInteger(startup.firstChunkSourceFrameSpan)} source frames`
                : null,
        ])
    }

    return rows
}

const SYNTH_ACTIVE_STATUSES = new Set(['uploading', 'queued', 'initializing', 'streaming', 'writing_artifacts'])

function SynthSharedColumn({ synthesisSession }) {
    const synthDetails = synthesisSession?.progress?.stageDetails?.synthesis ?? null
    const synthStatus = synthesisSession?.status ?? 'idle'
    const isActive = SYNTH_ACTIVE_STATUSES.has(synthStatus)
    const isDone = synthStatus === 'completed'
    const isError = synthStatus === 'error'
    const isPreset = Boolean(synthesisSession?.form?.presetIdA && synthesisSession?.form?.presetIdB)
    const jobId = synthesisSession?.jobId ?? null
    const elapsedMs = synthesisSession?.startedAt
        ? Math.max(0, (synthesisSession.now ?? Date.now()) - synthesisSession.startedAt)
        : 0
    const result = synthesisSession?.result ?? null

    const inferredChunksA = getMetricNumber(synthDetails?.inferredChunksA)
    const inferredChunksB = getMetricNumber(synthDetails?.inferredChunksB)
    const pairedChunks = getMetricNumber(synthDetails?.pairedChunks)
    const triangulatedChunks = getMetricNumber(synthDetails?.triangulatedChunks)
    const triangulatedFrames = getMetricNumber(synthDetails?.triangulatedFrames)
    const avgTriangulateMs = getMetricNumber(synthDetails?.avgTriangulateMs)
    const p95TriangulateMs = getMetricNumber(synthDetails?.p95TriangulateMs)

    const totalFrames = getMetricNumber(synthesisSession?.progress?.totalFrames)
    const progressFrames = getMetricNumber(synthesisSession?.progress?.processedFrames) ?? triangulatedFrames
    const progressRatio = totalFrames && totalFrames > 0 && progressFrames != null
        ? Math.min(1, progressFrames / totalFrames)
        : isDone ? 1 : null

    const analysisA = result?.analysisA ?? null
    const analysisB = result?.analysisB ?? null
    const skeleton3dMeta = result?.skeleton3d ?? null
    const q3d = skeleton3dMeta?.qualitySummary ?? null
    const timeline3d = skeleton3dMeta?.timeline ?? null
    const synthInfo = skeleton3dMeta?.synthesisInfo ?? null

    const triDetail = [
        avgTriangulateMs != null ? `avg ${formatMs(avgTriangulateMs)}` : null,
        p95TriangulateMs != null ? `p95 ${formatMs(p95TriangulateMs)}` : null,
    ].filter(Boolean).join(' · ') || null

    const badgeState = isError ? 'error' : isDone ? 'done' : isActive ? 'active' : 'idle'

    return (
        <div className={style.progressCol}>
            <div className={style.progressColHeader}>Synthesis Pipeline</div>

            {/* Status header */}
            <div className={style.ppStatusRow}>
                <div className={style.ppBadge} data-state={badgeState}>
                    <span className={style.ppBadgeDot} />
                    <span>{synthStatus}</span>
                </div>
                {jobId && (
                    <div className={style.ppMeta}>
                        <span>{`#${String(jobId).slice(-6)}`}</span>
                        <span>{formatDuration(elapsedMs)}</span>
                    </div>
                )}
            </div>

            {/* Pipeline topology */}
            <div className={style.topoWrapper}>

                {/* Parallel A/B inference tracks */}
                <div className={style.topoParallelRow}>
                    <div className={style.topoTrack}>
                        <div className={style.topoTrackHeader}>Camera A</div>
                        <TopoNode
                            label={isPreset ? 'preset load' : 'infer_poses(A)'}
                            count={
                                isPreset ? 'skip'
                                : inferredChunksA != null ? `${formatInteger(inferredChunksA)} chunks`
                                : 'waiting'
                            }
                            isLive={isActive && !isPreset && inferredChunksA != null}
                            isDone={isDone}
                            isSkipped={isPreset}
                        />
                    </div>
                    <div className={style.topoParallelDivider} />
                    <div className={style.topoTrack}>
                        <div className={style.topoTrackHeader}>Camera B</div>
                        <TopoNode
                            label={isPreset ? 'preset load' : 'infer_poses(B)'}
                            count={
                                isPreset ? 'skip'
                                : inferredChunksB != null ? `${formatInteger(inferredChunksB)} chunks`
                                : 'waiting'
                            }
                            isLive={isActive && !isPreset && inferredChunksB != null}
                            isDone={isDone}
                            isSkipped={isPreset}
                        />
                    </div>
                </div>

                {/* Convergence arrow */}
                <div className={style.topoConvergeRow}>
                    <div className={style.topoConvergeLine} />
                    <div className={style.topoConvergePoint}>▼</div>
                    <div className={style.topoConvergeLine} />
                </div>

                {/* coordinate() node */}
                <TopoNode
                    label="coordinate()"
                    count={pairedChunks != null ? `${formatInteger(pairedChunks)} pairs` : 'waiting'}
                    detail="→ assembler_a/b (2D skeleton)"
                    isLive={isActive && pairedChunks != null}
                    isDone={isDone}
                />

                <div className={style.topoArrowDown}>↓</div>

                {/* triangulate() node */}
                <TopoNode
                    label="triangulate()"
                    count={triangulatedChunks != null ? `${formatInteger(triangulatedChunks)} chunks` : 'waiting'}
                    detail={triDetail}
                    isLive={isActive && triangulatedChunks != null}
                    isDone={isDone}
                />

                <div className={style.topoArrowDown}>↓</div>

                {/* main collector node */}
                <TopoNode
                    label="[main collector]"
                    count={triangulatedFrames != null ? `${formatInteger(triangulatedFrames)} frames` : 'waiting'}
                    isLive={isActive && triangulatedFrames != null}
                    isDone={isDone}
                />

                {/* Progress bar */}
                {progressRatio != null && (isActive || isDone) && (
                    <div className={style.topoProgressWrap}>
                        <div className={style.topoProgressBar}>
                            <div
                                className={style.topoProgressFill}
                                data-done={isDone ? 'true' : 'false'}
                                style={{ width: `${progressRatio * 100}%` }}
                            />
                        </div>
                        <span className={style.topoProgressLabel}>
                            {(progressRatio * 100).toFixed(1)}%
                        </span>
                    </div>
                )}
            </div>

            {/* Error message */}
            {isError && synthesisSession?.error && (
                <div className={style.ppHint} style={{ color: 'var(--color-error, #f44)' }}>
                    {synthesisSession.error.message ?? 'Synthesis error'}
                </div>
            )}

            {/* Completion benchmark */}
            {isDone && (analysisA || analysisB || q3d) && (
                <div className={style.bmSection}>
                    <span className={style.bmSectionTitle}>Benchmark</span>

                    {/* 3D Triangulation Quality */}
                    {q3d && (
                        <div className={style.bmSubSection}>
                            <span className={style.bmSubTitle}>3D Quality</span>
                            <dl className={style.bmRows}>
                                {q3d.pairedFrameCount != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Paired frames</dt>
                                        <dd className={style.bmValue}>
                                            {formatInteger(q3d.pairedFrameCount)}
                                            {(q3d.unmatchedPrimaryFrameCount != null || q3d.unmatchedSecondaryFrameCount != null) && (
                                                <span className={style.bmDim}>
                                                    {q3d.unmatchedPrimaryFrameCount ?? 0} A unmatched · {q3d.unmatchedSecondaryFrameCount ?? 0} B unmatched
                                                </span>
                                            )}
                                        </dd>
                                    </div>
                                )}
                                {q3d.validFrameRatio != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Valid frame ratio</dt>
                                        <dd className={`${style.bmValue} ${q3d.validFrameRatio < 0.8 ? style.bmValueWarn : ''}`}>
                                            {formatPct(q3d.validFrameRatio)}
                                            {q3d.usableFrameCount != null && (
                                                <span className={style.bmDim}>{formatInteger(q3d.usableFrameCount)} usable</span>
                                            )}
                                        </dd>
                                    </div>
                                )}
                                {q3d.usableJointRatio != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Usable joint ratio</dt>
                                        <dd className={`${style.bmValue} ${q3d.usableJointRatio < 0.7 ? style.bmValueWarn : ''}`}>
                                            {formatPct(q3d.usableJointRatio)}
                                            {q3d.successfulJointCount != null && q3d.totalJointCount != null && (
                                                <span className={style.bmDim}>{formatInteger(q3d.successfulJointCount)} / {formatInteger(q3d.totalJointCount)} joints</span>
                                            )}
                                        </dd>
                                    </div>
                                )}
                                {q3d.meanReprojectionErrorPx != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Reprojection error</dt>
                                        <dd className={`${style.bmValue} ${q3d.meanReprojectionErrorPx > 10 ? style.bmValueWarn : ''}`}>
                                            {q3d.meanReprojectionErrorPx.toFixed(2)} px (mean)
                                        </dd>
                                    </div>
                                )}
                                {(q3d.meanTimestampDeltaMs != null || q3d.maxTimestampDeltaMs != null) && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Timestamp delta</dt>
                                        <dd className={style.bmValue}>
                                            {q3d.meanTimestampDeltaMs != null && `avg ${formatMs(q3d.meanTimestampDeltaMs)}`}
                                            {q3d.maxTimestampDeltaMs != null && (
                                                <span className={style.bmDim}>max {formatMs(q3d.maxTimestampDeltaMs)}</span>
                                            )}
                                        </dd>
                                    </div>
                                )}
                                {q3d.failureReasonCounts && Object.keys(q3d.failureReasonCounts).length > 0 && (
                                    <div className={`${style.bmRow} ${style.bmRowStack}`}>
                                        <dt className={`${style.bmLabel} ${style.bmValueWarn}`}>Failure reasons</dt>
                                        <dd className={style.bmDelegateErrors}>
                                            {Object.entries(q3d.failureReasonCounts).map(([k, v]) => (
                                                <div key={k} className={style.bmDelegateError}>
                                                    <span className={style.bmValueWarn}>{k}:</span> {formatInteger(v)}
                                                </div>
                                            ))}
                                        </dd>
                                    </div>
                                )}
                            </dl>
                        </div>
                    )}

                    {/* Per-camera analysis quality */}
                    {[['A', analysisA], ['B', analysisB]].map(([cam, analysis]) => {
                        const s = analysis?.summary
                        if (!s) return null
                        return (
                            <div key={cam} className={style.bmSubSection}>
                                <span className={style.bmSubTitle}>Camera {cam} Analysis</span>
                                <dl className={style.bmRows}>
                                    {s.frameCount != null && (
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Frames</dt>
                                            <dd className={style.bmValue}>
                                                {formatInteger(s.frameCount)}
                                                {s.sampledFps != null && (
                                                    <span className={style.bmDim}>@ {Number(s.sampledFps).toFixed(1)} fps</span>
                                                )}
                                                {s.durationMs != null && (
                                                    <span className={style.bmDim}>{formatDuration(s.durationMs)}</span>
                                                )}
                                            </dd>
                                        </div>
                                    )}
                                    {s.detectionRatio != null && (
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Pose detected</dt>
                                            <dd className={`${style.bmValue} ${s.detectionRatio < 0.5 ? style.bmValueWarn : ''}`}>
                                                {formatPct(s.detectionRatio)}
                                                {s.usableFrameCount != null && s.frameCount != null && (
                                                    <span className={style.bmDim}>{formatInteger(s.usableFrameCount)} usable / {formatInteger(s.frameCount)}</span>
                                                )}
                                            </dd>
                                        </div>
                                    )}
                                    {s.repCount != null && s.repCount > 0 && (
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Rep count</dt>
                                            <dd className={style.bmValue}>{s.repCount}</dd>
                                        </div>
                                    )}
                                </dl>
                            </div>
                        )
                    })}

                    {/* Pipeline throughput */}
                    {(inferredChunksA != null || pairedChunks != null || triangulatedChunks != null) && (
                        <div className={style.bmSubSection}>
                            <span className={style.bmSubTitle}>Pipeline — {formatDuration(elapsedMs)}</span>
                            <dl className={style.bmRows}>
                                {!isPreset && inferredChunksA != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Infer A</dt>
                                        <dd className={style.bmValue}>{formatInteger(inferredChunksA)} chunks</dd>
                                    </div>
                                )}
                                {!isPreset && inferredChunksB != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Infer B</dt>
                                        <dd className={style.bmValue}>{formatInteger(inferredChunksB)} chunks</dd>
                                    </div>
                                )}
                                {isPreset && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Source</dt>
                                        <dd className={style.bmValue}>preset JSON (no inference)</dd>
                                    </div>
                                )}
                                {pairedChunks != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Coordinate</dt>
                                        <dd className={style.bmValue}>{formatInteger(pairedChunks)} pairs</dd>
                                    </div>
                                )}
                                {triangulatedChunks != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Triangulate</dt>
                                        <dd className={style.bmValue}>
                                            {formatInteger(triangulatedChunks)} chunks
                                            {triDetail && <span className={style.bmDim}>{triDetail}</span>}
                                        </dd>
                                    </div>
                                )}
                                {(triangulatedFrames ?? timeline3d?.totalFrames) != null && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>3D frames</dt>
                                        <dd className={style.bmValue}>
                                            {formatInteger(triangulatedFrames ?? timeline3d?.totalFrames)}
                                            {timeline3d?.fps != null && (
                                                <span className={style.bmDim}>@ {timeline3d.fps.toFixed(1)} fps</span>
                                            )}
                                            {timeline3d?.durationMs != null && (
                                                <span className={style.bmDim}>{formatDuration(timeline3d.durationMs)}</span>
                                            )}
                                        </dd>
                                    </div>
                                )}
                                {synthInfo?.cameraPair && (
                                    <div className={style.bmRow}>
                                        <dt className={style.bmLabel}>Camera pair</dt>
                                        <dd className={style.bmValue}>{synthInfo.cameraPair.join(' · ')}</dd>
                                    </div>
                                )}
                            </dl>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

const IDLE_RING_LABELS = ['Upload', 'Queue', 'Init', 'Analyze', 'Biomech', 'Feedback', 'Done']
const IDLE_STEP_LABELS = [
    'Upload started',
    'Queued',
    'Landmarker init',
    'Streaming pipeline',
    'Biomechanical analysis',
    'Feedback generation',
    'Completed',
]

function ProgressColumn({ session, label }) {
    const { status, jobMeta, result, skeletonPage, benchmarkDetails, loadBenchmark, stageMoments, startedAt, now, isActive, form } = session
    const [isFetchingBenchmark, setIsFetchingBenchmark] = useState(false)
    const [bmRawCopied, setBmRawCopied] = useState(false)

    const progressSteps = buildProgressSteps(jobMeta.progress, stageMoments, now)
    const elapsedMs = startedAt ? Math.max(0, now - startedAt) : 0
    const totalSteps = progressSteps.length
    const currentStep = progressSteps.filter(s => s.status !== 'pending').length
    const hasVideo = Boolean(form.videoFile) || Boolean(form.presetEstimationId)
    const processedFrames = Number.isFinite(jobMeta.progress?.processedFrames)
        ? jobMeta.progress.processedFrames
        : null
    const totalFrames = Number.isFinite(jobMeta.progress?.totalFrames)
        ? jobMeta.progress.totalFrames
        : null
    const frameProgressLabel = totalFrames != null
        ? `${processedFrames ?? 0} / ${totalFrames} frames`
        : processedFrames != null
            ? `${processedFrames} frames`
            : `${currentStep} / ${totalSteps}`
    const frameRatio = (processedFrames != null && totalFrames != null && totalFrames > 0)
        ? Math.min(1, processedFrames / totalFrames)
        : null

    const bm = result?.benchmarkView ?? toBenchmarkView(benchmarkDetails)
    const canFetchBenchmark = !bm && jobMeta.jobId && (status === 'completed' || status === 'error')

    const bmRaw = bm?.raw ?? null
    const bmRun = bmRaw?.run ?? null
    const bmTiming = bmRaw?.timingSummary ?? null
    const bmQuality = bmRaw?.qualitySummary ?? null
    const bmLlm = bmRaw?.llmCallResult ?? null
    const bmLlmPrompt = bmRaw?.llmPromptDiagnostics ?? null
    const progressStageDetails = jobMeta.progress?.stageDetails ?? null
    const benchmarkStartupSummary = bmTiming?.startupSummary ?? null
    const pipelineSummary = bmTiming?.pipelineSummary ?? null
    const startupRows = buildStartupRows(benchmarkStartupSummary || progressStageDetails)
    const pipelineRows = buildPipelineRows(progressStageDetails, pipelineSummary, processedFrames)

    const handleFetchBenchmark = useCallback(async () => {
        setIsFetchingBenchmark(true)
        try {
            await loadBenchmark()
        } finally {
            setIsFetchingBenchmark(false)
        }
    }, [loadBenchmark])

    return (
        <div className={style.progressCol}>
            <div className={style.progressColHeader}>{label}</div>

            {!hasVideo ? (
                <>
                    <div className={style.ppStatusRow}>
                        <div className={style.ppBadge} data-state="idle">
                            <span className={style.ppBadgeDot} />
                            <span>Idle</span>
                        </div>
                        <div className={style.ppMeta}>
                            <span>—</span>
                            <span>0.0s</span>
                            <span>0 / 7</span>
                        </div>
                    </div>

                    <p className={style.ppHint}>Upload a video or select a preset JSON to activate live job polling and stage-by-stage pipeline updates.</p>

                    <svg className={style.ppSegBar} viewBox="0 0 140 140" width="100%" height="100%" aria-hidden="true">
                        {IDLE_RING_LABELS.map((ringLabel, i, arr) => {
                            const r = 62, total = arr.length
                            const segLen = (2 * Math.PI * r) * ((360 / total - 10) / 360)
                            const dashGap = (2 * Math.PI * r) - segLen
                            return (
                                <circle
                                    key={ringLabel}
                                    className={style.ppSeg}
                                    data-state="idle"
                                    cx="70" cy="70" r={r}
                                    fill="none"
                                    strokeDasharray={`${segLen.toFixed(2)} ${dashGap.toFixed(2)}`}
                                    style={{ transform: `rotate(${-90 + (360 / total) * i}deg)`, transformOrigin: '70px 70px' }}
                                />
                            )
                        })}
                    </svg>

                    <ol className={style.ppSteps}>
                        {IDLE_STEP_LABELS.map((stepLabel, i, arr) => (
                            <li key={stepLabel} className={style.ppStep} data-state="idle">
                                <div className={style.ppStepIndicator}>
                                    <span className={style.ppStepNum}>{i + 1}</span>
                                    {i < arr.length - 1 && <span className={style.ppStepLine} />}
                                </div>
                                <div className={style.ppStepBody}>
                                    <span className={style.ppStepLabel}>{stepLabel}</span>
                                    <span className={style.ppStepTime}>—</span>
                                </div>
                            </li>
                        ))}
                    </ol>
                </>
            ) : (
                <>
                    <div className={style.ppStatusRow}>
                        <div
                            className={style.ppBadge}
                            data-state={isActive ? 'active' : status === 'completed' ? 'done' : status === 'error' ? 'error' : 'idle'}
                        >
                            <span className={style.ppBadgeDot} />
                            <span>{formatStageLabel(jobMeta.progress?.stage ?? status)}</span>
                        </div>
                        <div className={style.ppMeta}>
                            <span>{jobMeta.jobId ? `#${String(jobMeta.jobId).slice(-6)}` : '—'}</span>
                            <span>{formatDuration(elapsedMs)}</span>
                            <span>{frameProgressLabel}</span>
                        </div>
                    </div>

                    <svg className={style.ppSegBar} viewBox="0 0 140 140" width="100%" height="100%" aria-hidden="true">
                        {progressSteps.map((step, i) => {
                            const r = 62, total = progressSteps.length
                            const segLen = (2 * Math.PI * r) * ((360 / total - 10) / 360)
                            const dashGap = (2 * Math.PI * r) - segLen
                            const rotation = -90 + (360 / total) * i
                            const isAnalyzingActive = step.key === 'analyzing' && step.status === 'active' && frameRatio != null
                            return (
                                <g key={step.key}>
                                    <circle
                                        className={style.ppSeg}
                                        data-state={isAnalyzingActive ? 'active-slot' : step.status}
                                        cx="70" cy="70" r={r}
                                        fill="none"
                                        strokeDasharray={`${segLen.toFixed(2)} ${dashGap.toFixed(2)}`}
                                        style={{ transform: `rotate(${rotation}deg)`, transformOrigin: '70px 70px' }}
                                    />
                                    {isAnalyzingActive && (
                                        <circle
                                            className={style.ppSegFill}
                                            cx="70" cy="70" r={r}
                                            fill="none"
                                            strokeDasharray={`${(segLen * frameRatio).toFixed(2)} ${((2 * Math.PI * r) - segLen * frameRatio).toFixed(2)}`}
                                            style={{ transform: `rotate(${rotation}deg)`, transformOrigin: '70px 70px' }}
                                        />
                                    )}
                                </g>
                            )
                        })}
                    </svg>

                    <ol className={style.ppSteps}>
                        {progressSteps.map((step, i) => {
                            const showConveyor = step.key === 'analyzing'
                                && (step.status === 'active' || step.status === 'done')
                            const showStartupDetails = startupRows.length > 0
                                && (step.key === 'initializing_landmarker' || step.key === 'analyzing')
                                && step.status !== 'pending'
                            return (
                                <li key={step.key} className={style.ppStep} data-state={step.status}>
                                    <div className={style.ppStepIndicator}>
                                        <span className={style.ppStepNum}>
                                            {step.status === 'done' ? '✓' : i + 1}
                                        </span>
                                        {i < progressSteps.length - 1 && <span className={style.ppStepLine} />}
                                    </div>
                                    <div className={style.ppStepBody}>
                                        <span className={style.ppStepLabel}>{step.label}</span>
                                        <span className={style.ppStepTime}>
                                            {step.status !== 'pending' ? formatDuration(step.elapsedMs) : '—'}
                                        </span>
                                        {showStartupDetails && (
                                            <dl className={style.ppDetailRows}>
                                                {startupRows.map(([detailLabel, value, hint]) => (
                                                    <div key={detailLabel} className={style.ppDetailRow}>
                                                        <dt className={style.ppDetailLabel}>{detailLabel}</dt>
                                                        <dd className={style.ppDetailValue}>
                                                            {typeof value === 'number' && detailLabel === 'First chunk span'
                                                                ? `${formatInteger(value)} samples`
                                                                : formatMs(value)}
                                                            {hint && <span className={style.ppDetailHint}>{hint}</span>}
                                                        </dd>
                                                    </div>
                                                ))}
                                            </dl>
                                        )}
                                        {showConveyor && (
                                            <div className={style.ppConveyor}>
                                                {pipelineRows.map((row) => {
                                                    const queueRatio = row.queueDepth != null && row.queueMax != null && row.queueMax > 0
                                                        ? Math.max(0, Math.min(1, row.queueDepth / row.queueMax))
                                                        : 0
                                                    const isRowLive = step.status === 'active' && row.hasWork

                                                    return (
                                                        <div
                                                            key={row.key}
                                                            className={style.ppConveyorRow}
                                                            data-state={step.status}
                                                            data-live={isRowLive ? 'true' : 'false'}
                                                            title={row.title}
                                                        >
                                                            <span className={style.ppConveyorLabel}>{row.label}</span>
                                                            <div
                                                                className={style.ppConveyorTrack}
                                                                data-kind={row.key}
                                                                data-live={isRowLive ? 'true' : 'false'}
                                                            >
                                                                {isRowLive && row.activityRatio > 0 && (
                                                                    <div
                                                                        className={style.ppConveyorActivityFill}
                                                                        data-kind={row.key}
                                                                        style={{ width: `${row.activityRatio * 100}%` }}
                                                                    />
                                                                )}
                                                                {queueRatio > 0 && (
                                                                    <div
                                                                        className={style.ppConveyorQueueFill}
                                                                        data-level={queueRatio >= 0.9 ? 'high' : queueRatio >= 0.5 ? 'mid' : 'low'}
                                                                        style={{ width: `${queueRatio * 100}%` }}
                                                                    />
                                                                )}
                                                                {step.status === 'done'
                                                                    ? <div className={style.ppConveyorDone} />
                                                                    : (
                                                                        <div
                                                                            className={style.ppConveyorFlow}
                                                                            data-kind={row.key}
                                                                            data-live={isRowLive ? 'true' : 'false'}
                                                                        />
                                                                    )
                                                                }
                                                            </div>
                                                            <div className={style.ppConveyorMeta}>
                                                                <span className={style.ppConveyorCount}>{row.countText}</span>
                                                                <span className={style.ppConveyorDetail}>
                                                                    {row.detailText || 'warming up'}
                                                                    {row.queueDepth != null && row.queueMax != null && (
                                                                        <span className={style.ppConveyorQueueTag}>
                                                                            q {formatInteger(row.queueDepth)}/{formatInteger(row.queueMax)}
                                                                        </span>
                                                                    )}
                                                                </span>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                                {processedFrames != null && (
                                                    <div className={style.ppConveyorFrameCount}>
                                                        {processedFrames.toLocaleString()} frames processed
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                </li>
                            )
                        })}
                    </ol>

                    {result?.summary && (
                        <div className={style.ppFacts}>
                            <span>
                                <span className={style.ppFactLabel}>Reps</span>
                                <strong className={style.ppFactValue}>{result.summary.repCount ?? '—'}</strong>
                            </span>
                            <span>
                                <span className={style.ppFactLabel}>Detection</span>
                                <strong className={style.ppFactValue}>
                                    {result.summary.detectionRatio != null
                                        ? `${Math.round(result.summary.detectionRatio * 100)}%`
                                        : '—'}
                                </strong>
                            </span>
                            <span>
                                <span className={style.ppFactLabel}>Sampled FPS</span>
                                <strong className={style.ppFactValue}>
                                    {result.summary.sampledFps != null
                                        ? Number(result.summary.sampledFps).toFixed(3)
                                        : skeletonPage?.fps != null
                                            ? Number(skeletonPage.fps).toFixed(3)
                                            : '—'}
                                </strong>
                            </span>
                        </div>
                    )}

                    {status === 'error' && jobMeta.error && (
                        <div className={style.bmSection}>
                            <span className={style.bmSectionTitle}>Error Detail</span>
                            <div className={style.bmErrorRow}>
                                <span className={style.bmErrorCode}>{jobMeta.error.code}</span>
                                <span className={style.bmErrorMessage}>{jobMeta.error.message}</span>
                            </div>
                        </div>
                    )}

                    {bm && (
                        <div className={style.bmSection}>
                            <span className={style.bmSectionTitle}>Benchmark</span>

                            {/* Quality — 실패 원인의 1순위 */}
                            {bmQuality && (
                                <div className={style.bmSubSection}>
                                    <span className={style.bmSubTitle}>Quality</span>
                                    <dl className={style.bmRows}>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Analysis success</dt>
                                            <dd className={`${style.bmValue} ${!bmQuality.analysisSuccess ? style.bmValueWarn : ''}`}>
                                                {bmQuality.analysisSuccess ? 'yes' : 'NO — analysis did not complete'}
                                            </dd>
                                        </div>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Pose detected</dt>
                                            <dd className={`${style.bmValue} ${bmQuality.poseDetectedRatio < 0.5 ? style.bmValueWarn : ''}`}>
                                                {formatPct(bmQuality.poseDetectedRatio)}
                                                <span className={style.bmDim}>{bmQuality.detectedFrameCount} / {bmRun?.frameCount ?? '?'} frames</span>
                                            </dd>
                                        </div>
                                        {bmQuality.avgVisibility != null && (
                                            <div className={style.bmRow}>
                                                <dt className={style.bmLabel}>Avg visibility</dt>
                                                <dd className={`${style.bmValue} ${bmQuality.avgVisibility < 0.5 ? style.bmValueWarn : ''}`}>
                                                    {bmQuality.avgVisibility.toFixed(3)}
                                                    {bmQuality.minVisibility != null && (
                                                        <span className={style.bmDim}>min {bmQuality.minVisibility.toFixed(3)}</span>
                                                    )}
                                                </dd>
                                            </div>
                                        )}
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Low vis. frames</dt>
                                            <dd className={`${style.bmValue} ${bmQuality.lowVisibilityFrameRatio > 0.4 ? style.bmValueWarn : ''}`}>
                                                {formatPct(bmQuality.lowVisibilityFrameRatio)}
                                            </dd>
                                        </div>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Max consec. missed</dt>
                                            <dd className={`${style.bmValue} ${bmQuality.consecutiveMissedPoseMax > 30 ? style.bmValueWarn : ''}`}>
                                                {bmQuality.consecutiveMissedPoseMax} frames
                                            </dd>
                                        </div>
                                    </dl>
                                </div>
                            )}

                            {/* Run — delegate, model, frame 설정 */}
                            {bmRun && (
                                <div className={style.bmSubSection}>
                                    <span className={style.bmSubTitle}>Run</span>
                                    <dl className={style.bmRows}>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Delegate</dt>
                                            <dd className={`${style.bmValue} ${bmRun.delegateFallbackApplied ? style.bmValueWarn : ''}`}>
                                                {bmRun.requestedDelegate} → {bmRun.actualDelegate}
                                                {bmRun.delegateFallbackApplied && <span className={style.bmFallbackTag}>fallback</span>}
                                            </dd>
                                        </div>
                                        {bmRun.delegateErrors && Object.keys(bmRun.delegateErrors).length > 0 && (
                                            <div className={`${style.bmRow} ${style.bmRowStack}`}>
                                                <dt className={`${style.bmLabel} ${style.bmValueWarn}`}>Delegate errors</dt>
                                                <dd className={style.bmDelegateErrors}>
                                                    {Object.entries(bmRun.delegateErrors).map(([k, v]) => (
                                                        <div key={k} className={style.bmDelegateError}>
                                                            <span className={style.bmValueWarn}>{k}:</span> {v}
                                                        </div>
                                                    ))}
                                                </dd>
                                            </div>
                                        )}
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Model</dt>
                                            <dd className={style.bmValue}>{bmRun.modelVariant} · {bmRun.inferenceBackend}</dd>
                                        </div>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Frames</dt>
                                            <dd className={style.bmValue}>
                                                {bmRun.frameCount}
                                                <span className={style.bmDim}>@ {bmRun.effectiveSamplingFps} fps · {formatMs(bmRun.sampleIntervalMs)}/frame</span>
                                            </dd>
                                        </div>
                                        {bmRun.requestedSamplingFps != null && bmRun.requestedSamplingFps !== bmRun.effectiveSamplingFps && (
                                            <div className={style.bmRow}>
                                                <dt className={`${style.bmLabel} ${style.bmValueWarn}`}>Sampling fps mismatch</dt>
                                                <dd className={`${style.bmValue} ${style.bmValueWarn}`}>
                                                    requested {bmRun.requestedSamplingFps} → effective {bmRun.effectiveSamplingFps}
                                                </dd>
                                            </div>
                                        )}
                                    </dl>
                                </div>
                            )}

                            {/* Timing — 각 단계 소요 시간 + 점유율 */}
                            {startupRows.length > 0 && (
                                <div className={style.bmSubSection}>
                                    <span className={style.bmSubTitle}>Startup Breakdown</span>
                                    <dl className={style.bmRows}>
                                        {startupRows.map(([detailLabel, value, hint]) => (
                                            <div key={detailLabel} className={style.bmRow}>
                                                <dt className={style.bmLabel}>{detailLabel}</dt>
                                                <dd className={style.bmValue}>
                                                    {typeof value === 'number' && detailLabel === 'First chunk span'
                                                        ? `${formatInteger(value)} samples`
                                                        : formatMs(value)}
                                                    {hint && <span className={style.bmDim}>{hint}</span>}
                                                </dd>
                                            </div>
                                        ))}
                                    </dl>
                                </div>
                            )}

                            {pipelineSummary && (
                                <div className={style.bmSubSection}>
                                    <span className={style.bmSubTitle}>Pipeline Summary</span>
                                    <dl className={style.bmRows}>
                                        {pipelineSummary.estimatedTotalFrames != null && (
                                            <div className={style.bmRow}>
                                                <dt className={style.bmLabel}>Estimated total</dt>
                                                <dd className={style.bmValue}>{formatInteger(pipelineSummary.estimatedTotalFrames)} frames</dd>
                                            </div>
                                        )}
                                        {pipelineRows.map((row) => (
                                            <div key={row.key} className={style.bmRow}>
                                                <dt className={style.bmLabel}>{row.title}</dt>
                                                <dd className={style.bmValue}>
                                                    {row.countText}
                                                    {row.detailText && <span className={style.bmDim}>{row.detailText}</span>}
                                                </dd>
                                            </div>
                                        ))}
                                    </dl>
                                </div>
                            )}

                            {bmTiming?.stageStats?.length > 0 && (
                                <div className={style.bmSubSection}>
                                    <span className={style.bmSubTitle}>Timing — total {formatMs(bmTiming.totalElapsedMs)}</span>
                                    <div className={style.bmTimingList}>
                                        {bmTiming.stageStats.map(stage => (
                                            <div key={stage.key} className={style.bmTimingRow}>
                                                <span className={style.bmTimingLabel}>{stage.label}</span>
                                                <div className={style.bmTimingBarWrap} title={`${formatPct(stage.shareRatio)}`}>
                                                    <div className={style.bmTimingBar} style={{ width: `${Math.round(stage.shareRatio * 100)}%` }} />
                                                </div>
                                                <span className={style.bmTimingTotal}>{formatMs(stage.totalMs)}</span>
                                                <span className={style.bmDim}>{formatPct(stage.shareRatio)}</span>
                                                {stage.averageMs != null && (
                                                    <span className={`${style.bmTimingDetail} ${style.bmDim}`}>
                                                        avg {formatMs(stage.averageMs)} · p95 {formatMs(stage.p95Ms)}
                                                    </span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* LLM Call */}
                            {bmLlm && (
                                <div className={style.bmSubSection}>
                                    <span className={style.bmSubTitle}>LLM Call</span>
                                    <dl className={style.bmRows}>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Model</dt>
                                            <dd className={`${style.bmValue} ${!bmLlm.enabled ? style.bmValueWarn : ''}`}>
                                                {bmLlm.model ?? '—'}
                                                {!bmLlm.enabled && <span className={style.bmFallbackTag}>disabled</span>}
                                                {bmLlm.fallbackApplied && <span className={style.bmFallbackTag}>fallback</span>}
                                            </dd>
                                        </div>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Tokens</dt>
                                            <dd className={style.bmValue}>
                                                {bmLlm.inputTokens.toLocaleString()} in · {bmLlm.outputTokens.toLocaleString()} out
                                            </dd>
                                        </div>
                                        <div className={style.bmRow}>
                                            <dt className={style.bmLabel}>Latency</dt>
                                            <dd className={style.bmValue}>{formatMs(bmLlm.latencyMs)}</dd>
                                        </div>
                                        {bmLlmPrompt && (
                                            <div className={style.bmRow}>
                                                <dt className={style.bmLabel}>Prompt reduction</dt>
                                                <dd className={style.bmValue}>
                                                    {formatPct(bmLlmPrompt.reductionRatio)}
                                                    <span className={style.bmDim}>{bmLlmPrompt.payloadApproxTokens.toLocaleString()} tokens sent</span>
                                                </dd>
                                            </div>
                                        )}
                                    </dl>
                                </div>
                            )}

                            {/* Raw JSON — frameMetrics 제외 */}
                            {bmRaw && (
                                <details className={style.bmRawDetails}>
                                    <summary className={style.bmRawSummary}>
                                        Raw JSON
                                        {bmRaw.frameMetrics?.length > 0 && (
                                            <span className={style.bmDim}>(frameMetrics [{bmRaw.frameMetrics.length}] omitted)</span>
                                        )}
                                        <button
                                            className={style.bmRawCopyBtn}
                                            onClick={(e) => {
                                                e.preventDefault()
                                                e.stopPropagation()
                                                navigator.clipboard.writeText(
                                                    JSON.stringify({ ...bmRaw, frameMetrics: undefined }, null, 2)
                                                ).then(() => {
                                                    setBmRawCopied(true)
                                                    setTimeout(() => setBmRawCopied(false), 2000)
                                                })
                                            }}
                                        >
                                            {bmRawCopied ? 'Copied!' : 'Copy'}
                                        </button>
                                    </summary>
                                    <pre className={style.bmRawPre}>
                                        {JSON.stringify({ ...bmRaw, frameMetrics: undefined }, null, 2)}
                                    </pre>
                                </details>
                            )}
                        </div>
                    )}

                    {canFetchBenchmark && (
                        <button
                            type="button"
                            className={style.bmFetchBtn}
                            onClick={handleFetchBenchmark}
                            disabled={isFetchingBenchmark}
                        >
                            {isFetchingBenchmark ? 'Loading…' : 'Load Benchmark'}
                        </button>
                    )}
                </>
            )}
        </div>
    )
}

const PRESET_PAIRS = [
    {
        id: 'hd_2min',
        label: 'HD 2min',
        description: 'hd_00_21_2min + hd_00_11_2min',
        presetIdA: 'hd_00_21_2min',
        presetIdB: 'hd_00_11_2min',
    },
]

export default function CoreDemoSection({ synthesisSession }) {
    const { form, isActive, status, userMessage } = synthesisSession

    const hasBothVideos = Boolean(form.videoFileA && form.videoFileB)
    const hasBothPresets = Boolean(form.presetIdA && form.presetIdB)
    const hasAnyVideo = Boolean(form.videoFileA) || Boolean(form.videoFileB)
    const hasAnyInput = hasBothVideos || hasBothPresets

    const handleSelectPreset = (pair) => {
        synthesisSession.updateForm('videoFileA', null)
        synthesisSession.updateForm('videoFileB', null)
        synthesisSession.updateForm('presetIdA', pair.presetIdA)
        synthesisSession.updateForm('presetIdB', pair.presetIdB)
    }

    const handleClearPreset = () => {
        synthesisSession.updateForm('presetIdA', null)
        synthesisSession.updateForm('presetIdB', null)
    }

    const handleVideoSelect = (key, file) => {
        synthesisSession.updateForm(key, file)
        const presetKey = key === 'videoFileA' ? 'presetIdA' : 'presetIdB'
        synthesisSession.updateForm(presetKey, null)
    }

    const startButtonLabel = isActive
        ? 'Synthesizing...'
        : status === 'completed'
            ? 'Re-run Synthesis'
            : 'Start Synthesis'

    const activePair = hasBothPresets
        ? PRESET_PAIRS.find(p => p.presetIdA === form.presetIdA)
        : null

    return (
        <SectionContainer
            id="coreDemo"
            heading='CORE DEMO'
            description='Upload two videos and run the unified synthesis pipeline — 2D pose inference, 3D triangulation, and biomechanical analysis in a single job.'
        >
            <div className={style.contents}>
                <div className={style.primaryGrid}>
                    <Panel icon={UploadIcon} label="Synthesis Settings" id="analysisSettingsPanel" tabIndex={-1} containerClassName={hasAnyInput ? style.settingsPanelExpanded : ''}>
                        <div className={style.panelContent}>
                            {!hasBothPresets && (
                                <div className={style.videoUploadRow}>
                                    <div className={style.videoUploadCol}>
                                        <span className={style.videoLabel}>Video A</span>
                                        <VideoUpload
                                            file={form.videoFileA}
                                            onFileSelect={(file) => handleVideoSelect('videoFileA', file)}
                                        />
                                    </div>
                                    <div className={style.videoUploadCol}>
                                        <span className={style.videoLabel}>Video B</span>
                                        <VideoUpload
                                            file={form.videoFileB}
                                            onFileSelect={(file) => handleVideoSelect('videoFileB', file)}
                                        />
                                    </div>
                                </div>
                            )}

                            {!hasAnyVideo && !hasBothPresets && (
                                <div className={style.presetSection}>
                                    <div className={style.presetDivider}><span>or use preset estimation JSON</span></div>
                                    <div className={style.presetOptions}>
                                        {PRESET_PAIRS.map(pair => (
                                            <button
                                                key={pair.id}
                                                type="button"
                                                className={style.presetButton}
                                                onClick={() => handleSelectPreset(pair)}
                                            >
                                                <span className={style.presetButtonLabel}>{pair.label}</span>
                                                <span className={style.presetButtonDesc}>{pair.description}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {hasAnyVideo && (
                                <div className={style.uploadDetails}>
                                    {userMessage && (
                                        <div className={style.errorBox}>{userMessage}</div>
                                    )}
                                    <Button
                                        label={startButtonLabel}
                                        width="100%"
                                        height="5.2rem"
                                        onClick={synthesisSession.startSynthesis}
                                        disabled={isActive || !hasBothVideos}
                                    />
                                </div>
                            )}

                            {hasBothPresets && (
                                <div className={style.presetActive}>
                                    <div className={style.presetActiveInfo}>
                                        <span className={style.presetActiveLabel}>Preset JSON</span>
                                        <span className={style.presetActiveName}>
                                            {activePair ? activePair.description : `${form.presetIdA} + ${form.presetIdB}`}
                                        </span>
                                        <button
                                            type="button"
                                            className={style.presetClearBtn}
                                            onClick={handleClearPreset}
                                            disabled={isActive}
                                        >
                                            Change
                                        </button>
                                    </div>

                                    {userMessage && (
                                        <div className={style.errorBox}>{userMessage}</div>
                                    )}

                                    <Button
                                        label={startButtonLabel}
                                        width="100%"
                                        height="5.2rem"
                                        onClick={synthesisSession.startSynthesis}
                                        disabled={isActive}
                                    />
                                </div>
                            )}
                        </div>
                    </Panel>

                    <Panel icon={SettingIcon} label="Pipeline Progress" containerClassName={style.progressPanelContainer} bodyClassName={style.progressPanelBody}>
                        <div className={style.dualProgressContent}>
                            <SynthSharedColumn synthesisSession={synthesisSession} />
                        </div>
                    </Panel>
                </div>
            </div>
        </SectionContainer>
    )
}
