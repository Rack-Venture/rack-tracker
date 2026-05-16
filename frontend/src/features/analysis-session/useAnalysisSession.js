import { startTransition, useCallback, useEffect, useRef, useState } from 'react'
import { createJob, DEFAULT_SKELETON_PAGE_LIMIT, downloadSkeletonFile, getBenchmark, getJobResult, getSkeletonPage, openJobStream } from '../../api/analysisClient.js'
import { adaptJobStatus, adaptResult, adaptSkeletonPage } from './adapters.js'

const ACTIVE_STATUSES = new Set([
    'uploading',
    'queued',
    'initializing_landmarker',
    'analyzing',
    'computing',
    'generating_feedback',
])

const DEFAULT_FORM = {
    videoFile: null,
    samplingFps: null,
    // General motion experiment mode — exercise-specific fields are omitted
    // Squat defaults preserved as comments for when squat pipeline is restored:
    // exerciseType: 'squat',
    // bodyweightKg: 73,
    // externalLoadKg: 260,
    // barPlacementMode: 'high_bar',
    modelAssetPath: '',
    modelVariant: 'full',
    delegate: 'CPU',
    presetEstimationId: null,
}

const DEFAULT_VIZ_CONFIG = {
    showSkeleton: true,
    showJointLabels: false,
    showAngleOverlay: false,
    showJointLoad: false,
    showIssueMarkers: true,
    showRepBoundaries: true,
    showEventMarkers: true,
    showPathTrace: false,
    showConfidenceTint: false,
    showBarPass: false,
    showGroundVector: false,
    showCoP: false,
}

const INITIAL_STATE = {
    status: 'idle',
    form: DEFAULT_FORM,
    vizConfig: DEFAULT_VIZ_CONFIG,
    jobMeta: {
        jobId: null,
        progress: null,
        error: null,
    },
    videoPath: null,
    result: null,
    skeletonPage: null,
    benchmarkDetails: null,
    validationError: '',
    userMessage: '',
    stageMoments: {},
    startedAt: null,
    now: Date.now(),
}

function sanitizeNumber(value) {
    if (value === '' || value == null) return null
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
}

function buildUserError(error) {
    if (error?.status === 404) return 'Analysis session not found. Start a new run.'
    if (error?.status === 409) return 'Results are not ready yet. Polling will continue until the backend completes.'
    return error?.message || 'Analysis request failed. Check the backend and try again.'
}


function mergeSkeletonPagePayload(previous, page) {
    if (!previous) return page
    if (!page) return previous

    const previousFrames = Array.isArray(previous.frames) ? previous.frames : []
    const nextFrames = Array.isArray(page.frames) ? page.frames : []
    const pageOffset = Number.isFinite(page?.offset) ? page.offset : previousFrames.length
    const totalFrames = Number.isFinite(page?.totalFrames)
        ? page.totalFrames
        : Math.max(previousFrames.length, pageOffset + nextFrames.length)
    const mergedFrames = previousFrames.slice(0, Math.max(totalFrames, previousFrames.length))

    nextFrames.forEach((frame, index) => {
        mergedFrames[pageOffset + index] = frame
    })

    const compactFrames = mergedFrames.filter(Boolean)

    return {
        ...previous,
        ...page,
        frames: compactFrames,
        offset: 0,
        limit: compactFrames.length,
        totalFrames,
    }
}

function mergeAdaptedSkeletonPage(previous, next) {
    if (!previous) return next
    if (!next) return previous

    const frames = previous.frames.slice()
    next.frames.forEach((frame, index) => {
        frames[(next.offset ?? frames.length) + index] = frame
    })

    const compactFrames = frames.filter(Boolean)
    return {
        ...previous,
        raw: mergeSkeletonPagePayload(previous.raw, next.raw),
        frames: compactFrames,
        timestamps: compactFrames.map(frame => frame.timestampMs),
        totalFrames: next.totalFrames ?? previous.totalFrames ?? compactFrames.length,
        limit: compactFrames.length,
        durationMs: Math.max(previous.durationMs ?? 0, next.durationMs ?? 0),
        frameMetricsByIndex: {
            ...(previous.frameMetricsByIndex ?? {}),
            ...(next.frameMetricsByIndex ?? {}),
        },
    }
}

