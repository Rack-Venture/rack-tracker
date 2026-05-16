const DEFAULT_BASE_URL = 'http://127.0.0.1:8080'

export function getBaseUrl() {
    return (import.meta.env.VITE_API_BASE_URL ?? DEFAULT_BASE_URL).replace(/\/$/, '')
}

export const DEFAULT_SKELETON_PAGE_LIMIT = 300
export const DEFAULT_SKELETON3D_PAGE_LIMIT = 300
export const DEFAULT_RACK_MOTION_PAGE_LIMIT = 120

async function buildError(response) {
    const contentType = response.headers.get('content-type') ?? ''
    const payload = contentType.includes('application/json')
        ? await response.json()
        : await response.text()

    const message = typeof payload === 'string'
        ? payload
        : payload?.detail ?? payload?.error?.message ?? `Request failed with ${response.status}`
    const error = new Error(message)
    error.status = response.status
    error.payload = payload
    return error
}

async function parseResponse(response) {
    if (!response.ok) {
        throw await buildError(response)
    }

    const contentType = response.headers.get('content-type') ?? ''
    const payload = contentType.includes('application/json')
        ? await response.json()
        : await response.text()

    return payload
}

async function request(path, init = {}) {
    const response = await fetch(`${getBaseUrl()}${path}`, init)
    return parseResponse(response)
}

function getAttachmentFilename(contentDisposition, fallbackName) {
    if (!contentDisposition) return fallbackName

    const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
    if (utf8Match?.[1]) {
        return decodeURIComponent(utf8Match[1])
    }

    const asciiMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
    return asciiMatch?.[1] ?? fallbackName
}

export function openJobStream(jobId) {
    return new EventSource(`${getBaseUrl()}/jobs/${jobId}/stream`)
}

export async function createJob(form, file, { signal } = {}) {
    const body = new FormData()

    if (file) {
        body.append('video', file)
    }

    if (form.samplingFps != null) {
        body.append('samplingFps', String(form.samplingFps))
    }

    // exerciseType is not sent → backend defaults to general_motion experiment mode
    // Squat-specific fields (bodyweightKg, externalLoadKg, barPlacementMode) omitted
    // body.append('exerciseType', 'squat')  // squat pipeline reference
    // if (form.bodyweightKg != null) body.append('bodyweightKg', String(form.bodyweightKg))
    // if (form.externalLoadKg != null) body.append('externalLoadKg', String(form.externalLoadKg))
    // if (form.barPlacementMode) body.append('barPlacementMode', form.barPlacementMode)

    if (form.presetEstimationId) {
        body.append('presetEstimationId', form.presetEstimationId)
    }

    if (!form.presetEstimationId) {
        if (form.modelVariant) {
            body.append('modelVariant', form.modelVariant)
        }
        if (form.delegate === 'CPU') {
            body.append('delegate', 'CPU')
        }
    }

    return request('/jobs', {
        method: 'POST',
        body,
        signal,
    })
}

export function getJobStatus(jobId, { signal } = {}) {
    return request(`/jobs/${jobId}`, { signal })
}

export function getJobResult(jobId, { signal } = {}) {
    return request(`/jobs/${jobId}/result`, { signal })
}

export function getSkeletonPage(jobId, offset = 0, limit = DEFAULT_SKELETON_PAGE_LIMIT, { signal } = {}) {
    return request(`/jobs/${jobId}/skeleton?offset=${offset}&limit=${limit}`, { signal })
}

export function createSynthesisJob({
    sourceJobIdA,
    sourceJobIdB,
    cameraIdA = '00_21',
    cameraIdB = '00_11',
    calibrationRef = '171204_pose1/171204_pose1/calibration_171204_pose1.json',
    runEvaluation = false,
} = {}, { signal } = {}) {
    return request('/synthesis/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            pairManifest: {
                schemaVersion: 'synthesis_pair_manifest.v1',
                sources: {
                    A: { sourceJobId: sourceJobIdA, cameraId: cameraIdA },
                    B: { sourceJobId: sourceJobIdB, cameraId: cameraIdB },
                },
                calibrationRef,
                sync: {
                    mode: 'timestamp',
                    timestampDomain: 'media_time_ms',
                    maxDeltaMs: 16.7,
                    fallback: 'frameIndex_for_gt_aligned_dataset_only',
                },
                landmarkSet: 'mediapipe_pose_33',
                outputCoordinateSystem: 'panoptic_world_cm',
            },
            options: { runEvaluation },
        }),
        signal,
    })
}

