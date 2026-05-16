import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { POSE_EDGES } from '../../SkeletonViewer/utils/poseEdges.js'
import style from './ThreeJSSkeleton.module.css'

const VIS_THRESHOLD = 0.3
const FOOT_LANDMARK_INDICES = [27, 28, 29, 30, 31, 32]
const METRIC_VIEW_SPAN = 2.2
const DEFAULT_FLOOR_Y = -1.25

const CAMERA_VIEW_DISTANCE = 3.6

function applyCameraPreset(camera, controls, view, metricViewFrame, frontView) {
    controls.target.set(0, 0, 0)

    if ((view === 'front' || view === 'side') && metricViewFrame && frontView?.cameraMidpointXZ) {
        const [midX, midZ] = frontView.cameraMidpointXZ
        const dxWorld = midX - metricViewFrame.centerX
        const dzWorld = midZ - metricViewFrame.centerZ
        const mag = Math.sqrt(dxWorld * dxWorld + dzWorld * dzWorld)
        const ndx = mag > 1e-6 ? dxWorld / mag : 0
        const ndz = mag > 1e-6 ? dzWorld / mag : 1
        const yRender = frontView.eyeHeightWorld != null
            ? (metricViewFrame.groundY - frontView.eyeHeightWorld) * metricViewFrame.scale + metricViewFrame.floorY
            : 0.4
        const D = CAMERA_VIEW_DISTANCE
        if (view === 'front') {
            camera.position.set(ndx * D, yRender, ndz * D)
        } else {
            // side: rotate front direction 90° around Y — (ndx, ndz) → (ndz, -ndx)
            camera.position.set(ndz * D, yRender, -ndx * D)
        }
    } else if (view === 'front') {
        camera.position.set(0, 0.4, CAMERA_VIEW_DISTANCE)
    } else if (view === 'side') {
        camera.position.set(CAMERA_VIEW_DISTANCE, 0.4, 0)
    } else if (view === 'top') {
        camera.position.set(0, 4.5, 0.01)
    }

    controls.update()
}

function isMetricFrame(frame) {
    return frame?.sourceType === 'skeleton3d'
        || frame?.coordinateSystem === 'panoptic_world_cm'
        || frame?.landmarks?.some(lm => lm?.metric3d)
}

function isFiniteMetricLandmark(lm) {
    return lm
        && lm.success !== false
        && lm.renderable !== false
        && Number.isFinite(lm.x)
        && Number.isFinite(lm.y)
        && Number.isFinite(lm.z)
}

function computeMetricViewFrame(landmarks, viewHint) {
    const renderable = landmarks.filter(isFiniteMetricLandmark)
    const valid = renderable.filter(lm => lm.success !== false)
    const boundsLandmarks = valid.length ? valid : renderable
    if (!renderable.length) return null

    const xs = boundsLandmarks.map(lm => lm.x)
    const ys = boundsLandmarks.map(lm => lm.y)
    const zs = boundsLandmarks.map(lm => lm.z)
    const min = { x: Math.min(...xs), y: Math.min(...ys), z: Math.min(...zs) }
    const max = { x: Math.max(...xs), y: Math.max(...ys), z: Math.max(...zs) }

    // Ground plane and up axis are fixed by the coordinate system, not estimated from joints.
    // panoptic_world_cm: upAxis=y, upAxisDirection=negative (more negative Y = higher),
    // groundPlaneValue=0 (feet rest at Y≈0 in world space).
    // Joint visibility affects only centering (X, Z) and scale — never ground position.
    const groundPlaneValue = viewHint?.groundPlaneValue ?? 0.0
    const bodyHeight = Math.max(groundPlaneValue - min.y, 1)
    const horizontalSpan = Math.max(max.x - min.x, max.z - min.z, 1)
    const scale = METRIC_VIEW_SPAN / Math.max(bodyHeight, horizontalSpan)
    const renderHeight = bodyHeight * scale

    return {
        centerX: (min.x + max.x) / 2,
        centerZ: (min.z + max.z) / 2,
        groundY: groundPlaneValue,
        scale,
        floorY: -renderHeight / 2,
    }
}

