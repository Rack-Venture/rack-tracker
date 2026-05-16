import { useCallback, useEffect, useRef, useState } from 'react'
import {
    createStreamingSynthesisJob,
    getSynthesisJobStatus,
    getSynthesisResult,
    getSynthesisSkeleton3D,
    getSkeletonAPage,
    getSkeletonBPage,
    uploadSynthesisVideo,
    DEFAULT_SKELETON3D_PAGE_LIMIT,
} from '../../api/analysisClient.js'

const SYNTH_ACTIVE_STATUSES = new Set(['uploading', 'queued', 'initializing', 'streaming', 'writing_artifacts'])

const DEFAULT_FORM = {
    videoFileA: null,
    videoFileB: null,
    presetIdA: null,
    presetIdB: null,
    cameraIdA: '00_21',
    cameraIdB: '00_11',
    calibrationRef: '171204_pose1/171204_pose1/calibration_171204_pose1.json',
}

const INITIAL_STATE = {
    status: 'idle',
    form: DEFAULT_FORM,
    jobId: null,
    progress: null,
    error: null,
    result: null,
    skeleton3d: null,
    skeletonA: null,
    skeletonB: null,
    startedAt: null,
    now: Date.now(),
    userMessage: '',
}

export function useSynthesisSession() {
    const [state, setState] = useState(INITIAL_STATE)
    const runRef = useRef({ runId: 0, pollIntervalId: null, abortController: null })

    const clearRun = useCallback(() => {
        if (runRef.current.pollIntervalId != null) {
            window.clearInterval(runRef.current.pollIntervalId)
            runRef.current.pollIntervalId = null
        }
        runRef.current.abortController?.abort()
        runRef.current.abortController = null
    }, [])

    useEffect(() => () => clearRun(), [clearRun])

    useEffect(() => {
        if (!SYNTH_ACTIVE_STATUSES.has(state.status)) return undefined
        const id = window.setInterval(() => {
            setState(prev => ({ ...prev, now: Date.now() }))
        }, 500)
        return () => window.clearInterval(id)
    }, [state.status])

    const updateForm = useCallback((key, value) => {
        setState(prev => ({ ...prev, form: { ...prev.form, [key]: value } }))
    }, [])

    const fetchCompletedArtifacts = useCallback(async (jobId, runId) => {
        runRef.current.abortController = new AbortController()
        const signal = runRef.current.abortController.signal
        try {
            const [result, skeleton3d, skeletonA, skeletonB] = await Promise.allSettled([
                getSynthesisResult(jobId, { signal }),
                getSynthesisSkeleton3D(jobId, { signal }),
                getSkeletonAPage(jobId, 0, DEFAULT_SKELETON3D_PAGE_LIMIT, { signal }),
                getSkeletonBPage(jobId, 0, DEFAULT_SKELETON3D_PAGE_LIMIT, { signal }),
            ])
            if (runId !== runRef.current.runId) return
            setState(prev => ({
                ...prev,
                status: 'completed',
                result: result.status === 'fulfilled' ? result.value : null,
                skeleton3d: skeleton3d.status === 'fulfilled' ? skeleton3d.value : null,
                skeletonA: skeletonA.status === 'fulfilled' ? skeletonA.value : null,
                skeletonB: skeletonB.status === 'fulfilled' ? skeletonB.value : null,
                now: Date.now(),
            }))
        } catch {
            // non-fatal: job completed, artifact fetch failed
        }
    }, [])

    const pollJob = useCallback((jobId, runId) => {
        runRef.current.pollIntervalId = window.setInterval(async () => {
            if (runId !== runRef.current.runId) {
                clearRun()
                return
            }
            try {
                const payload = await getSynthesisJobStatus(jobId)
                if (runId !== runRef.current.runId) return

                const rawStatus = payload?.status ?? 'unknown'
                const isFailed = rawStatus === 'failed'

                setState(prev => ({
                    ...prev,
                    status: isFailed ? 'error' : rawStatus,
                    progress: payload?.progress ?? null,
                    error: payload?.error ?? null,
                    now: Date.now(),
                }))

                if (rawStatus === 'completed') {
                    clearRun()
                    void fetchCompletedArtifacts(jobId, runId)
                } else if (isFailed) {
                    clearRun()
                    setState(prev => ({
                        ...prev,
                        userMessage: payload?.error?.message || 'Synthesis job failed.',
                    }))
                }
            } catch {
                // polling error — retry on next interval
            }
        }, 1000)
    }, [clearRun, fetchCompletedArtifacts])

    const startSynthesis = useCallback(async () => {
        const form = state.form
        const hasVideos = Boolean(form.videoFileA && form.videoFileB)
        const hasPresets = Boolean(form.presetIdA && form.presetIdB)

        if (!hasVideos && !hasPresets) return

        clearRun()
        const runId = runRef.current.runId + 1
        runRef.current.runId = runId
        const startedAt = Date.now()

        setState(prev => ({
            ...prev,
            status: 'uploading',
            jobId: null,
            progress: null,
            error: null,
            result: null,
            skeleton3d: null,
            skeletonA: null,
            skeletonB: null,
            startedAt,
            now: startedAt,
            userMessage: '',
        }))

        try {
            let sourceA, sourceB

            if (hasVideos) {
                const [uploadA, uploadB] = await Promise.all([
                    uploadSynthesisVideo(form.videoFileA),
                    uploadSynthesisVideo(form.videoFileB),
                ])
                if (runId !== runRef.current.runId) return
                sourceA = { videoPath: uploadA.videoPath, cameraId: form.cameraIdA }
                sourceB = { videoPath: uploadB.videoPath, cameraId: form.cameraIdB }
            } else {
                sourceA = { presetEstimationId: form.presetIdA, cameraId: form.cameraIdA }
                sourceB = { presetEstimationId: form.presetIdB, cameraId: form.cameraIdB }
            }

            const jobResponse = await createStreamingSynthesisJob({
                sourceA,
                sourceB,
                calibrationRef: form.calibrationRef,
            })
            if (runId !== runRef.current.runId) return

            const jobId = jobResponse?.jobId
            if (!jobId) throw new Error('Backend did not return a jobId.')

            setState(prev => ({
                ...prev,
                status: 'queued',
                jobId,
                now: Date.now(),
            }))

            pollJob(jobId, runId)
        } catch (err) {
            if (runId !== runRef.current.runId) return
            clearRun()
            setState(prev => ({
                ...prev,
                status: 'error',
                error: { code: 'request_error', message: err?.message ?? 'Request error' },
                userMessage: err?.message ?? 'Synthesis request failed.',
                now: Date.now(),
            }))
        }
    }, [clearRun, pollJob, state.form])

    return {
        ...state,
        isActive: SYNTH_ACTIVE_STATUSES.has(state.status),
        updateForm,
        startSynthesis,
    }
}
