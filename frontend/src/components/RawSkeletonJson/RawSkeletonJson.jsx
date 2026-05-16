import { useEffect, useRef, useState } from 'react'
import style from './RawSkeletonJson.module.css'

const FRAME_PREVIEW_LIMIT = 10

function buildPreviewPayload(skeletonJson) {
    if (!skeletonJson) return skeletonJson
    const frames = Array.isArray(skeletonJson.frames) ? skeletonJson.frames : null
    if (!frames || frames.length <= FRAME_PREVIEW_LIMIT) return skeletonJson

    return {
        ...skeletonJson,
        frames: frames.slice(0, FRAME_PREVIEW_LIMIT),
        _preview: `Showing first ${FRAME_PREVIEW_LIMIT} of ${frames.length} frames.`,
    }
}

export default function RawSkeletonJson({ skeletonJson }) {
    const [serialized, setSerialized] = useState(null)
    const timeoutRef = useRef(null)

    useEffect(() => {
        setSerialized(null)

        timeoutRef.current = setTimeout(() => {
            setSerialized(JSON.stringify(buildPreviewPayload(skeletonJson), null, 2))
        }, 0)

        return () => clearTimeout(timeoutRef.current)
    }, [skeletonJson])

    return (
        <article className={style.RawSkeletonJsonConatiner}>
            <pre className={style.RawSkeletonJson}>
                {serialized ?? 'Serializing...'}
            </pre>
        </article>
    )
}