function toLandmarkVec3(lm, metricViewFrame = null) {
    if (metricViewFrame) {
        return [
            (lm.x - metricViewFrame.centerX) * metricViewFrame.scale,
            (metricViewFrame.groundY - lm.y) * metricViewFrame.scale + metricViewFrame.floorY,
            (lm.z - metricViewFrame.centerZ) * metricViewFrame.scale,
        ]
    }
    return [
        (lm.x - 0.5) * 2,
        -(lm.y - 0.5) * 2,
        -(lm.z ?? 0) * 3,
    ]
}

function qualityColor(lm, threshold = 8) {
    if (lm?.success === false) return 0x7c8596
    const error = lm?.reprojectionErrorPx
    if (typeof error === 'number') {
        if (error > threshold) return 0xff6b6b
        if (error > threshold / 2) return 0xfbbf24
    }
    return 0x00d4ff
}

function isRenderableLandmark(lm) {
    if (!lm) return false
    if (lm.metric3d) {
        return lm.success !== false
            && lm.renderable !== false
            && Number.isFinite(lm.x)
            && Number.isFinite(lm.y)
            && Number.isFinite(lm.z)
    }
    return (lm.visibility ?? 1) >= VIS_THRESHOLD
}

function isReliableBoneEndpoint(lm) {
    if (!isRenderableLandmark(lm)) return false
    return !lm.metric3d || lm.success !== false
}

