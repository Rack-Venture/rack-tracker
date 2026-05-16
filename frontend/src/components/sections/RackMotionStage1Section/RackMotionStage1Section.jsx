import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as THREE from 'three'
import { CSS2DObject, CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { getRackMotionFromSynthesis, DEFAULT_RACK_MOTION_PAGE_LIMIT } from '../../../api/analysisClient.js'
import SectionContainer from '../../SectionContainer/SectionContainer.jsx'
import style from './RackMotionStage1Section.module.css'

const PERSON_EDGES = [
    // Head — nose to eye chains
    ['person.nose', 'person.left_eye_inner'],
    ['person.left_eye_inner', 'person.left_eye'],
    ['person.left_eye', 'person.left_eye_outer'],
    ['person.left_eye_outer', 'person.left_ear'],
    ['person.nose', 'person.right_eye_inner'],
    ['person.right_eye_inner', 'person.right_eye'],
    ['person.right_eye', 'person.right_eye_outer'],
    ['person.right_eye_outer', 'person.right_ear'],
    // Mouth
    ['person.mouth_left', 'person.mouth_right'],
    // Torso
    ['person.left_shoulder', 'person.right_shoulder'],
    ['person.left_shoulder', 'person.left_hip'],
    ['person.right_shoulder', 'person.right_hip'],
    ['person.left_hip', 'person.right_hip'],
    // Arms
    ['person.left_shoulder', 'person.left_elbow'],
    ['person.right_shoulder', 'person.right_elbow'],
    ['person.left_elbow', 'person.left_wrist'],
    ['person.right_elbow', 'person.right_wrist'],
    // Hands (wrist-level tips)
    ['person.left_wrist', 'person.left_thumb'],
    ['person.left_wrist', 'person.left_index'],
    ['person.left_wrist', 'person.left_pinky'],
    ['person.left_index', 'person.left_pinky'],
    ['person.right_wrist', 'person.right_thumb'],
    ['person.right_wrist', 'person.right_index'],
    ['person.right_wrist', 'person.right_pinky'],
    ['person.right_index', 'person.right_pinky'],
    // Legs
    ['person.left_hip', 'person.left_knee'],
    ['person.right_hip', 'person.right_knee'],
    ['person.left_knee', 'person.left_ankle'],
    ['person.right_knee', 'person.right_ankle'],
    // Feet
    ['person.left_ankle', 'person.left_heel'],
    ['person.right_ankle', 'person.right_heel'],
    ['person.left_heel', 'person.left_foot_index'],
    ['person.right_heel', 'person.right_foot_index'],
]

const CAMERA_PRESETS = [
    { value: 'front', label: 'Front' },
    { value: 'side', label: 'Side' },
    { value: 'top', label: 'Top' },
]

const DEGRADED_RACK_M = { width: 1.22, depth: 1.3, height: 2.3 }

function disposeObject3D(object) {
    object.traverse((child) => {
        if (child.isCSS2DObject) {
            child.element?.remove()
        }
        child.geometry?.dispose?.()
        const material = child.material
        if (Array.isArray(material)) {
            material.forEach((item) => item.dispose?.())
        } else {
            material?.dispose?.()
        }
    })
}

function clearGroup(group) {
    while (group.children.length) {
        const child = group.children[0]
        group.remove(child)
        disposeObject3D(child)
    }
}

function makeDimLabel(text, cssClass) {
    const el = document.createElement('div')
    el.textContent = text
    el.className = cssClass
    return new CSS2DObject(el)
}

function formatCm(meters) {
    if (!Number.isFinite(meters)) return 'N/A'
    return `${Math.round(meters * 100)} cm`
}

function formatM(val) {
    if (!Number.isFinite(val)) return 'N/A'
    return val.toFixed(3)
}

function formatMetric(metric) {
    if (!metric) return 'N/A'
    const value = metric.value ?? 'N/A'
    return metric.unit ? `${value} ${metric.unit}` : String(value)
}

function statusLabel(status) {
    if (!status) return 'not_computed'
    return status
}

function SpaceBadge({ spaceId }) {
    return (
        <span
            className={style.spaceBadge}
            data-space={spaceId ?? 'not_computed'}
        >
            {spaceId ?? 'not_computed'}
        </span>
    )
}

function RackMotionScene({ fixture, frame, cameraPreset, showRack, showSkeleton }) {
    const mountRef = useRef(null)
    const sceneState = useRef(null)

    useEffect(() => {
        const container = mountRef.current
        if (!container) return undefined

        const width = container.clientWidth
        const height = container.clientHeight
        const scene = new THREE.Scene()
        scene.background = new THREE.Color(0x070a10)
        scene.fog = new THREE.FogExp2(0x070a10, 0.14)

        const camera = new THREE.PerspectiveCamera(46, width / height, 0.01, 100)
        camera.position.set(0, 0.55, 4.2)

        const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true })
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
        renderer.setSize(width, height)
        renderer.toneMapping = THREE.ACESFilmicToneMapping
        renderer.toneMappingExposure = 1.05
        container.appendChild(renderer.domElement)

        const css2DRenderer = new CSS2DRenderer()
        css2DRenderer.setSize(width, height)
        css2DRenderer.domElement.style.position = 'absolute'
        css2DRenderer.domElement.style.top = '0'
        css2DRenderer.domElement.style.left = '0'
        css2DRenderer.domElement.style.width = '100%'
        css2DRenderer.domElement.style.height = '100%'
        css2DRenderer.domElement.style.pointerEvents = 'none'
        container.appendChild(css2DRenderer.domElement)

        const controls = new OrbitControls(camera, renderer.domElement)
        controls.enableDamping = true
        controls.dampingFactor = 0.06
        controls.minDistance = 1.2
        controls.maxDistance = 8
        controls.target.set(0, 0, 0)
        controls.update()

        scene.add(new THREE.AmbientLight(0x21344f, 3.2))
        const hemi = new THREE.HemisphereLight(0x5bbbd4, 0x101216, 1.8)
        scene.add(hemi)
        const key = new THREE.DirectionalLight(0xffffff, 2.4)
        key.position.set(4, 5, 3)
        scene.add(key)
        const fill = new THREE.DirectionalLight(0x6ee7b7, 1.2)
        fill.position.set(-3, 2, -3)
        scene.add(fill)

        const rackGroup = new THREE.Group()
        const personGroup = new THREE.Group()
        scene.add(rackGroup)
        scene.add(personGroup)

        const ro = new ResizeObserver(() => {
            if (!mountRef.current) return
            const nextWidth = mountRef.current.clientWidth
            const nextHeight = mountRef.current.clientHeight
            renderer.setSize(nextWidth, nextHeight)
            css2DRenderer.setSize(nextWidth, nextHeight)
            camera.aspect = nextWidth / nextHeight
            camera.updateProjectionMatrix()
        })
        ro.observe(container)

        let frameId = null
        const animate = () => {
            controls.update()
            renderer.render(scene, camera)
            css2DRenderer.render(scene, camera)
            frameId = requestAnimationFrame(animate)
        }
        frameId = requestAnimationFrame(animate)

        sceneState.current = { camera, controls, renderer, css2DRenderer, rackGroup, personGroup }

        return () => {
            if (frameId) cancelAnimationFrame(frameId)
            ro.disconnect()
            clearGroup(rackGroup)
            clearGroup(personGroup)
            renderer.dispose()
            if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement)
            if (container.contains(css2DRenderer.domElement)) container.removeChild(css2DRenderer.domElement)
            sceneState.current = null
        }
    }, [])

    // Rack volume, anchors, dimension labels
    useEffect(() => {
        const state = sceneState.current
        if (!state) return
        const { rackGroup } = state
        clearGroup(rackGroup)
        rackGroup.visible = showRack

        const alignment = fixture?.rackAlignment
        const notComputed = !alignment || alignment.status === 'not_computed'
        const dimensions = notComputed ? DEGRADED_RACK_M : alignment.rackDimensionsM

        const fitScale = 2.8 / Math.max(dimensions.width, dimensions.depth, dimensions.height)
        const halfH = (dimensions.height / 2) * fitScale
        const halfW = (dimensions.width / 2) * fitScale
        const halfD = (dimensions.depth / 2) * fitScale

        const toRender = (x, y, z) => new THREE.Vector3(
            x * fitScale,
            (y - dimensions.height / 2) * fitScale,
            z * fitScale,
        )

        if (notComputed) {
            // Dashed degraded placeholder
            const geo = new THREE.BoxGeometry(
                dimensions.width * fitScale,
                dimensions.height * fitScale,
                dimensions.depth * fitScale,
            )
            const dashMat = new THREE.LineDashedMaterial({
                color: 0x8080a0,
                dashSize: 0.08,
                gapSize: 0.05,
                transparent: true,
                opacity: 0.35,
            })
            const dashEdges = new THREE.LineSegments(new THREE.EdgesGeometry(geo), dashMat)
            dashEdges.computeLineDistances()
            rackGroup.add(dashEdges)

            const notComputedLabel = makeDimLabel('RackWorldSpace\nnot computed', 'rm-dim-label-not-computed')
            notComputedLabel.position.set(0, 0, 0)
            rackGroup.add(notComputedLabel)
            return
        }

        // Rack volume fill
        const volumeGeometry = new THREE.BoxGeometry(
            dimensions.width * fitScale,
            dimensions.height * fitScale,
            dimensions.depth * fitScale,
        )
        const isDev = alignment.status === 'dev_assumption'
        rackGroup.add(new THREE.Mesh(
            volumeGeometry,
            new THREE.MeshBasicMaterial({
                color: isDev ? 0x2a3a22 : 0x1e4678,
                transparent: true,
                opacity: 0.07,
                side: THREE.BackSide,
                depthWrite: false,
            }),
        ))
        rackGroup.add(new THREE.LineSegments(
            new THREE.EdgesGeometry(volumeGeometry),
            new THREE.LineBasicMaterial({ color: isDev ? 0x6ab87a : 0x7a9ab8, transparent: true, opacity: 0.74 }),
        ))

        // Floor grid
        const gridSize = Math.max(dimensions.width, dimensions.depth) * fitScale
        const grid = new THREE.GridHelper(gridSize, 12, 0x2f7c92, 0x163a4b)
        grid.position.y = -halfH
        rackGroup.add(grid)

        // Floor plane
        const floorPlane = new THREE.Mesh(
            new THREE.PlaneGeometry(dimensions.width * fitScale, dimensions.depth * fitScale),
            new THREE.MeshBasicMaterial({ color: 0x0d5c55, transparent: true, opacity: 0.08, side: THREE.DoubleSide, depthWrite: false }),
        )
        floorPlane.rotation.x = -Math.PI / 2
        floorPlane.position.y = -halfH
        rackGroup.add(floorPlane)

        // Anchor markers
        const jcupGeo = new THREE.SphereGeometry(0.035 * fitScale, 16, 16)
        const safetyGeo = new THREE.CylinderGeometry(0.012 * fitScale, 0.012 * fitScale, dimensions.width * fitScale, 12)
        const anchorGeo = new THREE.SphereGeometry(0.02 * fitScale, 12, 12)
        const jcupMat = new THREE.MeshStandardMaterial({ color: 0xffaa44, emissive: 0x3a1b00, metalness: 0.45, roughness: 0.35 })
        const safetyMat = new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.46 })
        const anchorMat = new THREE.MeshStandardMaterial({ color: 0x6ee7b7, emissive: 0x083827, roughness: 0.4 })

        for (const anchor of frame?.rackAnchors ?? []) {
            const isJcup = anchor.anchorId.includes('jcup')
            const isSafetyLeft = anchor.anchorId.includes('safety') && anchor.anchorId.includes('left')
            if (isJcup) {
                const m = new THREE.Mesh(jcupGeo.clone(), jcupMat.clone())
                m.position.copy(toRender(anchor.x, anchor.y, anchor.z))
                rackGroup.add(m)
            } else if (isSafetyLeft) {
                const m = new THREE.Mesh(safetyGeo.clone(), safetyMat.clone())
                m.rotation.z = Math.PI / 2
                m.position.copy(toRender(0, anchor.y, anchor.z))
                rackGroup.add(m)
            } else if (!anchor.anchorId.includes('safety')) {
                const m = new THREE.Mesh(anchorGeo.clone(), anchorMat.clone())
                m.position.copy(toRender(anchor.x, anchor.y, anchor.z))
                rackGroup.add(m)
            }
        }

        // Dimension annotations
        const widthLabel = makeDimLabel(`${formatCm(dimensions.width)}`, 'rm-dim-label')
        widthLabel.position.set(0, halfH + 0.14, 0)
        rackGroup.add(widthLabel)

        const heightLabel = makeDimLabel(`${formatCm(dimensions.height)}`, 'rm-dim-label')
        heightLabel.position.set(halfW + 0.14, 0, 0)
        rackGroup.add(heightLabel)

        const depthLabel = makeDimLabel(`${formatCm(dimensions.depth)}`, 'rm-dim-label')
        depthLabel.position.set(halfW + 0.14, -halfH + halfH * 0.4, -halfD - 0.05)
        rackGroup.add(depthLabel)

        // J-cup height annotation
        if (alignment.jcupHeightsM?.length > 0) {
            const jcupAnnotation = makeDimLabel(`J-cup ${formatCm(alignment.jcupHeightsM[0])}`, 'rm-dim-label-small')
            jcupAnnotation.position.set(halfW + 0.14, (alignment.jcupHeightsM[0] - dimensions.height / 2) * fitScale, 0)
            rackGroup.add(jcupAnnotation)
        }
    }, [fixture, frame, showRack])

    // Person keypoints
    useEffect(() => {
        const state = sceneState.current
        const dimensions = fixture?.rackAlignment?.rackDimensionsM
        if (!state || !dimensions) return
        const { personGroup } = state
        clearGroup(personGroup)
        personGroup.visible = showSkeleton

        const fitScale = 2.8 / Math.max(dimensions.width, dimensions.depth, dimensions.height)
        const toRender = (point) => new THREE.Vector3(
            point.x * fitScale,
            (point.y - dimensions.height / 2) * fitScale,
            point.z * fitScale,
        )

        const validPoints = (frame?.personKeypoints ?? []).filter(
            (p) => p.status === 'valid' && Number.isFinite(p.x) && Number.isFinite(p.y) && Number.isFinite(p.z),
        )
        const points = new Map(validPoints.map((point) => [point.targetId, point]))

        const jointGeo = new THREE.SphereGeometry(0.022 * fitScale, 14, 14)
        for (const point of points.values()) {
            const material = new THREE.MeshStandardMaterial({
                color: point.quality >= 0.75 ? 0x00d4ff : 0xfbbf24,
                emissive: point.quality >= 0.75 ? 0x003344 : 0x332000,
                metalness: 0.25,
                roughness: 0.35,
            })
            const mesh = new THREE.Mesh(jointGeo.clone(), material)
            mesh.position.copy(toRender(point))
            personGroup.add(mesh)
        }

        const positions = []
        for (const [fromId, toId] of PERSON_EDGES) {
            const from = points.get(fromId)
            const to = points.get(toId)
            if (!from || !to) continue
            const a = toRender(from)
            const b = toRender(to)
            positions.push(a.x, a.y, a.z, b.x, b.y, b.z)
        }
        if (positions.length) {
            const geometry = new THREE.BufferGeometry()
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
            personGroup.add(new THREE.LineSegments(
                geometry,
                new THREE.LineBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.82 }),
            ))
        }
    }, [fixture, frame, showSkeleton])

    // Toggle visibility without rebuilding
    useEffect(() => {
        const state = sceneState.current
        if (!state) return
        state.rackGroup.visible = showRack
    }, [showRack])

    useEffect(() => {
        const state = sceneState.current
        if (!state) return
        state.personGroup.visible = showSkeleton
    }, [showSkeleton])

    // Camera preset
    useEffect(() => {
        const state = sceneState.current
        if (!state) return
        const { camera, controls } = state
        controls.target.set(0, 0, 0)
        if (cameraPreset === 'side') {
            camera.position.set(4.0, 0.45, 0.0)
        } else if (cameraPreset === 'top') {
            camera.position.set(0.0, 4.2, 0.01)
        } else {
            camera.position.set(0.0, 0.55, 4.2)
        }
        controls.update()
    }, [cameraPreset])

    return <div ref={mountRef} className={style.sceneCanvas} />
}

