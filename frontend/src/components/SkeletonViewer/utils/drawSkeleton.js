import { ANGLE_JOINTS, LOAD_JOINTS, POSE_EDGES } from './poseEdges.js'

const VIS_THRESHOLD = 0.5

function lm(landmarks, idx) {
    return landmarks?.[idx]
}

export function drawSkeleton(ctx, landmarks, w, h, options = {}) {
    if (!landmarks || landmarks.length < 33) return
    ctx.save()

    ctx.strokeStyle = '#00D4FF'
    ctx.lineWidth = 2
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'

    for (const [i, j] of POSE_EDGES) {
        const a = lm(landmarks, i)
        const b = lm(landmarks, j)
        if (!a || !b) continue
        if ((a.visibility ?? 1) < VIS_THRESHOLD || (b.visibility ?? 1) < VIS_THRESHOLD) continue

        ctx.beginPath()
        ctx.moveTo(a.x * w, a.y * h)
        ctx.lineTo(b.x * w, b.y * h)
        ctx.stroke()
    }

    for (let i = 0; i < landmarks.length; i += 1) {
        const point = landmarks[i]
        if (!point || (point.visibility ?? 1) < VIS_THRESHOLD) continue

        const visibilityAlpha = options.showConfidenceTint
            ? Math.max(0.35, Math.min(1, point.visibility ?? 1))
            : 1

        ctx.beginPath()
        ctx.arc(point.x * w, point.y * h, 4, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255,255,255,${visibilityAlpha})`
        ctx.fill()
        ctx.strokeStyle = '#00D4FF'
        ctx.lineWidth = 1.5
        ctx.stroke()

        if (options.showJointLabels) {
            const label = point.name ?? String(i)
            ctx.font = '11px monospace'
            ctx.fillStyle = 'rgba(10,10,12,0.72)'
            ctx.fillRect(point.x * w + 6, point.y * h - 10, 58, 14)
            ctx.fillStyle = '#E8F4FD'
            ctx.fillText(label, point.x * w + 8, point.y * h)
        }
    }

    ctx.restore()
}

export function drawPathTrace(ctx, frameTrail, w, h) {
    if (!Array.isArray(frameTrail) || frameTrail.length < 2) return
    ctx.save()
    ctx.strokeStyle = 'rgba(0, 242, 255, 0.45)'
    ctx.lineWidth = 2
    ctx.beginPath()

    frameTrail.forEach((frame, index) => {
        const leftHip = frame?.landmarks?.[23]
        const rightHip = frame?.landmarks?.[24]
        if (!leftHip || !rightHip) return

        const x = ((leftHip.x + rightHip.x) / 2) * w
        const y = ((leftHip.y + rightHip.y) / 2) * h

        if (index === 0) {
            ctx.moveTo(x, y)
            return
        }

        ctx.lineTo(x, y)
    })

    ctx.stroke()
    ctx.restore()
}

export function drawIssueMarkers(ctx, activeIssues, w, h) {
    if (!activeIssues.length) return
    ctx.save()
    const padX = w * 0.022
    const padY = h * 0.04
    const fontSize = Math.max(10, Math.round(h * 0.026))
    const chipH = fontSize * 1.7
    const chipGap = chipH * 0.3

    ctx.font = `bold ${fontSize}px monospace`

    activeIssues.forEach((issue, i) => {
        const text = issue.label ?? issue.message ?? 'ISSUE'
        const tw = ctx.measureText(text).width
        const chipW = tw + fontSize
        const y = padY + i * (chipH + chipGap)

        ctx.fillStyle = 'rgba(239, 68, 68, 0.88)'
        roundRect(ctx, padX, y, chipW, chipH, chipH * 0.3)
        ctx.fill()

        ctx.fillStyle = '#fff'
        ctx.fillText(text, padX + fontSize * 0.5, y + chipH * 0.7)
    })

    ctx.restore()
}

export function drawEventMarkers(ctx, activeEvents, w, h) {
    if (!activeEvents.length) return
    ctx.save()
    const padX = w * 0.022
    const fontSize = Math.max(10, Math.round(h * 0.026))
    const chipH = fontSize * 1.7
    const chipGap = chipH * 0.3
    const padYBottom = h * 0.04

    ctx.font = `bold ${fontSize}px monospace`

    activeEvents.forEach((event, i) => {
        const text = event.label ?? event.message ?? 'EVENT'
        const tw = ctx.measureText(text).width
        const chipW = tw + fontSize
        const y = h - padYBottom - chipH - i * (chipH + chipGap)

        ctx.fillStyle = 'rgba(34, 197, 94, 0.88)'
        roundRect(ctx, padX, y, chipW, chipH, chipH * 0.3)
        ctx.fill()

        ctx.fillStyle = 'rgba(10, 10, 12, 0.9)'
        ctx.fillText(text, padX + fontSize * 0.5, y + chipH * 0.7)
    })

    ctx.restore()
}

export function drawRepOverlay(ctx, repIndex, totalReps, phase, w, h) {
    ctx.save()
    const fontSize = Math.max(10, Math.round(h * 0.028))
    ctx.font = `bold ${fontSize}px monospace`

    const repText = `REP ${repIndex} / ${totalReps}`
    const phaseText = phase === 'ascent' ? '↑' : '↓'
    const text = `${phaseText} ${repText}`

    const tw = ctx.measureText(text).width
    const chipH = fontSize * 1.7
    const chipW = tw + fontSize
    const padX = w * 0.022
    const padY = h * 0.04

    const isAscent = phase === 'ascent'
    ctx.fillStyle = isAscent
        ? 'rgba(0, 212, 255, 0.85)'
        : 'rgba(13, 147, 242, 0.85)'
    roundRect(ctx, w - chipW - padX, padY, chipW, chipH, chipH * 0.3)
    ctx.fill()

    ctx.fillStyle = isAscent ? 'rgba(10,10,12,0.9)' : '#fff'
    ctx.fillText(text, w - chipW - padX + fontSize * 0.5, padY + chipH * 0.7)

    ctx.restore()
}

function getBarPoint(frame, w, h, barPlacementMode) {
    const ls = frame?.landmarks?.[11]
    const rs = frame?.landmarks?.[12]
    if (!ls || !rs) return null
    const yShift = barPlacementMode === 'low_bar' ? 0.025 : 0
    return {
        x: ((ls.x + rs.x) / 2) * w,
        y: ((ls.y + rs.y) / 2 + yShift) * h,
    }
}

// 구간(fromIndex ~ toIndex)만 누적 캔버스에 그림 — dot 없음
export function drawBarPassSegment(ctx, frames, fromIndex, toIndex, w, h, barPlacementMode) {
    if (!Array.isArray(frames) || toIndex <= fromIndex) return

    const start = Math.max(0, fromIndex)
    const segment = frames.slice(start, toIndex + 1)
    if (segment.length < 2) return

    ctx.save()
    ctx.strokeStyle = 'rgba(255, 200, 0, 0.85)'
    ctx.lineWidth = 2
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'
    ctx.beginPath()

    let started = false
    for (const frame of segment) {
        const pt = getBarPoint(frame, w, h, barPlacementMode)
        if (!pt) continue
        if (!started) { ctx.moveTo(pt.x, pt.y); started = true }
        else ctx.lineTo(pt.x, pt.y)
    }
    ctx.stroke()
    ctx.restore()
}

// 현재 위치 dot만 메인 캔버스에 그림
export function drawBarPassDot(ctx, frame, w, h, barPlacementMode) {
    const pt = getBarPoint(frame, w, h, barPlacementMode)
    if (!pt) return

    ctx.save()
    ctx.beginPath()
    ctx.arc(pt.x, pt.y, 5, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(255, 200, 0, 0.95)'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)'
    ctx.lineWidth = 1.5
    ctx.stroke()
    ctx.restore()
}

// 하위 호환 — 뒤로 스크럽 시 전체 재드로잉용
export function drawBarPass(ctx, frames, upToIndex, w, h, barPlacementMode) {
    drawBarPassSegment(ctx, frames, 0, upToIndex, w, h, barPlacementMode)
}

const GROUND_VIS = 0.4

function getGroundPoints(frame) {
    const lHeel = frame?.landmarks?.[29]
    const rHeel = frame?.landmarks?.[30]
    const lAnkle = frame?.landmarks?.[27]
    const rAnkle = frame?.landmarks?.[28]
    const l = (lHeel?.visibility ?? 0) > GROUND_VIS ? lHeel : lAnkle
    const r = (rHeel?.visibility ?? 0) > GROUND_VIS ? rHeel : rAnkle
    if (!l || !r) return null
    if ((l.visibility ?? 1) < GROUND_VIS || (r.visibility ?? 1) < GROUND_VIS) return null
    return { l, r }
}

export function drawGroundVector(ctx, landmarks, w, h) {
    const pts = getGroundPoints({ landmarks })
    if (!pts) return

    const lx = pts.l.x * w
    const rx = pts.r.x * w
    // groundY = estimated ground level (Y-axis reference)
    const groundY = ((pts.l.y + pts.r.y) / 2) * h

    // Vanishing point: midpoint between feet on the horizon
    const vpX = (lx + rx) / 2
    const vpY = groundY

    const depth = h * 0.32
    const bottomY = Math.min(h, groundY + depth)

    // Spread of radial lines at the bottom (wider than canvas = full coverage)
    const spreadLeft = -w * 0.15
    const spreadRight = w * 1.15

    const numRadials = 16
    const numCross = 7

    ctx.save()

    // Background fill (trapezoid shaped ground plane)
    const bg = ctx.createLinearGradient(0, groundY, 0, bottomY)
    bg.addColorStop(0, 'rgba(0, 255, 180, 0.10)')
    bg.addColorStop(1, 'rgba(0, 200, 255, 0.02)')
    ctx.fillStyle = bg
    ctx.beginPath()
    ctx.moveTo(0, groundY)
    ctx.lineTo(w, groundY)
    ctx.lineTo(w, bottomY)
    ctx.lineTo(0, bottomY)
    ctx.closePath()
    ctx.fill()

    // Z-axis radial lines: converge at vanishing point (perspective X lines)
    for (let i = 0; i <= numRadials; i++) {
        const t = i / numRadials
        const bx = spreadLeft + t * (spreadRight - spreadLeft)
        const alpha = (i === 0 || i === numRadials) ? 0.15 : 0.22
        ctx.strokeStyle = `rgba(0, 255, 180, ${alpha})`
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(vpX, vpY)
        ctx.lineTo(bx, bottomY)
        ctx.stroke()
    }

    // X-axis cross lines: exponential spacing (perspective Z lines)
    for (let r = 0; r <= numCross; r++) {
        const t = r / numCross
        // Exponential distribution — close at horizon, wide near camera
        const expT = (Math.pow(6, t) - 1) / (6 - 1)
        const y = groundY + expT * depth
        if (y > bottomY) continue

        // Clip to radial boundary at this Y level
        const leftX = vpX + (spreadLeft - vpX) * expT
        const rightX = vpX + (spreadRight - vpX) * expT

        const isHorizon = r === 0
        ctx.strokeStyle = isHorizon
            ? 'rgba(0, 255, 180, 0.90)'
            : `rgba(0, 255, 180, ${0.18 + expT * 0.22})`
        ctx.lineWidth = isHorizon ? 2 : 1
        ctx.beginPath()
        ctx.moveTo(Math.max(0, leftX), y)
        ctx.lineTo(Math.min(w, rightX), y)
        ctx.stroke()
    }

    // Horizon line (ground Y reference)
    ctx.strokeStyle = 'rgba(0, 255, 180, 0.90)'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(0, groundY)
    ctx.lineTo(w, groundY)
    ctx.stroke()

    // Foot contact tick marks on the horizon
    ctx.strokeStyle = 'rgba(0, 255, 180, 1)'
    ctx.lineWidth = 2.5
    const tickH = h * 0.018
    for (const x of [lx, rx]) {
        ctx.beginPath()
        ctx.moveTo(x, vpY - tickH)
        ctx.lineTo(x, vpY + tickH)
        ctx.stroke()
    }

    // Vanishing point dot
    ctx.beginPath()
    ctx.arc(vpX, vpY, 3, 0, Math.PI * 2)
    ctx.fillStyle = 'rgba(0, 255, 180, 0.85)'
    ctx.fill()

    // Axis labels
    ctx.font = 'bold 10px monospace'
    ctx.fillStyle = 'rgba(0, 255, 180, 0.7)'
    ctx.fillText('X', Math.min(w - 20, vpX + (spreadRight - vpX) * 0.72), groundY + depth * 0.55)
    ctx.fillText('Z', vpX + 6, groundY + depth * 0.82)

    ctx.restore()
}

export function drawCoP(ctx, frameTrail, w, h) {
    if (!Array.isArray(frameTrail) || !frameTrail.length) return

    ctx.save()
    const lineHeight = h * 0.36

    frameTrail.forEach((frame, index) => {
        const pts = getGroundPoints(frame)
        if (!pts) return

        const copX = ((pts.l.x + pts.r.x) / 2) * w
        const groundY = ((pts.l.y + pts.r.y) / 2) * h
        const progress = index / (frameTrail.length - 1)
        const alpha = 0.1 + progress * 0.65
        const isLast = index === frameTrail.length - 1

        ctx.strokeStyle = `rgba(255, 30, 30, ${alpha})`
        ctx.lineWidth = isLast ? 2 : 1
        ctx.beginPath()
        ctx.moveTo(copX, groundY)
        ctx.lineTo(copX, groundY - lineHeight)
        ctx.stroke()

        if (isLast) {
            ctx.beginPath()
            ctx.arc(copX, groundY, 4, 0, Math.PI * 2)
            ctx.fillStyle = 'rgba(255, 30, 30, 0.9)'
            ctx.fill()
        }
    })

    ctx.restore()
}

function roundRect(ctx, x, y, width, height, radius) {
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + width - radius, y)
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
    ctx.lineTo(x + width, y + height - radius)
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    ctx.lineTo(x + radius, y + height)
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
}

export function drawJointLoad(ctx, landmarks, jointLoad, w, h) {
    if (!landmarks || !jointLoad) return
    ctx.save()

    for (const [jointName, landmarkIdx] of Object.entries(LOAD_JOINTS)) {
        const load = jointLoad[jointName]
        if (load == null) continue

        const pt = lm(landmarks, landmarkIdx)
        if (!pt || (pt.visibility ?? 1) < VIS_THRESHOLD) continue

        const cx = pt.x * w
        const cy = pt.y * h
        const radius = 4 + load * 16  // 4 px at 0% → 20 px at 100%

        // Radial glow behind the circle
        const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius * 2)
        glow.addColorStop(0, `rgba(255, 60, 60, ${(load * 0.28).toFixed(3)})`)
        glow.addColorStop(1, 'rgba(255, 60, 60, 0)')
        ctx.beginPath()
        ctx.arc(cx, cy, radius * 2, 0, Math.PI * 2)
        ctx.fillStyle = glow
        ctx.fill()

        // Filled red circle
        ctx.beginPath()
        ctx.arc(cx, cy, radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255, 60, 60, ${(0.15 + load * 0.3).toFixed(3)})`
        ctx.fill()
        ctx.strokeStyle = `rgba(255, 80, 80, ${(0.65 + load * 0.35).toFixed(3)})`
        ctx.lineWidth = 1.5 + load * 1.5
        ctx.stroke()

        // Percentage label below the circle
        const pct = `${Math.round(load * 100)}%`
        ctx.font = 'bold 10px monospace'
        const tw = ctx.measureText(pct).width
        const pad = 3
        const bw = tw + pad * 2
        const bh = 14
        const labelY = cy + radius + 4

        ctx.fillStyle = 'rgba(10,10,12,0.75)'
        roundRect(ctx, cx - bw / 2, labelY, bw, bh, 3)
        ctx.fill()
        ctx.fillStyle = '#FF6060'
        ctx.fillText(pct, cx - tw / 2, labelY + bh * 0.76)
    }

    ctx.restore()
}