export default function ThreeJSSkeleton({ synthFrame, cameraView }) {
    const mountRef = useRef(null)
    const sceneState = useRef(null)
    const metricViewFrameRef = useRef(null)
    const frontViewHintRef = useRef(null)

    useEffect(() => {
        const container = mountRef.current
        if (!container) return

        const w = container.clientWidth
        const h = container.clientHeight

        const scene = new THREE.Scene()
        scene.background = new THREE.Color(0x070a10)
        scene.fog = new THREE.FogExp2(0x070a10, 0.18)

        const camera = new THREE.PerspectiveCamera(48, w / h, 0.01, 200)
        camera.position.set(0, 0.4, CAMERA_VIEW_DISTANCE)

        const renderer = new THREE.WebGLRenderer({ antialias: true })
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
        renderer.setSize(w, h)
        renderer.toneMapping = THREE.ACESFilmicToneMapping
        renderer.toneMappingExposure = 1.1
        container.appendChild(renderer.domElement)

        const controls = new OrbitControls(camera, renderer.domElement)
        controls.enableDamping = true
        controls.dampingFactor = 0.06
        controls.minDistance = 0.8
        controls.maxDistance = 12
        controls.target.set(0, 0, 0)
        controls.update()

        // Lighting
        scene.add(new THREE.AmbientLight(0x1a2a44, 4))
        const hemi = new THREE.HemisphereLight(0x1a4a8a, 0x080a0e, 2)
        scene.add(hemi)
        const dirLight = new THREE.DirectionalLight(0x00d4ff, 3)
        dirLight.position.set(3, 6, 4)
        scene.add(dirLight)
        const fillLight = new THREE.DirectionalLight(0x004466, 1.5)
        fillLight.position.set(-3, 2, -2)
        scene.add(fillLight)

        // Grid floor
        const grid = new THREE.GridHelper(8, 40, 0x0c1f38, 0x091726)
        grid.position.y = DEFAULT_FLOOR_Y
        scene.add(grid)

        // Ground glow
        const glowGeo = new THREE.PlaneGeometry(6, 6)
        const glowMat = new THREE.MeshBasicMaterial({
            color: 0x001a44,
            transparent: true,
            opacity: 0.18,
            side: THREE.DoubleSide,
            depthWrite: false,
        })
        const glowPlane = new THREE.Mesh(glowGeo, glowMat)
        glowPlane.rotation.x = -Math.PI / 2
        glowPlane.position.y = DEFAULT_FLOOR_Y
        scene.add(glowPlane)

        // Axis indicator (small, bottom-left of scene)
        const axisHelper = new THREE.AxesHelper(0.3)
        axisHelper.position.set(-1.8, -1.1, 0)
        scene.add(axisHelper)

        // Joint spheres
        const jointGeo = new THREE.SphereGeometry(0.024, 10, 10)
        const joints = Array.from({ length: 33 }, () => {
            const mat = new THREE.MeshStandardMaterial({
                color: 0x00d4ff,
                emissive: 0x003055,
                roughness: 0.3,
                metalness: 0.6,
                transparent: true,
                opacity: 1,
            })
            const mesh = new THREE.Mesh(jointGeo, mat)
            mesh.visible = false
            scene.add(mesh)
            return mesh
        })

        // Bone lines (LineSegments for all edges)
        const boneCount = POSE_EDGES.length
        const bonePositions = new Float32Array(boneCount * 6) // 2 verts * 3 floats
        const boneGeo = new THREE.BufferGeometry()
        boneGeo.setAttribute('position', new THREE.BufferAttribute(bonePositions, 3))
        const boneMat = new THREE.LineBasicMaterial({
            color: 0x0099cc,
            transparent: true,
            opacity: 0.75,
        })
        const boneLines = new THREE.LineSegments(boneGeo, boneMat)
        scene.add(boneLines)

        // Ghost bone lines (additive glow layer)
        const ghostGeo = new THREE.BufferGeometry()
        ghostGeo.setAttribute('position', new THREE.BufferAttribute(bonePositions.slice(), 3))
        const ghostMat = new THREE.LineBasicMaterial({
            color: 0x00eeff,
            transparent: true,
            opacity: 0.18,
            blending: THREE.AdditiveBlending,
            depthWrite: false,
        })
        const ghostLines = new THREE.LineSegments(ghostGeo, ghostMat)
        scene.add(ghostLines)

        // ResizeObserver
        const ro = new ResizeObserver(() => {
            if (!mountRef.current) return
            const nw = mountRef.current.clientWidth
            const nh = mountRef.current.clientHeight
            renderer.setSize(nw, nh)
            camera.aspect = nw / nh
            camera.updateProjectionMatrix()
        })
        ro.observe(container)

        // Render only while the 3D viewer is close to the viewport. The section
        // sits below completed 2D results, so an always-on RAF competes with
        // post-completion hydration while the user is still above this canvas.
        let animFrame = null
        let isVisible = typeof IntersectionObserver !== 'function'

        const renderScene = () => {
            controls.update()
            renderer.render(scene, camera)
        }

        const stopRenderLoop = () => {
            if (animFrame) {
                cancelAnimationFrame(animFrame)
                animFrame = null
            }
        }

        const animate = () => {
            if (!isVisible) {
                animFrame = null
                return
            }
            renderScene()
            animFrame = requestAnimationFrame(animate)
        }

        const startRenderLoop = () => {
            if (animFrame) return
            animFrame = requestAnimationFrame(animate)
        }

        let io = null
        if (typeof IntersectionObserver === 'function') {
            io = new IntersectionObserver(([entry]) => {
                isVisible = Boolean(entry?.isIntersecting)
                if (isVisible) {
                    renderScene()
                    startRenderLoop()
                } else {
                    stopRenderLoop()
                }
            }, { rootMargin: '200px 0px', threshold: 0.01 })
            io.observe(container)
        } else {
            startRenderLoop()
        }

        sceneState.current = {
            scene,
            camera,
            renderer,
            controls,
            joints,
            grid,
            glowPlane,
            axisHelper,
            boneLines,
            ghostLines,
            boneGeo,
            ghostGeo,
            requestRender: () => {
                if (isVisible) renderScene()
            },
        }

        return () => {
            stopRenderLoop()
            io?.disconnect()
            ro.disconnect()
            renderer.dispose()
            jointGeo.dispose()
            boneGeo.dispose()
            ghostGeo.dispose()
            boneMat.dispose()
            ghostMat.dispose()
            glowGeo.dispose()
            glowMat.dispose()
            if (container.contains(renderer.domElement)) {
                container.removeChild(renderer.domElement)
            }
        }
    }, [])

    // Camera view presets
    useEffect(() => {
        const s = sceneState.current
        if (!s) return
        applyCameraPreset(s.camera, s.controls, cameraView, metricViewFrameRef.current, frontViewHintRef.current)
        s.requestRender?.()
    }, [cameraView])

    // Update skeleton when frame changes
    useEffect(() => {
        const s = sceneState.current
        if (!s) return
        const { joints, grid, glowPlane, axisHelper, boneGeo, ghostGeo } = s

        const hideAll = () => {
            joints.forEach(m => { m.visible = false })
            const pos = boneGeo.attributes.position
            const gpos = ghostGeo.attributes.position
            for (let i = 0; i < pos.count; i++) {
                pos.setXYZ(i, 0, -999, 0)
                gpos.setXYZ(i, 0, -999, 0)
            }
            pos.needsUpdate = true
            gpos.needsUpdate = true
        }

        if (!synthFrame?.landmarks) {
            hideAll()
            return
        }

        const landmarks = synthFrame.landmarks
        const metricViewFrame = isMetricFrame(synthFrame) ? computeMetricViewFrame(landmarks, synthFrame.viewHint) : null
        const isFirstHint = !frontViewHintRef.current && synthFrame?.viewHint?.frontView
        metricViewFrameRef.current = metricViewFrame
        if (synthFrame?.viewHint?.frontView) frontViewHintRef.current = synthFrame.viewHint.frontView
        const threshold = synthFrame?.thresholds?.maxReprojectionErrorPx
            ?? synthFrame?.synthesisInfo?.thresholds?.maxReprojectionErrorPx
            ?? 8

        const floorY = metricViewFrame?.floorY ?? DEFAULT_FLOOR_Y
        grid.position.y = floorY
        glowPlane.position.y = floorY
        axisHelper.position.y = floorY + 0.15

        if (isFirstHint && metricViewFrame) {
            applyCameraPreset(s.camera, s.controls, 'front', metricViewFrame, frontViewHintRef.current)
        }

        landmarks.forEach((lm, i) => {
            if (!joints[i]) return
            if (!isRenderableLandmark(lm)) {
                joints[i].visible = false
                return
            }
            joints[i].visible = true
            const [x, y, z] = toLandmarkVec3(lm, metricViewFrame)
            joints[i].position.set(x, y, z)
            const vis = lm.visibility ?? 1
            const opacity = lm.success === false ? 0.25 : Math.max(0.35, Math.min(1, vis))
            joints[i].material.color.setHex(qualityColor(lm, threshold))
            joints[i].material.opacity = opacity
            joints[i].material.emissiveIntensity = 0.2 + vis * 0.8
        })

        const bpos = boneGeo.attributes.position
        const gpos = ghostGeo.attributes.position
        let idx = 0
        for (const [a, b] of POSE_EDGES) {
            const lmA = landmarks[a]
            const lmB = landmarks[b]
            const okA = isReliableBoneEndpoint(lmA)
            const okB = isReliableBoneEndpoint(lmB)
            if (okA && okB) {
                const [ax, ay, az] = toLandmarkVec3(lmA, metricViewFrame)
                const [bx, by, bz] = toLandmarkVec3(lmB, metricViewFrame)
                bpos.setXYZ(idx, ax, ay, az)
                bpos.setXYZ(idx + 1, bx, by, bz)
                gpos.setXYZ(idx, ax, ay, az)
                gpos.setXYZ(idx + 1, bx, by, bz)
            } else {
                bpos.setXYZ(idx, 0, -999, 0)
                bpos.setXYZ(idx + 1, 0, -999, 0)
                gpos.setXYZ(idx, 0, -999, 0)
                gpos.setXYZ(idx + 1, 0, -999, 0)
            }
            idx += 2
        }
        bpos.needsUpdate = true
        gpos.needsUpdate = true
        s.requestRender?.()
    }, [synthFrame])

    return <div ref={mountRef} className={style.canvas} />
}
