// MediaPipe BlazePose 33 landmark connections
export const POSE_EDGES = [
    // Face
    [0, 1], [1, 2], [2, 3], [3, 7],
    [0, 4], [4, 5], [5, 6], [6, 8],
    [9, 10],
    // Shoulders
    [11, 12],
    // Left arm
    [11, 13], [13, 15],
    // Right arm
    [12, 14], [14, 16],
    // Left hand
    [15, 17], [17, 19], [19, 15], [15, 21],
    // Right hand
    [16, 18], [18, 20], [20, 16], [16, 22],
    // Torso
    [11, 23], [12, 24], [23, 24],
    // Left leg
    [23, 25], [25, 27], [27, 29], [29, 31], [27, 31],
    // Right leg
    [24, 26], [26, 28], [28, 30], [30, 32], [28, 32],
]

// joint name → landmark index at the vertex of the angle
export const ANGLE_JOINTS = {
    left_elbow:    { vertex: 13, a: 11, b: 15 },
    right_elbow:   { vertex: 14, a: 12, b: 16 },
    left_knee:     { vertex: 25, a: 23, b: 27 },
    right_knee:    { vertex: 26, a: 24, b: 28 },
    left_hip:      { vertex: 23, a: 11, b: 25 },
    right_hip:     { vertex: 24, a: 12, b: 26 },
}

// joint name → landmark index for heatmap circles
export const LOAD_JOINTS = {
    left_shoulder:  11,
    right_shoulder: 12,
    left_elbow:     13,
    right_elbow:    14,
    left_hip:       23,
    right_hip:      24,
    left_knee:      25,
    right_knee:     26,
    left_ankle:     27,
    right_ankle:    28,
}