export function drawAngles(ctx, landmarks, jointAngles, w, h) {
    if (!landmarks || !jointAngles) return
    ctx.save()

    for (const [jointName, { vertex, a, b }] of Object.entries(ANGLE_JOINTS)) {
        const angle = jointAngles[jointName]
        if (angle === undefined || angle === null) continue

        const vPt = lm(landmarks, vertex)
        const aPt = lm(landmarks, a)
        const bPt = lm(landmarks, b)
        if (!vPt || !aPt || !bPt) continue
        if (
            (vPt.visibility ?? 1) < VIS_THRESHOLD ||
            (aPt.visibility ?? 1) < VIS_THRESHOLD ||
            (bPt.visibility ?? 1) < VIS_THRESHOLD
        ) continue

        const vx = vPt.x * w
        const vy = vPt.y * h
        const ax = aPt.x * w
        const ay = aPt.y * h
        const bx = bPt.x * w
        const by = bPt.y * h

        const dax = ax - vx
        const day = ay - vy
        const dbx = bx - vx
        const dby = by - vy
        const distA = Math.hypot(dax, day)
        const distB = Math.hypot(dbx, dby)
        if (distA < 1 || distB < 1) continue

        const normA = [dax / distA, day / distA]
        const normB = [dbx / distB, dby / distB]
        const angleA = Math.atan2(day, dax)
        const angleB = Math.atan2(dby, dbx)

        // 호 반지름: 두 레이 중 짧은 쪽의 35%, 12~40px로 클램프
        const arcR = Math.max(12, Math.min(Math.min(distA, distB) * 0.35, 40))
        const rayLen = arcR * 1.3

        // 호 방향: targetSweep(joint angle)에 가까운 방향 선택
        const targetSweep = angle * (Math.PI / 180)
        let cwSweep = angleB - angleA
        if (cwSweep < 0) cwSweep += Math.PI * 2
        let ccwSweep = angleA - angleB
        if (ccwSweep < 0) ccwSweep += Math.PI * 2
        const anticlockwise = Math.abs(ccwSweep - targetSweep) < Math.abs(cwSweep - targetSweep)
        const midAngle = anticlockwise
            ? angleA - ccwSweep / 2
            : angleA + cwSweep / 2

        // 레이 두 개
        ctx.strokeStyle = 'rgba(255, 210, 0, 0.9)'
        ctx.lineWidth = 1.5
        ctx.setLineDash([])
        ctx.beginPath()
        ctx.moveTo(vx, vy)
        ctx.lineTo(vx + normA[0] * rayLen, vy + normA[1] * rayLen)
        ctx.stroke()
        ctx.beginPath()
        ctx.moveTo(vx, vy)
        ctx.lineTo(vx + normB[0] * rayLen, vy + normB[1] * rayLen)
        ctx.stroke()

        // 부채꼴 채우기
        ctx.beginPath()
        ctx.moveTo(vx, vy)
        ctx.arc(vx, vy, arcR, angleA, angleB, anticlockwise)
        ctx.closePath()
        ctx.fillStyle = 'rgba(255, 210, 0, 0.13)'
        ctx.fill()

        // 호
        ctx.beginPath()
        ctx.arc(vx, vy, arcR, angleA, angleB, anticlockwise)
        ctx.strokeStyle = 'rgba(255, 210, 0, 0.85)'
        ctx.lineWidth = 1.5
        ctx.stroke()

        // 라벨 (호 중간 방향)
        const labelR = arcR + 14
        const lx = vx + Math.cos(midAngle) * labelR
        const ly = vy + Math.sin(midAngle) * labelR
        const text = `${Math.round(angle)}°`
        ctx.font = 'bold 11px monospace'
        const tw = ctx.measureText(text).width
        const pad = 3
        const bw = tw + pad * 2
        const bh = 15

        ctx.fillStyle = 'rgba(10,10,12,0.78)'
        roundRect(ctx, lx - bw / 2, ly - bh * 0.8, bw, bh, 3)
        ctx.fill()
        ctx.fillStyle = '#FFD200'
        ctx.fillText(text, lx - tw / 2, ly)
    }

    ctx.restore()
}
