// TODO: 목업 데이터 — 실제 분석 데이터로 교체 필요

export const squatMetrics = [
    { label: "Knee Flexion Angle", value: "92.4°", type: "performance" },
    { label: "Hip Hinge Depth", value: "118.7°", type: "performance" },
    { label: "Descent Symmetry", value: "52%", type: "performance" },
    { label: "Trunk Lean Angle", value: "34.2°", type: "risk" },
    { label: "Knee Valgus", value: "14.3°", type: "risk" },
];

export const rawSkeletonJson = {
    "session_id": "racl-20240408-001",
    "timestamp": "2024-04-08T09:14:32.441Z",
    "frame": 142,
    "source": "MediaPipe Pose v0.10",
    "subject": { "id": "user_001", "height_cm": 175, "weight_kg": 72 },
    "keypoints": [
        { "id": 0,  "name": "nose",              "x": 0.512, "y": 0.148, "z": -0.312, "visibility": 0.998 },
        { "id": 1,  "name": "left_eye_inner",     "x": 0.531, "y": 0.133, "z": -0.334, "visibility": 0.997 },
        { "id": 2,  "name": "left_eye",           "x": 0.548, "y": 0.131, "z": -0.341, "visibility": 0.996 },
        { "id": 3,  "name": "left_eye_outer",     "x": 0.564, "y": 0.134, "z": -0.338, "visibility": 0.994 },
        { "id": 4,  "name": "right_eye_inner",    "x": 0.493, "y": 0.133, "z": -0.334, "visibility": 0.997 },
        { "id": 5,  "name": "right_eye",          "x": 0.476, "y": 0.131, "z": -0.341, "visibility": 0.996 },
        { "id": 6,  "name": "right_eye_outer",    "x": 0.459, "y": 0.134, "z": -0.338, "visibility": 0.993 },
        { "id": 7,  "name": "left_ear",           "x": 0.572, "y": 0.152, "z": -0.289, "visibility": 0.981 },
        { "id": 8,  "name": "right_ear",          "x": 0.444, "y": 0.152, "z": -0.289, "visibility": 0.980 },
        { "id": 9,  "name": "mouth_left",         "x": 0.538, "y": 0.168, "z": -0.318, "visibility": 0.992 },
        { "id": 10, "name": "mouth_right",        "x": 0.486, "y": 0.168, "z": -0.318, "visibility": 0.991 },
        { "id": 11, "name": "left_shoulder",      "x": 0.601, "y": 0.284, "z": -0.142, "visibility": 0.989 },
        { "id": 12, "name": "right_shoulder",     "x": 0.411, "y": 0.284, "z": -0.142, "visibility": 0.988 },
        { "id": 13, "name": "left_elbow",         "x": 0.634, "y": 0.421, "z": -0.088, "visibility": 0.974 },
        { "id": 14, "name": "right_elbow",        "x": 0.378, "y": 0.421, "z": -0.088, "visibility": 0.973 },
        { "id": 15, "name": "left_wrist",         "x": 0.658, "y": 0.537, "z": -0.063, "visibility": 0.961 },
        { "id": 16, "name": "right_wrist",        "x": 0.354, "y": 0.537, "z": -0.063, "visibility": 0.960 },
        { "id": 17, "name": "left_pinky",         "x": 0.671, "y": 0.548, "z": -0.051, "visibility": 0.932 },
        { "id": 18, "name": "right_pinky",        "x": 0.341, "y": 0.548, "z": -0.051, "visibility": 0.931 },
        { "id": 19, "name": "left_index",         "x": 0.668, "y": 0.544, "z": -0.049, "visibility": 0.941 },
        { "id": 20, "name": "right_index",        "x": 0.344, "y": 0.544, "z": -0.049, "visibility": 0.940 },
        { "id": 21, "name": "left_thumb",         "x": 0.661, "y": 0.541, "z": -0.055, "visibility": 0.938 },
        { "id": 22, "name": "right_thumb",        "x": 0.351, "y": 0.541, "z": -0.055, "visibility": 0.937 },
        { "id": 23, "name": "left_hip",           "x": 0.578, "y": 0.531, "z":  0.000, "visibility": 0.986 },
        { "id": 24, "name": "right_hip",          "x": 0.434, "y": 0.531, "z":  0.000, "visibility": 0.985 },
        { "id": 25, "name": "left_knee",          "x": 0.597, "y": 0.718, "z":  0.081, "visibility": 0.977 },
        { "id": 26, "name": "right_knee",         "x": 0.419, "y": 0.718, "z":  0.081, "visibility": 0.972 },
        { "id": 27, "name": "left_ankle",         "x": 0.584, "y": 0.891, "z":  0.124, "visibility": 0.963 },
        { "id": 28, "name": "right_ankle",        "x": 0.428, "y": 0.891, "z":  0.124, "visibility": 0.958 },
        { "id": 29, "name": "left_heel",          "x": 0.581, "y": 0.912, "z":  0.138, "visibility": 0.944 },
        { "id": 30, "name": "right_heel",         "x": 0.431, "y": 0.912, "z":  0.138, "visibility": 0.939 },
        { "id": 31, "name": "left_foot_index",    "x": 0.603, "y": 0.934, "z":  0.107, "visibility": 0.921 },
        { "id": 32, "name": "right_foot_index",   "x": 0.409, "y": 0.934, "z":  0.107, "visibility": 0.916 }
    ],
    "derived_angles": {
        "knee_flexion_left":   92.4,
        "knee_flexion_right":  90.1,
        "hip_hinge_depth":    118.7,
        "trunk_lean_angle":    34.2,
        "knee_valgus_left":    14.3,
        "knee_valgus_right":    6.8
    }
};