export default function RackMotionStage1Section({ synthesisJobId }) {
    const [fixture, setFixture] = useState(null)
    const [allFrames, setAllFrames] = useState([])
    const [error, setError] = useState(null)
    const [frameIndex, setFrameIndex] = useState(0)
    const [isPlaying, setIsPlaying] = useState(false)
    const [cameraPreset, setCameraPreset] = useState('front')
    const animRef = useRef(null)
    const lastTsRef = useRef(null)
    const [showProvenance, setShowProvenance] = useState(false)
    const [showRack, setShowRack] = useState(true)
    const [showSkeleton, setShowSkeleton] = useState(true)

    useEffect(() => {
        if (!synthesisJobId) {
            setFixture(null)
            setAllFrames([])
            setError(null)
            return
        }
        const abortController = new AbortController()
        const signal = abortController.signal

        const fetchAll = async () => {
            try {
                const firstPage = await getRackMotionFromSynthesis(
                    synthesisJobId, 0, DEFAULT_RACK_MOTION_PAGE_LIMIT, { signal },
                )
                setFixture(firstPage)
                const accumulated = [...(firstPage.framePage?.frames ?? [])]
                setAllFrames([...accumulated])
                setFrameIndex(0)
                setIsPlaying(false)
                setError(null)

                let nextStart = firstPage.framePage?.page?.nextStartFrame ?? null
                while (nextStart !== null) {
                    const nextPage = await getRackMotionFromSynthesis(
                        synthesisJobId, nextStart, DEFAULT_RACK_MOTION_PAGE_LIMIT, { signal },
                    )
                    const pageFrames = nextPage.framePage?.frames ?? []
                    accumulated.push(...pageFrames)
                    setAllFrames([...accumulated])
                    nextStart = nextPage.framePage?.page?.nextStartFrame ?? null
                }
            } catch (err) {
                if (err?.name === 'AbortError') return
                setError(err)
            }
        }

        fetchAll()
        return () => abortController.abort()
    }, [synthesisJobId])

    const frames = allFrames
    const boundedFrameIndex = Math.round(Math.min(Math.max(frameIndex, 0), Math.max(frames.length - 1, 0)))
    const currentFrame = frames[boundedFrameIndex] ?? null

    const inferredFps = useMemo(() => {
        if (frames.length < 2) return 30
        const delta = (frames[1]?.timestampMs ?? 0) - (frames[0]?.timestampMs ?? 0)
        return delta > 0 ? 1000 / delta : 30
    }, [frames])

    const stopPlayback = useCallback(() => {
        setIsPlaying(false)
        if (animRef.current) cancelAnimationFrame(animRef.current)
        lastTsRef.current = null
    }, [])

    useEffect(() => {
        if (!isPlaying) {
            lastTsRef.current = null
            return
        }
        const tick = (ts) => {
            if (lastTsRef.current !== null) {
                const delta = ts - lastTsRef.current
                setFrameIndex(prev => {
                    const next = prev + (delta / 1000) * inferredFps
                    if (next >= frames.length - 1) {
                        stopPlayback()
                        return frames.length - 1
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
    }, [isPlaying, inferredFps, frames.length, stopPlayback])
    const alignment = fixture?.rackAlignment ?? null
    const dimensions = alignment?.rackDimensionsM ?? null
    const qualityMetric = alignment?.qualityMetrics?.[0] ?? null
    const alignmentStatus = alignment?.status ?? 'not_computed'
    const captureToRack = alignment?.captureToRackStatus ?? 'not_computed'

    const personQuality = useMemo(() => {
        const keypoints = (currentFrame?.personKeypoints ?? []).filter((p) => p.status === 'valid')
        if (!keypoints.length) return null
        return keypoints.reduce((sum, point) => sum + point.quality, 0) / keypoints.length
    }, [currentFrame])

    const syncStatus = fixture?.session?.syncQuality?.status ?? null

    return (
        <SectionContainer
            id="rackMotionStage1"
            heading="RACK MOTION VIEWER"
            description="Stage 1 rack-world fixture with explicit alignment provenance and person keypoints."
        >
            <div className={style.viewerShell}>
                <div className={style.statusBar}>
                    <div className={style.statusTitle}>Rack Motion Viewer</div>
                    <span className={style.badge} data-kind="space">rack_world</span>
                    <span className={style.badge} data-kind={alignmentStatus}>
                        {statusLabel(alignmentStatus)}
                    </span>
                    {syncStatus && (
                        <span className={style.badge} data-kind={syncStatus === 'ok' ? 'sync-ok' : 'sync-warn'}>
                            sync: {syncStatus}
                        </span>
                    )}
                    <span className={style.badge} data-kind="quality">
                        Q: {personQuality == null ? 'N/A' : `${Math.round(personQuality * 100)}%`}
                    </span>
                    {synthesisJobId && (
                        <span className={style.badge} data-kind="source">from synthesis</span>
                    )}
                </div>

                {alignmentStatus === 'dev_assumption' && (
                    <div className={style.warningBanner}>
                        Dev-only alignment active — rack dimensions from synthetic fixture. Not production grade.
                    </div>
                )}
                {alignmentStatus === 'not_computed' && (
                    <div className={style.errorBanner}>
                        RackWorldSpace not available — rack alignment not computed.
                    </div>
                )}

                <div className={style.contentGrid}>
                    <div className={style.scenePane}>
                        <RackMotionScene
                            fixture={fixture}
                            frame={currentFrame}
                            cameraPreset={cameraPreset}
                            showRack={showRack}
                            showSkeleton={showSkeleton}
                        />
                        {!synthesisJobId && (
                            <div className={style.sceneOverlay}>
                                Skeleton 3D 합성을 먼저 실행하세요
                            </div>
                        )}
                        {synthesisJobId && !fixture && !error && (
                            <div className={style.sceneOverlay}>Loading rack motion fixture</div>
                        )}
                        {error && (
                            <div className={style.sceneOverlay} data-state="error">
                                Rack motion fixture unavailable
                            </div>
                        )}
                        <div className={style.sceneControls}>
                            {CAMERA_PRESETS.map((preset) => (
                                <button
                                    key={preset.value}
                                    type="button"
                                    className={`${style.controlButton} ${cameraPreset === preset.value ? style.controlButtonActive : ''}`}
                                    onClick={() => setCameraPreset(preset.value)}
                                >
                                    {preset.label}
                                </button>
                            ))}
                        </div>
                    </div>

                    <aside className={style.inspectorPane}>
                        <div className={style.inspectorSection}>
                            <div className={style.inspectorTitle}>Session</div>
                            <dl className={style.factList}>
                                <div>
                                    <dt>session</dt>
                                    <dd title={fixture?.session?.sessionId ?? ''}>{fixture?.session?.sessionId ?? 'N/A'}</dd>
                                </div>
                                <div>
                                    <dt>alignment</dt>
                                    <dd>{alignment?.rackAlignmentId ?? 'N/A'}</dd>
                                </div>
                                <div>
                                    <dt>capture_to_rack</dt>
                                    <dd>
                                        <span className={style.spaceBadge} data-space={captureToRack}>
                                            {captureToRack}
                                        </span>
                                    </dd>
                                </div>

                            </dl>
                        </div>

                        <div className={style.inspectorSection}>
                            <div className={style.inspectorTitle}>Rack Volume</div>
                            <dl className={style.factList}>
                                <div>
                                    <dt>width</dt>
                                    <dd>
                                        {formatCm(dimensions?.width)}
                                        {dimensions && <SpaceBadge spaceId="rack_world" />}
                                    </dd>
                                </div>
                                <div>
                                    <dt>depth</dt>
                                    <dd>
                                        {formatCm(dimensions?.depth)}
                                        {dimensions && <SpaceBadge spaceId="rack_world" />}
                                    </dd>
                                </div>
                                <div>
                                    <dt>height</dt>
                                    <dd>
                                        {formatCm(dimensions?.height)}
                                        {dimensions && <SpaceBadge spaceId="rack_world" />}
                                    </dd>
                                </div>
                                <div>
                                    <dt>J-cup</dt>
                                    <dd>
                                        {formatCm(alignment?.jcupHeightsM?.[0])}
                                        {alignment?.jcupHeightsM?.length > 0 && <SpaceBadge spaceId="rack_world" />}
                                    </dd>
                                </div>
                                <div>
                                    <dt>safety</dt>
                                    <dd>
                                        {formatCm(alignment?.safetyPinHeightsM?.[0])}
                                        {alignment?.safetyPinHeightsM?.length > 0 && <SpaceBadge spaceId="rack_world" />}
                                    </dd>
                                </div>
                            </dl>
                        </div>

                        <div className={style.inspectorSection}>
                            <div className={style.inspectorTitle}>View</div>
                            <div className={style.toggleList}>
                                <label className={style.toggleRow}>
                                    <input
                                        type="checkbox"
                                        checked={showRack}
                                        onChange={(e) => setShowRack(e.target.checked)}
                                    />
                                    <span>Rack Mesh</span>
                                </label>
                                <label className={style.toggleRow}>
                                    <input
                                        type="checkbox"
                                        checked={showSkeleton}
                                        onChange={(e) => setShowSkeleton(e.target.checked)}
                                    />
                                    <span>Skeleton</span>
                                </label>
                            </div>
                        </div>

                        <div className={style.inspectorSection}>
                            <div className={style.frameHeader}>
                                <div className={style.inspectorTitle}>Frame</div>
                                <button
                                    className={`${style.playBtn} ${isPlaying ? style.playBtnActive : ''}`}
                                    onClick={() => setIsPlaying(p => !p)}
                                    disabled={frames.length < 2}
                                >
                                    {isPlaying ? '■' : '▶'}
                                </button>
                            </div>
                            <input
                                type="range"
                                className={style.frameSlider}
                                min={0}
                                max={Math.max(frames.length - 1, 0)}
                                value={boundedFrameIndex}
                                onChange={(event) => {
                                    stopPlayback()
                                    setFrameIndex(Number(event.target.value))
                                }}
                                disabled={!frames.length}
                                style={{
                                    '--progress': frames.length > 1
                                        ? `${(boundedFrameIndex / (frames.length - 1)) * 100}%`
                                        : '0%',
                                }}
                            />
                            <dl className={style.factList}>
                                <div>
                                    <dt>index</dt>
                                    <dd>{currentFrame?.frameIndex ?? 'N/A'}</dd>
                                </div>
                                <div>
                                    <dt>time</dt>
                                    <dd>{currentFrame ? `${Math.round(currentFrame.timestampMs)} ms` : 'N/A'}</dd>
                                </div>
                                <div>
                                    <dt>keypoints</dt>
                                    <dd>
                                        {(currentFrame?.personKeypoints ?? []).filter((p) => p.status === 'valid').length}
                                        &nbsp;/&nbsp;
                                        {currentFrame?.personKeypoints?.length ?? 0}
                                    </dd>
                                </div>
                                <div>
                                    <dt>sync delta</dt>
                                    <dd>{formatMetric(currentFrame?.qualityMetrics?.[0])}</dd>
                                </div>
                            </dl>
                        </div>

                        {currentFrame?.personKeypoints?.length > 0 && (
                            <div className={style.inspectorSection}>
                                <div className={style.inspectorTitle}>Keypoints</div>
                                <div className={style.keypointList}>
                                    {currentFrame.personKeypoints.map((point) => (
                                        <div
                                            key={point.targetId}
                                            className={style.keypointRow}
                                            data-status={point.status}
                                        >
                                            <div className={style.keypointName}>
                                                {point.targetId.replace('person.', '')}
                                            </div>
                                            {point.status === 'valid' ? (
                                                <div className={style.keypointCoords}>
                                                    <span>x {formatM(point.x)}</span>
                                                    <span>y {formatM(point.y)}</span>
                                                    <span>z {formatM(point.z)}</span>
                                                    <SpaceBadge spaceId={point.spaceId} />
                                                </div>
                                            ) : (
                                                <div className={style.keypointMissing}>
                                                    {point.failureReason ?? 'failed'}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        <button
                            type="button"
                            className={style.provenanceButton}
                            onClick={() => setShowProvenance((next) => !next)}
                        >
                            {showProvenance ? '▲' : '▼'} Provenance
                        </button>

                        {showProvenance && (
                            <pre className={style.provenanceBlock}>
                                {JSON.stringify({
                                    sessionId: fixture?.session?.sessionId,
                                    schemaVersion: fixture?.session?.schemaVersion,
                                    sourceRefs: fixture?.session?.sourceRefs,
                                    coordinateSpaces: fixture?.session?.coordinateSpaces,
                                    syncQuality: fixture?.session?.syncQuality?.status,
                                    rackAlignment: {
                                        status: alignment?.status,
                                        captureToRackStatus: captureToRack,
                                    },
                                }, null, 2)}
                            </pre>
                        )}

                        {qualityMetric && (
                            <div className={style.qualityStrip}>
                                <span>{qualityMetric.metricName}</span>
                                <strong>{formatMetric(qualityMetric)}</strong>
                            </div>
                        )}
                    </aside>
                </div>
            </div>
        </SectionContainer>
    )
}