export async function uploadSynthesisVideo(file, { signal } = {}) {
    const body = new FormData()
    body.append('video', file)
    return request('/synthesis/upload', { method: 'POST', body, signal })
}

export function createStreamingSynthesisJob({
    sourceA,
    sourceB,
    videoPathA,
    videoPathB,
    cameraIdA = '00_21',
    cameraIdB = '00_11',
    calibrationRef = '171204_pose1/171204_pose1/calibration_171204_pose1.json',
    runEvaluation = false,
} = {}, { signal } = {}) {
    const resolvedA = sourceA ?? { videoPath: videoPathA, cameraId: cameraIdA }
    const resolvedB = sourceB ?? { videoPath: videoPathB, cameraId: cameraIdB }
    return request('/synthesis/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            streamingManifest: {
                schemaVersion: 'streaming_pair_manifest.v1',
                sources: { A: resolvedA, B: resolvedB },
                calibrationRef,
                sync: {
                    mode: 'timestamp',
                    timestampDomain: 'media_time_ms',
                    maxDeltaMs: 16.7,
                    fallback: 'frameIndex_for_gt_aligned_dataset_only',
                },
                landmarkSet: 'mediapipe_pose_33',
                outputCoordinateSystem: 'panoptic_world_cm',
            },
            options: { runEvaluation },
        }),
        signal,
    })
}

export function getSkeletonAPage(
    jobId,
    offset = 0,
    limit = DEFAULT_SKELETON3D_PAGE_LIMIT,
    { signal } = {},
) {
    return request(`/synthesis/jobs/${jobId}/skeleton_a?offset=${offset}&limit=${limit}`, { signal })
}

export function getSkeletonBPage(
    jobId,
    offset = 0,
    limit = DEFAULT_SKELETON3D_PAGE_LIMIT,
    { signal } = {},
) {
    return request(`/synthesis/jobs/${jobId}/skeleton_b?offset=${offset}&limit=${limit}`, { signal })
}

export function getSynthesisJobStatus(jobId, { signal } = {}) {
    return request(`/synthesis/jobs/${jobId}`, { signal })
}

export function getSynthesisResult(jobId, { signal } = {}) {
    return request(`/synthesis/jobs/${jobId}/result`, { signal })
}

export function getSynthesisSkeleton3D(jobId, { signal } = {}) {
    return request(`/synthesis/jobs/${jobId}/skeleton3d/all`, { signal })
}

export function getSynthesisSkeleton3DPage(
    jobId,
    offset = 0,
    limit = DEFAULT_SKELETON3D_PAGE_LIMIT,
    { signal } = {},
) {
    return request(`/synthesis/jobs/${jobId}/skeleton3d?offset=${offset}&limit=${limit}`, { signal })
}

export function getSynthesisDebugReport(jobId, { signal } = {}) {
    return request(`/synthesis/jobs/${jobId}/debug`, { signal })
}

export function getRackMotionStage1Fixture(
    offset = 0,
    limit = DEFAULT_RACK_MOTION_PAGE_LIMIT,
    { signal } = {},
) {
    return request(`/rack-motion/fixtures/stage1?offset=${offset}&limit=${limit}`, { signal })
}

export function getRackMotionFromSynthesis(
    synthesisJobId,
    offset = 0,
    limit = DEFAULT_RACK_MOTION_PAGE_LIMIT,
    { signal } = {},
) {
    return request(
        `/rack-motion/from-synthesis/${encodeURIComponent(synthesisJobId)}/stage1?offset=${offset}&limit=${limit}`,
        { signal },
    )
}

export function getBenchmark(jobId, { signal } = {}) {
    return request(`/jobs/${jobId}/benchmark`, { signal })
}

export async function downloadSkeletonFile(jobId, { signal } = {}) {
    const response = await fetch(`${getBaseUrl()}/jobs/${jobId}/skeleton/download`, { signal })

    if (!response.ok) {
        throw await buildError(response)
    }

    const blob = await response.blob()
    return {
        blob,
        fileName: getAttachmentFilename(
            response.headers.get('content-disposition'),
            `job-${jobId}-skeleton.json`
        ),
    }
}