export const feedbackText =
`Knee Flexion Angle — 92.4°
Your knee flexion angle of 92.4° sits within an acceptable functional range, but remains near the lower boundary for a full-depth squat. Achieving closer to 100–110° would allow greater recruitment of the vastus medialis and gluteus maximus. Consider gradually increasing depth over subsequent sessions using box squats or goblet squats as a controlled progression tool.

Hip Hinge Depth — 118.7°
A hip hinge depth of 118.7° reflects solid hip mobility and suggests the posterior chain is being engaged effectively. However, this metric alone does not confirm balanced loading. Cross-referencing with pelvic tilt data is recommended to rule out butt-wink occurring at the bottom of the movement, which could indicate hamstring tightness limiting safe depth.

Descent Symmetry — 52%
Descent symmetry at 52% indicates a moderate bilateral imbalance, with the dominant side bearing a disproportionate share of the load. Over time, this pattern can compound joint stress asymmetrically. Incorporate single-leg accessory work — such as Bulgarian split squats or step-ups — to address the weaker side. Re-assess symmetry after 3–4 weeks of targeted intervention.

Trunk Lean Angle — 34.2° ⚠
The trunk lean angle of 34.2° exceeds the recommended ceiling of 30°, placing elevated compressive and shear forces on the lumbar vertebrae, particularly L4–L5. This is commonly caused by limited ankle dorsiflexion or weak anterior core stability. Begin with heel elevation during squats to temporarily compensate while working on ankle mobility drills and core bracing patterns such as dead bugs and pallof presses.

Knee Valgus — 14.3° ⚠ High Risk
A knee valgus of 14.3° is the most significant finding in this session and should be addressed as a priority. At this degree, the medial structures of the knee — including the ACL, MCL, and medial meniscus — are exposed to increased stress during each repetition. Reduce load immediately if this pattern is consistent across sets. Focus on hip abductor and external rotator strengthening (clamshells, banded walks, single-leg RDLs), and use verbal or mirror cueing to reinforce a knees-out alignment throughout the squat.`;