function yieldToBrowser() {
    return new Promise(resolve => {
        if (typeof window.requestIdleCallback === 'function') {
            window.requestIdleCallback(resolve, { timeout: 120 })
            return
        }
        window.setTimeout(resolve, 16)
    })
}

export function useAnalysisSession() {
    const [state, setState] = useState(INITIAL_STATE)
    const runRef = useRef({
        runId: 0,
        eventSource: null,
        abortController: null,
    })

    const clearRun = useCallback(() => {
        runRef.current.eventSource?.close()
        runRef.current.eventSource = null
        runRef.current.abortController?.abort()
        runRef.current.abortController = null
    }, [])

    useEffect(() => () => clearRun(), [clearRun])

    useEffect(() => {
        if (!ACTIVE_STATUSES.has(state.status)) return undefined

        const intervalId = window.setInterval(() => {
            setState(prev => ({ ...prev, now: Date.now() }))
        }, 250)

        return () => window.clearInterval(intervalId)
    }, [state.status])

    const markStage = useCallback((stage) => {
        setState(prev => {
            if (!stage || prev.stageMoments[stage]) {
                return { ...prev, now: Date.now() }
            }

            return {
                ...prev,
                stageMoments: {
                    ...prev.stageMoments,
                    [stage]: Date.now(),
                },
                now: Date.now(),
            }
        })
    }, [])

    const updateForm = useCallback((key, value) => {
        setState(prev => ({
            ...prev,
            form: {
                ...prev.form,
                [key]: value,
            },
            validationError: '',
            userMessage: '',
        }))
    }, [])

    const updateVizConfig = useCallback((key, value) => {
        setState(prev => ({
            ...prev,
            vizConfig: {
                ...prev.vizConfig,
                [key]: value,
            },
        }))
    }, [])

    const hydrateResult = useCallback((resultPayload, skeletonPayload, benchmarkPayload = null) => {
        const adaptedResult = adaptResult(resultPayload, benchmarkPayload)
        const adaptedSkeleton = adaptSkeletonPage(skeletonPayload, adaptedResult)

        setState(prev => ({
            ...prev,
            status: 'completed',
            jobMeta: {
                ...prev.jobMeta,
                progress: {
                    stage: 'completed',
                    currentStep: 6,
                    totalSteps: 6,
                    ratio: 1,
                    processedFrames: adaptedSkeleton?.totalFrames ?? null,
                    totalFrames: adaptedSkeleton?.totalFrames ?? null,
                },
                error: null,
            },
            result: adaptedResult,
            skeletonPage: adaptedSkeleton,
            benchmarkDetails: benchmarkPayload ?? adaptedResult.benchmark ?? null,
            userMessage: '',
            now: Date.now(),
        }))
    }, [])

    const appendSkeletonPage = useCallback((skeletonPayload, resultPayload, runId) => {
        const adaptedResult = adaptResult(resultPayload)
        const adaptedSkeleton = adaptSkeletonPage(skeletonPayload, adaptedResult)

        startTransition(() => {
            setState(prev => {
                if (runId !== runRef.current.runId || prev.status !== 'completed') return prev

                const mergedSkeleton = mergeAdaptedSkeletonPage(prev.skeletonPage, adaptedSkeleton)
                return {
                    ...prev,
                    skeletonPage: mergedSkeleton,
                    jobMeta: {
                        ...prev.jobMeta,
                        progress: {
                            ...(prev.jobMeta.progress ?? {}),
                            stage: 'completed',
                            processedFrames: mergedSkeleton.frames.length,
                            totalFrames: mergedSkeleton.totalFrames ?? mergedSkeleton.frames.length,
                        },
                    },
                    now: Date.now(),
                }
            })
        })
    }, [])

    const loadRemainingSkeletonPages = useCallback(async (jobId, firstPage, resultPayload, runId, signal) => {
        const frames = Array.isArray(firstPage?.frames) ? firstPage.frames : []
        const firstOffset = Number.isFinite(firstPage?.offset) ? firstPage.offset : 0
        const totalFrames = Number.isFinite(firstPage?.totalFrames) ? firstPage.totalFrames : null
        let offset = firstOffset + frames.length

        while (!signal?.aborted && frames.length && (totalFrames == null || offset < totalFrames)) {
            await yieldToBrowser()
            const page = await getSkeletonPage(jobId, offset, DEFAULT_SKELETON_PAGE_LIMIT, { signal })
            if (runId !== runRef.current.runId) return

            const pageFrames = Array.isArray(page?.frames) ? page.frames : []
            const pageOffset = Number.isFinite(page?.offset) ? page.offset : offset
            const nextOffset = pageOffset + pageFrames.length
            if (!pageFrames.length || nextOffset <= offset) return

            await yieldToBrowser()
            appendSkeletonPage(page, resultPayload, runId)
            offset = nextOffset
        }
    }, [appendSkeletonPage])

    const loadBenchmark = useCallback(async (jobId, runId = runRef.current.runId) => {
        try {
            const benchmarkPayload = await getBenchmark(jobId)
            if (runId !== runRef.current.runId) return

            setState(prev => {
                if (!prev.result) {
                    return {
                        ...prev,
                        benchmarkDetails: benchmarkPayload,
                    }
                }

                const adaptedResult = adaptResult(prev.result.raw, benchmarkPayload)
                return {
                    ...prev,
                    result: adaptedResult,
                    benchmarkDetails: benchmarkPayload,
                    // skeletonPage는 timeseries/repSegments/timelineMarkers에만 의존하며
                    // benchmark 도착 시 변하지 않으므로 재계산 생략
                }
            })
        } catch {
            // Benchmark is optional.
        }
    }, [])

    const streamJob = useCallback((jobId, runId) => {
        const es = openJobStream(jobId)
        runRef.current.eventSource = es

        es.onmessage = async (event) => {
            if (runId !== runRef.current.runId) {
                es.close()
                return
            }

            let statusPayload
            try {
                statusPayload = JSON.parse(event.data)
            } catch {
                return
            }

            const job = adaptJobStatus(statusPayload)
            if (job.rawStatus) markStage(job.rawStatus)

            setState(prev => ({
                ...prev,
                // completed는 result/skeletonPage와 동시에 hydrateResult에서 설정.
                // 여기서 먼저 설정하면 데이터 없는 'completed' 상태가 노출됨.
                ...(job.rawStatus !== 'completed' && { status: job.status }),
                jobMeta: {
                    jobId,
                    progress: job.progress,
                    error: job.error,
                },
                userMessage: job.status === 'error'
                    ? buildUserError({ message: job.error?.message })
                    : '',
                now: Date.now(),
            }))

            if (job.rawStatus === 'completed') {
                es.close()
                runRef.current.eventSource = null
                runRef.current.abortController = new AbortController()
                const signal = runRef.current.abortController.signal
                try {
                    const [resultPayload, skeletonPayload] = await Promise.all([
                        getJobResult(jobId, { signal }),
                        getSkeletonPage(jobId, 0, DEFAULT_SKELETON_PAGE_LIMIT, { signal }),
                    ])
                    if (runId !== runRef.current.runId) return
                    markStage('completed')
                    hydrateResult(resultPayload, skeletonPayload)
                    loadBenchmark(jobId, runId)
                    void loadRemainingSkeletonPages(jobId, skeletonPayload, resultPayload, runId, signal).catch(error => {
                        if (error?.name === 'AbortError' || runId !== runRef.current.runId) return
                        setState(prev => ({
                            ...prev,
                            userMessage: prev.userMessage || 'Skeleton frames are still partially loaded. Try re-running if playback is incomplete.',
                        }))
                    })
                } catch (error) {
                    if (error?.name === 'AbortError' || runId !== runRef.current.runId) return
                    setState(prev => ({
                        ...prev,
                        status: 'error',
                        userMessage: buildUserError(error),
                        jobMeta: {
                            ...prev.jobMeta,
                            error: {
                                code: String(error?.status ?? 'network_error'),
                                message: error?.message ?? 'Network error',
                            },
                        },
                    }))
                }
                return
            }

            if (job.rawStatus === 'failed') {
                es.close()
                runRef.current.eventSource = null
                setState(prev => ({
                    ...prev,
                    status: 'error',
                    userMessage: buildUserError({ message: job.error?.message }),
                }))
                loadBenchmark(jobId, runId)
            }
        }

        es.onerror = () => {
            if (runId !== runRef.current.runId) return
            if (es.readyState === EventSource.CLOSED) {
                clearRun()
                setState(prev => ({
                    ...prev,
                    status: 'error',
                    userMessage: 'Stream connection failed.',
                    jobMeta: {
                        ...prev.jobMeta,
                        error: { code: 'stream_error', message: 'Stream connection failed.' },
                    },
                }))
            }
            // readyState === CONNECTING: 브라우저가 자동 재연결 중 — 대기
        }
    }, [clearRun, hydrateResult, loadBenchmark, loadRemainingSkeletonPages, markStage])

    const startAnalysis = useCallback(async () => {
        const form = state.form

        if (!form.videoFile && !form.presetEstimationId) {
            setState(prev => ({ ...prev, validationError: 'Upload a video or select a preset estimation JSON.' }))
            return
        }

        // General motion experiment mode: no exercise-specific validation
        // Squat validation preserved as comments for when squat pipeline is restored:
        // if (form.exerciseType !== 'squat') { ... }
        // if (bodyweightKg == null || bodyweightKg <= 0) { ... }
        // if (externalLoadKg == null || externalLoadKg < 0) { ... }

        clearRun()
        const runId = runRef.current.runId + 1
        runRef.current.runId = runId
        const sessionStartedAt = Date.now()

        setState(prev => ({
            ...prev,
            status: 'uploading',
            startedAt: sessionStartedAt,
            now: sessionStartedAt,
            validationError: '',
            userMessage: '',
            videoPath: null,
            result: null,
            skeletonPage: null,
            benchmarkDetails: null,
            jobMeta: {
                jobId: null,
                progress: null,
                error: null,
            },
            stageMoments: {
                uploading: sessionStartedAt,
            },
        }))

        try {
            const payload = await createJob(form, form.videoFile)
            if (runId !== runRef.current.runId) return

            markStage(payload?.status ?? 'queued')
            setState(prev => ({
                ...prev,
                status: payload?.status ?? 'queued',
                videoPath: payload?.videoPath ?? null,
                jobMeta: {
                    jobId: payload?.jobId ?? null,
                    progress: payload?.status ? {
                        stage: payload.status,
                        currentStep: 0,
                        totalSteps: 6,
                        ratio: 0,
                        processedFrames: 0,
                        totalFrames: null,
                    } : null,
                    error: null,
                },
            }))

            if (!payload?.jobId) {
                throw new Error('The backend did not return a jobId.')
            }

            streamJob(payload.jobId, runId)
        } catch (error) {
            if (runId !== runRef.current.runId) return
            clearRun()
            setState(prev => ({
                ...prev,
                status: 'error',
                userMessage: buildUserError(error),
                jobMeta: {
                    ...prev.jobMeta,
                    error: {
                        code: String(error?.status ?? 'request_error'),
                        message: error?.message ?? 'Request error',
                    },
                },
            }))
        }
    }, [clearRun, markStage, streamJob, state.form])

    const downloadRawSkeleton = useCallback(async (jobId = state.jobMeta.jobId) => {
        if (!jobId) {
            throw new Error('Skeleton download is unavailable before a job starts.')
        }

        const { blob, fileName } = await downloadSkeletonFile(jobId)
        const objectUrl = window.URL.createObjectURL(blob)
        const anchor = document.createElement('a')

        anchor.href = objectUrl
        anchor.download = fileName
        document.body.appendChild(anchor)
        anchor.click()
        anchor.remove()

        window.setTimeout(() => {
            window.URL.revokeObjectURL(objectUrl)
        }, 0)
    }, [state.jobMeta.jobId])

    return {
        ...state,
        isActive: ACTIVE_STATUSES.has(state.status),
        updateForm,
        updateVizConfig,
        startAnalysis,
        downloadRawSkeleton,
        loadBenchmark: () => state.jobMeta.jobId ? loadBenchmark(state.jobMeta.jobId) : Promise.resolve(),
    }
}
