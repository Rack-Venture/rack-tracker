const STAGE_ORDER = [
    'uploading',
    'queued',
    'initializing_landmarker',
    'analyzing',
    'computing',
    'generating_feedback',
    'completed',
]

const STAGE_LABELS = {
    uploading: 'Upload started',
    queued: 'Queued',
    initializing_landmarker: 'Landmarker init',
    analyzing: 'Streaming pipeline',
    computing: 'Biomechanical analysis',
    generating_feedback: 'Feedback generation',
    completed: 'Completed',
    failed: 'Failed',
    error: 'Error',
}

function asArray(value) {
    return Array.isArray(value) ? value : []
}

function asNumber(value) {
    return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function inferFpsFromFrames(frames) {
    if (frames.length < 2) return 30
    const delta = frames[1].timestampMs - frames[0].timestampMs
    return delta > 0 ? 1000 / delta : 30
}

function toAngleMetrics(timeseries, frameTimestamps) {
    const timestamps = asArray(timeseries?.timestamps_ms)
    if (!timestamps.length || !frameTimestamps.length) {
        return {}
    }

    const sources = [
        ['left_knee_angle',  'left_knee'],
        ['right_knee_angle', 'right_knee'],
        ['left_hip_angle',   'left_hip'],
        ['right_hip_angle',  'right_hip'],
        ['left_elbow_angle', 'left_elbow'],
        ['right_elbow_angle','right_elbow'],
    ].filter(([sourceKey]) => Array.isArray(timeseries?.[sourceKey]))

    if (!sources.length) {
        return {}
    }

    // Both arrays are monotonically increasing — advance a single pointer per frame: O(N + M)
    const result = {}
    let seriesIndex = 0

    for (let frameIndex = 0; frameIndex < frameTimestamps.length; frameIndex++) {
        const target = frameTimestamps[frameIndex]
        while (
            seriesIndex < timestamps.length - 1 &&
            Math.abs(timestamps[seriesIndex + 1] - target) <= Math.abs(timestamps[seriesIndex] - target)
        ) {
            seriesIndex++
        }

        const jointAngles = Object.fromEntries(
            sources
                .map(([sourceKey, targetKey]) => [targetKey, timeseries[sourceKey][seriesIndex]])
                .filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
        )

        result[frameIndex] = { jointAngles }
    }

    return result
}

function toTimelineMarkers(items, durationMs, kind) {
    return asArray(items)
        .filter(item => typeof item?.timestampMs === 'number')
        .map((item, index) => ({
            id: `${kind}-${index}`,
            kind,
            label: item.type ?? item.code ?? `${kind} ${index + 1}`,
            timestampMs: item.timestampMs,
            repIndex: item.repIndex ?? null,
            severity: item.severity ?? null,
            position: durationMs > 0 ? Math.max(0, Math.min(100, (item.timestampMs / durationMs) * 100)) : 0,
            message: item.message ?? null,
        }))
}

export function adaptJobStatus(payload) {
    const status = payload?.status === 'failed' ? 'error' : payload?.status ?? 'idle'
    return {
        jobId: payload?.jobId ?? null,
        status,
        rawStatus: payload?.status ?? 'idle',
        progress: payload?.progress
            ? {
                ...payload.progress,
                stageDetails: payload.progress.stageDetails ?? {},
                processedFrames: payload.progress.processedFrames ?? null,
                totalFrames: payload.progress.totalFrames ?? null,
            }
            : null,
        error: payload?.error ?? null,
    }
}

export function adaptResult(result, benchmarkOverride = null) {
    const analysis = result?.analysis ?? {}
    const llmFeedback = result?.llmFeedback ?? {}
    const benchmark = benchmarkOverride ?? result?.benchmark ?? null
    const skeletonSummary = result?.skeleton ?? {}

    const summary = analysis?.summary ?? {}
    const kpis = asArray(analysis?.kpis)
    const repSegments = asArray(analysis?.repSegments)
    const issues = asArray(analysis?.issues)
    const events = asArray(analysis?.events)
    const durationMs = asNumber(summary.durationMs)
        ?? asNumber(skeletonSummary?.nextTimestampCursorMs)
        ?? 0

    return {
        raw: result,
        skeletonSummary,
        analysis,
        llmFeedback,
        benchmark,
        summary,
        kpis,
        repSegments,
        issues,
        events,
        timeseries: analysis?.timeseries ?? {},
        visualization: analysis?.visualization ?? {},
        llmView: {
            overallComment: llmFeedback?.overallComment?.trim() || 'LLM feedback unavailable.',
            highlights: asArray(llmFeedback?.highlights).filter(Boolean),
            corrections: asArray(llmFeedback?.corrections).filter(Boolean),
            coachCue: llmFeedback?.coachCue?.trim() || 'No coach cue was returned for this session.',
            available: Boolean(llmFeedback?.overallComment?.trim() || asArray(llmFeedback?.highlights).length || asArray(llmFeedback?.corrections).length || llmFeedback?.coachCue?.trim()),
        },
        benchmarkView: benchmark ? {
            requestedDelegate: benchmark?.run?.requestedDelegate ?? 'unknown',
            actualDelegate: benchmark?.run?.actualDelegate ?? 'unknown',
            delegateFallbackApplied: Boolean(benchmark?.run?.delegateFallbackApplied),
            totalElapsedMs: asNumber(benchmark?.timingSummary?.totalElapsedMs),
            poseDetectedRatio: asNumber(benchmark?.qualitySummary?.poseDetectedRatio),
            avgVisibility: asNumber(benchmark?.qualitySummary?.avgVisibility),
            raw: benchmark,
        } : null,
        durationMs,
        timelineMarkers: [
            ...toTimelineMarkers(events, durationMs, 'event'),
            ...toTimelineMarkers(issues, durationMs, 'issue'),
        ],
    }
}

export function adaptSkeletonPage(page, analysis = null) {
    const frames = asArray(page?.frames).map((frame, index) => ({
        frameIndex: typeof frame?.frameIndex === 'number' ? frame.frameIndex : index,
        timestampMs: asNumber(frame?.timestampMs) ?? index * (1000 / 30),
        poseDetected: frame?.poseDetected !== false,
        landmarks: asArray(frame?.landmarks).map((landmark, landmarkIndex) => ({
            name: landmark?.name ?? `landmark_${landmarkIndex}`,
            x: landmark?.x ?? 0,
            y: landmark?.y ?? 0,
            z: landmark?.z ?? 0,
            visibility: landmark?.visibility ?? 1,
            presence: landmark?.presence ?? 1,
        })),
    }))

    const timestamps = frames.map(frame => frame.timestampMs)
    const effectiveFps = asNumber(page?.videoInfo?.effectiveSamplingFps) ?? inferFpsFromFrames(frames)
    const frameMetricsByIndex = toAngleMetrics(analysis?.timeseries, timestamps)
    const summaryDurationMs = analysis?.summary?.durationMs ?? timestamps.at(-1) ?? 0

    return {
        raw: page,
        videoInfo: page?.videoInfo ?? {},
        cameraBinding: page?.cameraBinding ?? page?.videoInfo?.cameraBinding ?? null,
        imageCoordinateSpace: page?.imageCoordinateSpace ?? page?.videoInfo?.imageCoordinateSpace ?? null,
        fps: effectiveFps,
        frames,
        timestamps,
        totalFrames: page?.totalFrames ?? frames.length,
        offset: page?.offset ?? 0,
        limit: page?.limit ?? frames.length,
        durationMs: summaryDurationMs,
        frameMetricsByIndex,
        timelineMarkers: analysis?.timelineMarkers ?? [],
        repSegments: asArray(analysis?.repSegments),
    }
}

function observationVisibility(observations) {
    const values = Object.values(observations ?? {})
        .map(item => item?.visibility)
        .filter(value => typeof value === 'number' && Number.isFinite(value))
    if (!values.length) return null
    return values.reduce((sum, value) => sum + value, 0) / values.length
}

export function adaptSkeleton3DPage(page) {
    const startFrame = asNumber(page?.page?.startFrame) ?? 0
    const synthesisInfo = page?.synthesisInfo ?? {}
    const qualitySummary = page?.qualitySummary ?? {}
    const timeline = page?.timeline ?? {}
    const frames = asArray(page?.frames).map((frame, localIndex) => {
        const joints = asArray(frame?.joints ?? frame?.joints3d)
        const landmarks = []
        joints.forEach((joint, fallbackIndex) => {
            const landmarkIndex = Number.isFinite(joint?.landmarkIndex)
                ? joint.landmarkIndex
                : fallbackIndex
            const position = joint?.position ?? {}
            const x = asNumber(position?.x)
            const y = asNumber(position?.y)
            const z = asNumber(position?.z)
            const hasPosition = x != null && y != null && z != null
            const visibility = observationVisibility(joint?.observations)
            landmarks[landmarkIndex] = {
                name: joint?.name ?? `landmark_${landmarkIndex}`,
                x: x ?? 0,
                y: y ?? 0,
                z: z ?? 0,
                visibility: visibility ?? (joint?.success === false ? 0.25 : 1),
                presence: joint?.success === false ? 0 : 1,
                success: joint?.success !== false,
                failureReason: joint?.failureReason ?? null,
                reprojectionErrorPx: asNumber(joint?.reprojectionErrorPx),
                metric3d: true,
                renderable: hasPosition && joint?.success !== false,
            }
        })
        return {
            frameIndex: asNumber(frame?.frameIndex) ?? startFrame + localIndex,
            timestampMs: asNumber(frame?.timestampMs) ?? (startFrame + localIndex) * (1000 / 30),
            timestampDeltaMs: asNumber(frame?.timestampDeltaMs),
            poseDetected: landmarks.some(landmark => landmark?.success),
            landmarks,
            joints,
            quality: frame?.quality ?? {},
            source: frame?.source ?? {},
            coordinateSystem: synthesisInfo?.coordinateSystem ?? 'panoptic_world_cm',
            viewHint: synthesisInfo?.viewHint ?? null,
            thresholds: synthesisInfo?.thresholds ?? {},
            sourceType: 'skeleton3d',
        }
    })

    return {
        raw: page,
        schemaVersion: page?.schemaVersion ?? 'skeleton3d.v1',
        synthesisInfo,
        qualitySummary,
        fps: asNumber(timeline?.fps) ?? inferFpsFromFrames(frames),
        frames,
        offset: startFrame,
        limit: asNumber(page?.page?.limit) ?? frames.length,
        totalFrames: asNumber(page?.page?.totalFrames) ?? frames.length,
        nextStartFrame: page?.page?.nextStartFrame ?? null,
        durationMs: asNumber(timeline?.durationMs) ?? (frames.at(-1)?.timestampMs ?? 0),
        timelineMarkers: [],
    }
}

export function buildProgressSteps(progress, stageMoments, now) {
    const currentStage = progress?.stage ?? null
    const currentStageIndex = STAGE_ORDER.indexOf(currentStage)
    const stageDurationsMs = progress?.stageDurationsMs ?? {}

    return STAGE_ORDER.map((stage, index) => {
        const serverDurationMs = stageDurationsMs[stage] ?? null
        const startedAt = stageMoments?.[stage] ?? null
        const nextStartedAt = STAGE_ORDER
            .slice(index + 1)
            .map(nextStage => stageMoments?.[nextStage] ?? null)
            .find(Boolean) ?? null

        const elapsedMs = serverDurationMs !== null
            ? serverDurationMs
            : startedAt
                ? Math.max(0, (nextStartedAt ?? now) - startedAt)
                : 0

        let status
        if (startedAt) {
            // completed는 마지막 스테이지라 nextStartedAt이 항상 null → active 오판 방지
            const isTerminal = stage === 'completed'
            status = (stage === currentStage && !nextStartedAt && !isTerminal) ? 'active' : 'done'
        } else if (currentStage === stage) {
            status = 'active'
        } else if (currentStageIndex >= 0 && index < currentStageIndex) {
            // stageMoments에 기록되지 않았어도 현재 스테이지보다 앞이면 done 처리
            status = 'done'
        } else {
            status = 'pending'
        }

        return {
            key: stage,
            label: STAGE_LABELS[stage],
            status,
            elapsedMs,
        }
    })
}

export function formatStageLabel(stage) {
    return STAGE_LABELS[stage] ?? stage ?? 'Idle'
}

export function getTimeseriesSeries(timeseries = {}) {
    return Object.entries(timeseries)
        .filter(([key, value]) => key !== 'timestamps_ms' && Array.isArray(value) && value.length)
        .map(([key, value]) => ({
            key,
            label: key.replaceAll('_', ' '),
            values: value,
        }))
}
