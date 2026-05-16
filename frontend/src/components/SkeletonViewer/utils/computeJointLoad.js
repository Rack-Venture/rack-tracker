// Approximate per-joint load score (0 = no load, 1 = max load) derived from
// joint angles. No force-plate data is available, so load is estimated from
// angle deviation from the neutral (extended) position — a well-established
// proxy for joint reaction force in squat biomechanics.

const KNEE_NEUTRAL  = 175  // near-full extension → baseline load
const KNEE_LOADED   = 60   // deep squat → max load

const HIP_NEUTRAL   = 175
const HIP_LOADED    = 50

const ELBOW_NEUTRAL = 165  // roughly extended arm
const ELBOW_RANGE   = 80   // max meaningful deviation

function clamp01(v) {
    return Math.max(0, Math.min(1, v))
}

function flexionLoad(angle, neutral, loaded) {
    if (angle == null) return null
    return clamp01((neutral - angle) / (neutral - loaded))
}

/**
 * Compute per-joint load score (0–1) from joint angles.
 *
 * @param {Object} jointAngles  { left_knee, right_knee, left_hip, right_hip,
 *                                left_elbow, right_elbow }  — all in degrees
 * @returns {Object}  Same joint-name keys mapped to a load score (0–1),
 *                    or null when angle data is absent.
 */
export function computeJointLoad(jointAngles) {
    if (!jointAngles) return {}

    const load = {}

    for (const side of ['left', 'right']) {
        const knee  = jointAngles[`${side}_knee`]
        const hip   = jointAngles[`${side}_hip`]
        const elbow = jointAngles[`${side}_elbow`]

        if (knee  != null) load[`${side}_knee`]  = flexionLoad(knee,  KNEE_NEUTRAL,  KNEE_LOADED)
        if (hip   != null) load[`${side}_hip`]   = flexionLoad(hip,   HIP_NEUTRAL,   HIP_LOADED)
        if (elbow != null) load[`${side}_elbow`] = clamp01(Math.abs(elbow - ELBOW_NEUTRAL) / ELBOW_RANGE)
    }

    return load
}
