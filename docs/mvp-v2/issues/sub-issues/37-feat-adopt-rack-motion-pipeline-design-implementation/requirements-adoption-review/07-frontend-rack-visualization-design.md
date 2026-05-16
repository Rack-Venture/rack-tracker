# 프론트엔드 랙 모션 시각화 기획안

## 문서 관계

- 부모 문서: `../rack-motion-adoption-design.md`
- 관련 채택 검토: `01-rack-tracker-pipeline-contract.md` ~ `06-open-questions.md`
- 참고 스타일: NVIDIA Omniverse 디지털 트윈 + OpenSim 생체역학 해석 UI 결합
- 상태: Stage 1 사용자 채택 결정 반영 중

---

## 설계 목적

현재 `skeleton3d.v1` 뷰어(`ThreeJSSkeleton.jsx`)는 panoptic_world_cm 기반 inspection 도구로 역할을 유지한다. `06-open-questions.md`의 2026-05-07 사용자 채택 결정에 따라 first frontend scope는 Stage 1 `Rack Volume Fixture Viewer`이며, 별도 `RackMotionViewer`로 구현하고 기존 `ThreeJSSkeleton.jsx`와 분리한다.
이 문서는 그것과 완전히 분리된 **파워랙 물리 분석 전용 뷰어**를 설계한다.

목표는 실제 파워랙 공간을 디지털 트윈으로 재현하고,
바벨 궤적·관절 역학·랙 근접 계측을 한 화면에서 반복 분석할 수 있는 **엔지니어링 전용 도구**를 만드는 것이다.

**비교 참고 도구**

| 카테고리 | 참고 | 채용할 요소 |
| --- | --- | --- |
| Digital Twin | NVIDIA Omniverse, Unity HDRP, Unreal Datasmith | 파워랙 low-poly mesh, 카메라 frustum, depth cue, 계측 annotation |
| Biomechanics Lab | OpenSim, Vicon Nexus, Visual3D | 관절축 시각화, 각도 arc, COM 벡터, 반투명 세그먼트 |
| Manufacturing | CATIA/ANSYS 뷰어 | 치수 annotation 스타일, 단위 레이블, 좌표계 indicator |
| Robotics Sim | MuJoCo, ROS RViz | 프레임 원점 marker, 충돌 볼륨, 관절 범위 envelope |

---

## 1. 시각화 범위

### 1.1 skeleton3d.v1 뷰어 — 변경 없이 유지

| 항목 | 유지 이유 |
| --- | --- |
| `ThreeJSSkeleton.jsx` 전체 | `panoptic_world_cm` inspection-only viewer로 역할 고정 |
| joint reprojection error 색상 | synthesis 품질 확인용. rack-domain 분석 metric 아님 |
| camera view preset (front/side/top) | display-only view helper |
| skeleton bounds 기반 scale/center | 렌더링 편의 transform. domain 좌표 아님 |

### 1.2 신규 Rack Motion Viewer — 별도 컴포넌트

| 항목 | 입력 소스 | 비고 |
| --- | --- | --- |
| 파워랙 투명 볼륨 + 프레임 엣지 | rack alignment artifact (치수) | skeleton bounds 사용 금지 |
| 격자 플로어 + 치수 annotation | rack alignment artifact | cm 단위 눈금 |
| J-cup / safety pin 위치 마커 | rack alignment artifact | |
| 바벨 shaft + endpoint sphere | BarbellEntity artifact | |
| 바벨 trajectory spline | 복수 프레임 endpoint 궤적 | |
| 인체 keypoint subset (rack-domain) | ReconstructionTarget3D (`person.*` prefix) | MediaPipe 33개 전체 아님 |
| COM 마커 + 궤적 | 선택적, 계산 가능한 경우만 | |
| 관절 각도 arc | 선택적 overlay | |
| 카메라 frustum / LOS ray | diagnostic 모드 only | |
| 품질 HUD 오버레이 | QualityMetric artifact | |

### 1.3 rack-world artifact 없이 표시 불가

| 항목 | 차단 조건 |
| --- | --- |
| 바벨 rack proximity metric | rack anchor + rack-world 필요 |
| support-contact event | rack anchor + bar endpoint + rack-world 필요 |
| unrack / rerack event | same |
| endpoint asymmetry (절대값) | rack-world 기반 높이 차이 필요 |
| GRF vector | force plate 입력 없음 |

---

## 2. 좌표 공간 처리

### 2.1 공간 분리 원칙

```
ImageSpace          source 픽셀 — 2D observation 저장 기준
    ↓ (undistort → camera ray)
CameraSpace         카메라 광학 중심 기준 3D — diagnostic only
    ↓ (triangulation)
CaptureWorldSpace   panoptic_world_cm → capture_world — reconstruction output
    ↓ (rack alignment: capture_to_rack)
RackWorldSpace      rack origin 기준 분석 좌표 — rack metric 계산 기준
    ↓ (rackToRender, display-only constant)
RenderSpace         Three.js scene 좌표 — 렌더링 전용, metric 계산 금지
```

`rackToRender`는 module-private `const`로 선언한다.
이 행렬의 역산으로 RackWorldSpace 좌표를 복원하거나 metric을 계산하는 코드를 작성하지 않는다.

### 2.2 좌표 공간 색상 뱃지

모든 숫자 metric 옆에 해당 공간 색상 뱃지를 함께 표시한다.

| 공간 | 색상 토큰 | Hex |
| --- | --- | --- |
| `capture_world` | `--space-capture` | `#2266dd` |
| `rack_world` | `--space-rack` | `#00aaaa` |
| display-only | `--space-display` | `#446677` |
| `dev_assumption` | `--space-dev` | `#884400` |
| `not_computed` | `--space-missing` | `#556680` |

**표시 규칙: unit + space badge 없는 숫자 metric 렌더 금지.**

```
✓  108.3 cm  [rack_world ●]
✗  108.3                     ← unit, space 없음
✗  108.3 cm                  ← space badge 없음
```

### 2.3 RackWorldSpace 가용 여부 판단

```
rackAlignment.status:
  "calibrated"      → rack volume 렌더 허용, teal 뱃지
  "dev_assumption"  → rack volume 렌더 허용, 주황 경고 배너
  "not_computed"    → rack volume 렌더 차단, degraded placeholder 표시
  missing/null      → same as "not_computed"
```

### 2.4 Provenance Drawer

패널 토글로 여닫을 수 있는 드로어. 다음 필드를 텍스트로 표시한다:

- `session_id`, `calibration_id`, `rack_alignment_id`
- capture_world: `unit`, `axis_up`, `calibration_ref`
- rack_world: `status`, `capture_to_rack` (calibrated / identity_assumed / not_computed)
- artifact producer version

---

## 3. 아티팩트 입력 계약 (Frontend-Facing 설계 수준)

구체적인 API schema는 backend 구현 단계에서 확정한다.
이 섹션은 frontend가 소비할 데이터 구조의 설계 수준 계약이다.

### 3.1 SessionManifest

```jsonc
{
  "sessionId": "string",
  "schemaVersion": "rack_motion_session.v1",
  "sourceRefs": {
    "skeletonJobIds": ["string"],
    "calibrationId": "string",
    "rackAlignmentId": "string | null"
  },
  "coordinateSpaces": {
    "captureWorld": { "spaceId": "capture_world", "unit": "m", "axisUp": "+y" },
    "rackWorld":   { "spaceId": "rack_world", "status": "calibrated | dev_assumption | not_computed" }
  },
  "syncQuality": { "status": "ok | partial | warn", "policyId": "string | null" }
}
```

### 3.2 CalibrationBundleSummary (frontend 요약)

```jsonc
{
  "calibrationId": "string",
  "schemaVersion": "rack_motion.calibration_bundle.v1",
  "cameras": [
    {
      "cameraId": "00_11",
      "logicalRole": "rack_top_left | rack_top_right | null",
      "imageSize": [1920, 1080],
      "captureWorldPosition_m": [-1.43, -2.397, -2.057]
    }
  ],
  "qualityStatus": "ok | warn | stale"
}
```

### 3.3 RackAlignmentSummary (frontend 요약)

```jsonc
{
  "rackAlignmentId": "string | null",
  "status": "calibrated | dev_assumption | not_computed",
  "rackDimensions_m": { "width": 1.2, "depth": 1.3, "height": 2.3 },
  "jcupHeights_m": [1.02, 1.08],
  "safetyPinHeights_m": [0.6, 0.65],
  "displayUnit": "cm",
  "captureToRackStatus": "calibrated | identity_assumed | not_computed",
  "qualityMetrics": []
}
```

치수는 이 artifact에서만 가져온다. Three.js scene bounds나 skeleton joint bounds로 추정하지 않는다.

### 3.4 RackMotionFrame (paged)

```jsonc
{
  "sessionId": "string",
  "frameIndex": 0,
  "timestampMs": 4720,
  "rackAnchors": [],
  "supportZones": [],
  "barbellEntity": {
    "leftEndpoint":  { "x": -0.6, "y": 1.083, "z": 0.0, "spaceId": "rack_world", "unit": "m", "confidence": 0.91 },
    "rightEndpoint": { "x":  0.6, "y": 1.081, "z": 0.0, "spaceId": "rack_world", "unit": "m", "confidence": 0.89 },
    "reconstructionMode": "multi_camera",
    "missingEndpoints": []
  },
  "personKeypoints": [
    { "targetId": "person.left_shoulder", "x": -0.2, "y": 1.45, "z": 0.05,
      "spaceId": "rack_world", "unit": "m", "confidence": 0.95 }
  ],
  "qualityMetrics": []
}
```

### 3.5 QualityMetric

```jsonc
{
  "metricName": "reprojection_error | sync_delta_ms | rack_alignment_quality",
  "value": 3.2,
  "unit": "px | ms | m | cm",
  "status": "ok | warn | failed",
  "policyId": "string | null",
  "spaceId": "rack_world | capture_world | null",
  "aggregationLevel": "frame | session"
}
```

### 3.6 CoordinateSpaceManifest (provenance 블록)

```jsonc
{
  "spaces": [
    { "spaceId": "capture_world", "unit": "m", "axisUp": "+y", "calibrationId": "..." },
    { "spaceId": "rack_world",    "unit": "m", "axisUp": "+y", "rackAlignmentId": "...", "status": "calibrated" }
  ],
  "transforms": [
    { "from": "capture_world", "to": "rack_world", "status": "calibrated", "transformId": "..." }
  ]
}
```

---

## 4. 렌더 모델

### 4.1 Three.js Scene 좌표 관례

```
RackWorldSpace  origin = rack floor center, Y-up, artifact unit = m
RenderSpace     origin = scene center, Y-up
rackToRender    scale × translation (display-only, rack config에서 도출)
                example: display labels convert m -> cm, render scale is scene-only

절대 금지:
  - rackToRender 역행렬로 metric 계산
  - skeleton bounds로 rackToRender scale 결정
  - Three.js camera preset position으로 RackWorldSpace 좌표 추정
```

### 4.2 파워랙 Volume Mesh — 핵심 시각화 오브젝트

파워랙을 **실제 치수 기준 투명 볼륨 + 프레임 엣지 + 격자**로 표현한다.
치수는 모두 `RackAlignmentSummary.rackDimensions_m`에서 가져오고 `displayUnit="cm"`로 변환해 표시한다.

```
RackGroup (THREE.Group, RackWorldSpace 기준 배치)
│
├── UprightEdges[4]          EdgesGeometry(BoxGeometry(upright_w, height, upright_d))
│                            LineBasicMaterial({ color: #7a9ab8, opacity: 0.70 })
│                            위치: 좌전 / 우전 / 좌후 / 우후 업라이트
│
├── CrossMemberEdges         상단 / 하단 가로 연결바
│                            LineBasicMaterial({ color: #4a6a88, opacity: 0.50 })
│
├── RackVolumeMesh           BoxGeometry(width, height, depth)
│                            MeshBasicMaterial({
│                              color: #1e4678,
│                              transparent: true, opacity: 0.06,
│                              side: THREE.BackSide, depthWrite: false
│                            })
│                            → 내부에서 보면 랙 공간 경계가 희미하게 드러남
│
├── FloorGridRack            GridHelper(width, depth, n_major, n_minor)
│                            major: rgba(60,140,200,0.25) — 50cm 간격
│                            minor: rgba(40,90,140,0.10) — 10cm 간격
│                            rack floor (Y=0)에 배치
│
├── FaceGridFront            (토글) 정면 XY 격자
├── FaceGridSide             (토글) 측면 YZ 격자
│
├── DimensionAnnotations     CSS2DRenderer 레이블
│   ├── WidthLabel           "120 cm" — 상단 가로
│   ├── HeightLabel          "230 cm" — 우측 세로
│   └── DepthLabel           "130 cm" — 우측 앞쪽 대각
│
├── JCupMarkers[]            SphereGeometry(r=3cm)
│                            MeshStandardMaterial({ color: #ffaa44, metalness: 0.6 })
│                            CSS2DLabel: "J-cup L 108 cm [rack_world]"
│
└── SafetyPinMarkers[]       CylinderGeometry(r=1.5cm, h=rack_width)
                             MeshBasicMaterial({ color: rgba(255,80,60,0.45) })
                             CSS2DLabel: "Safety 65 cm [rack_world]"
```

### 4.3 ASCII — 랙 볼륨 렌더 콘셉트

```
         ╔═════════════════╗    ← 상단 crossbar
         ║                 ║
    ┌────╫─────────────────╫────┐  ← 좌우 업라이트 (엣지 라인, steel #7a9ab8)
    │    ║                 ║    │
    │    ║  ░░░░░░░░░░░░   ║    │  ← 랙 내부 볼륨 (투명 fill, opacity 0.06)
    │    ║  ░░░░░░░░░░░░   ║    │
    │◆───╫─────◆───────◆──╫───◆│  ← J-cup markers (amber #ffaa44)
    │    ║  ┤barbell├      ║    │  ← 바벨 shaft (gold #c8a840)
    │    ║  ░░░░░░░░░░░░   ║    │
    │════╫═════════════════╫════│  ← safety pin zone (red tint)
    │    ║  ░░░░░░░░░░░░   ║    │
    └────╫─────────────────╫────┘
    ·····║·· · ·  ·  · ·  ║·····  ← floor grid (teal, 10cm/50cm)
    ·····╚═════════════════╝·····
         │← 120 cm →│              ← 치수 annotation

    치수 라벨 스타일: "120 cm" @11px mono, color #6aacf0
    단위 suffix: @9px, color #4477aa (dimmer)
```

### 4.4 바벨 엔티티

```
BarbellGroup
│
├── BarbellShaft             CylinderGeometry(r=2.5cm, length)
│                            MeshStandardMaterial({ color: #c8a840, metalness: 0.8, roughness: 0.3 })
│
├── LeftEndpointSphere       SphereGeometry(r=4.5cm)
│                            color:  ok → #f0c840 | missing → #ff4444 | single-cam → #ffdd44
│                            outline: single-camera estimate → 노란 점선 링 (ShaderMaterial)
│                            CSS2DLabel: "L  108.3 cm  [rack_world ●]"
│
├── RightEndpointSphere      same as left
│
├── TrajectorySpline         CatmullRomCurve3(past 30 frames endpoints)
│                            → TubeGeometry(radius=0.8cm)
│                            MeshBasicMaterial({ vertexColors: true })
│                            최근 프레임 → rgba(240,200,64,0.8)
│                            과거 프레임 → rgba(180,140,40,0.15) (age fade)
│
├── VelocityVector           ArrowHelper(direction, origin, length=speed×display_scale)
│                            color: #ffdd44
│                            CSS2DLabel: "0.42 m/s [rack_world]"
│
└── AsymmetryLine            LineSegments (left ↔ right endpoint Y 차이 시각화)
                             color: |diff| < 1cm → #00cc66 | < 3cm → #ffbb33 | ≥ 3cm → #ff4444
                             CSS2DLabel: "Δ 2.1 cm [rack_world]"
```

### 4.5 인체 키포인트 (rack-domain subset)

MediaPipe 33개 전체가 아니라 rack motion 분석에 필요한 `person.*` target subset만 렌더한다.

```
PersonGroup
│
├── KeypointSpheres[]        SphereGeometry(r=1.8cm)
│                            targetId 기준: person.left_shoulder, person.right_shoulder,
│                              person.left_hip, person.right_hip, person.left_knee 등
│                            quality color:
│                              ok → #00d4ff | warn → #fbbf24 | fail → #7c8596
│
├── BoneLines                rack-domain subset edges만
│                            LineBasicMaterial({ color: #0099cc, opacity: 0.75 })
│
├── SegmentMeshes[]          (토글) 반투명 신체 세그먼트 mesh
│                            MeshBasicMaterial({ color: rgba(0,160,200,0.08) })
│                            OpenSim 스타일 semi-transparent capsule segments
│
├── COMMarker                SphereGeometry(r=3cm)
│                            MeshStandardMaterial({ color: #ff6644, emissive: #441100 })
│                            CSS2DLabel: "COM [rack_world]"
│
├── COMTrail                 Line (최근 60프레임 COM 위치)
│                            opacity age-fade: 최근 → 0.7, 오래된 것 → 0.05
│                            color: rgba(255,100,68,varies)
│
└── JointAngleArcs[]         (토글) 주요 관절 각도 시각화
                             ArcGeometry (SphereGeometry slice)
                             MeshBasicMaterial({ color: rgba(255,200,0,0.6), side: DoubleSide })
                             CSS2DLabel: "knee L  92°"
```

### 4.6 카메라 시각화 (diagnostic 모드)

기본 비활성. 우측 상단 Diagnostic 버튼으로 토글.

```
CameraGroup
│
├── CameraPositions[]        OctahedronGeometry(r=5cm)
│                            MeshStandardMaterial({ color: #60cc60 })
│                            CSS2DLabel: "00_11\nrack_top_left [capture_world]"
│
├── FrustumVolumes[]         CameraModel intrinsic + extrinsic 기반 Frustum mesh
│                            MeshBasicMaterial({ color: rgba(100,200,100,0.10) })
│                            EdgesGeometry 외곽: rgba(100,200,100,0.50)
│
└── LOSRays[]                선택 관절 → 각 카메라 방향 ray
                             (선택된 frame + 선택된 joint에서만 활성)
                             LineBasicMaterial({ color: rgba(100,200,100,0.50) })
```

### 4.7 분석 오버레이 (토글)

```
AnalysisOverlayGroup
│
├── ROMZones[]               파워랙 내 동작 범위 볼륨 (BoxGeometry)
│                            ok:              rgba(0,180,100,0.08)
│                            approaching:     rgba(255,180,0,0.10)
│                            at_limit:        rgba(255,60,40,0.12)
│
├── ProximityZones[]         J-cup / safety pin 근접 경고 볼륨
│                            rgba(255,100,0,0.10)
│
└── EventMarkers[]           support-contact / unrack / rerack 이벤트 위치
                             SphereGeometry + CSS2DLabel
                             color by event type (후속 event policy에서 정의)
```

---

## 5. UI/UX 레이아웃

### 5.1 전체 레이아웃

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ ▌ Rack Motion Viewer  [rack_world ●]  [dev_assumption ⚠]  [sync: ok ✓]  [Q: 87%]  │
├─────────────────┬──────────────────────────────────────────────┬────────────────────┤
│                 │                                              │                    │
│  SESSION INFO   │            3D VIEWPORT                       │  FRAME INSPECTOR   │
│  ─────────────  │                                              │  ────────────────  │
│  session: a3f…  │  ┌────────────────────────────────────┐      │  frame:  142       │
│  calib:   c8b…  │  │                                    │      │  t:      4720 ms   │
│  align:   ⚠dev  │  │   [파워랙 투명 볼륨 + 격자]        │      │  ────────────────  │
│                 │  │   [바벨 shaft + endpoint + trail]  │      │  bar_vel           │
│  SPACE LEGEND   │  │   [skeleton subset + COM trail]    │      │    0.42 m/s        │
│  ─────────────  │  │   [치수 annotation]                 │      │    [rack_world ●]  │
│  ● capture_w    │  │                                    │      │  ────────────────  │
│  ● rack_world   │  └────────────────────────────────────┘      │  left endpoint     │
│  ⚠ dev_assum.   │  [Front][Side][Top][Free]   [Diag ○]         │    y: 108.3 cm     │
│                 ├──────────────────────────────────────────────┤    [rack_world ●]  │
│  VIEW TOGGLES   │  ▐▌  ◀◀  ◀  ▶  ▶▶  1×  [speed ▼]           │    conf: 0.91      │
│  ─────────────  │  ═══════════◆═══════════════════════════     │  ────────────────  │
│  ☑ Rack Mesh    │  · · · ·│sync_warn│ ·event· │ · · · · ·     │  reprojection      │
│  ☑ Barbell      │  0 s          4.7 s              18.3 s      │    L: 3.2 px ✓     │
│  ☑ Skeleton     ├──────────────────────────────────────────────┤    R: 4.1 px ✓     │
│  ☑ COM Trail    │                                              │                    │
│  ☐ Segments     │  LIVE METRIC HUD                             │  QUALITY DETAIL    │
│  ☐ Joint Axes   │  ┌──────────┐ ┌──────────┐ ┌────────────┐   │  ────────────────  │
│  ☐ Cameras      │  │ bar vel  │ │asymmetry │ │ rack prox  │   │  sync:       ✓ ok  │
│  ☐ LOS Rays     │  │ 0.42 m/s │ │  2.1 cm  │ │  N/A ────  │   │  reprojection:✓ok  │
│  ☐ ROM Zones    │  │[rack_w ●]│ │[rack_w ●]│ │ [missing]  │   │  rack_world: ⚠     │
│  ☐ Proximity    │  └──────────┘ └──────────┘ └────────────┘   │    dev_assumption  │
│                 │                                              │                    │
│  [▼ Provenance] │                                              │  [▼ Provenance]    │
└─────────────────┴──────────────────────────────────────────────┴────────────────────┘
```

### 5.2 상태 헤더 (최상단 바)

| 요소 | 내용 |
| --- | --- |
| 뷰어 이름 | "Rack Motion Viewer" |
| 활성 공간 뱃지 | `[rack_world ●]` (teal) / `[capture_world ●]` (blue) |
| Alignment 뱃지 | `[dev_assumption ⚠]` / `[calibrated ✓]` / `[not_computed ✕]` |
| Sync 상태 | `[sync: ok ✓]` / `[sync: warn ⚠]` |
| 품질 요약 | `[Q: 87%]` — 현재 프레임 quality 종합 |

### 5.3 타임라인

- 프레임 스크러버 (◆ = 현재 위치)
- 재생 컨트롤: ◀◀ 처음 / ◀ 이전 프레임 / ▶ 재생·정지 / ▶▶ 마지막
- 재생 속도: 0.1× / 0.25× / 0.5× / 1× / 선택
- 이벤트 마커: 타임라인 위에 수직 컬러 선 (event type별 색상)
- sync_warn 구간: 황색 배경 표시
- 프레임 품질 gradient: 타임라인 하단 컬러 바 (ok=초록, warn=노랑, fail=빨강)

### 5.4 라이브 메트릭 HUD

최대 4개 metric 카드를 뷰포트 하단에 배치.

```
┌────────────────────────┐
│ metric name            │  ← 12px, --metric-label
│ 0.42 m/s               │  ← 24px mono, --metric-value
│ [rack_world ●]         │  ← 11px, space badge
└────────────────────────┘
```

- threshold 초과 시: 카드 border `#ff4444`, 값 색상 `#ff4444`
- `not_computed` / missing: "N/A ────" 표시, opacity 0.5

### 5.5 프레임 인스펙터 (오른쪽 패널)

- frameIndex, timestampMs
- 바벨: left/right endpoint (x, y, z, unit, conf), reconstructionMode
- 인체: 주요 관절 좌표 (rack-domain subset)
- 프레임별 QualityMetric 목록 (status 아이콘 + value + unit)
- Quality Detail: 각 metric 상세

### 5.6 Provenance Drawer

사이드바 / 인스펙터 하단에 접이식 드로어.

```
▼ Provenance
  session_id:         a3f9c...
  calibration_id:     c8b2a...
  rack_alignment_id:  dev-rig-001
  capture_world:      unit=m, axis_up=+y, display_unit=cm
  rack_world:         status=dev_assumption
  capture_to_rack:    identity_assumed
  producer:           rack_motion_session.v1
```

---

## 6. 품질 및 실패 상태

### 6.1 상태별 시각화

| 상태 | 3D 뷰어 처리 | HUD | 배너 |
| --- | --- | --- | --- |
| rack alignment missing | 랙 볼륨 미표시, dashed degraded placeholder | 모든 rack_world metric "N/A ────" | `⚠ RackWorldSpace not available — alignment not computed` (주황) |
| `capture_to_rack` not_computed | 랙 볼륨 표시, 주황 점선 외곽 | rack_world metric "N/A" | `⚠ capture-to-rack not computed` |
| `dev_assumption` alignment | 랙 볼륨 표시, 점선 + dev badge | dev badge 부착 | `🔧 Dev-only alignment active — not production grade` |
| low confidence joint | 해당 keypoint 회색, opacity 감소 | reprojection 황색 | 없음 (frame inspector 표시) |
| high reprojection error | 해당 keypoint 빨간색 | reprojection 빨간색 | 없음 |
| missing barbell endpoint | endpoint sphere 빨간색 + "?" | endpoint metric 빨간색 | 없음 |
| single-camera estimate | endpoint 노란 점선 테두리, "est." label | `⚠ single-camera est.` badge | 없음 |
| sync warning | 타임라인 구간 황색 강조 | sync metric 황색 | 없음 |
| unit/axis mismatch | 렌더 중단, 오류 메시지 | — | `✕ Coordinate unit/axis mismatch — cannot render` (빨간) |
| stale calibration | calibration badge 황색 | — | `⚠ Calibration may be stale` |
| stale rack config | alignment badge 황색 | — | `⚠ Rack alignment may be stale` |

### 6.2 Degraded Placeholder (rack volume 없을 때)

```
- BoxGeometry(120, 230, 130) — alignment 없어 치수는 표준 파워랙 추정값
- EdgesGeometry + LineDashedMaterial (dashed 점선)
- color: rgba(128,128,160,0.30)
- CSS2DLabel (중앙): "RackWorldSpace\nnot computed"
- 사용자가 수동 치수 입력 시에도 동일 placeholder로 표시 (분석 사용 불가)
```

### 6.3 필수 표시 규칙 요약

1. 모든 metric 숫자: **unit + space badge 항상 병기**
2. `dev_assumption` 상태: **배너 필수, 경고 배지 항상 표시**
3. `single_camera_estimate`: **diagnostic mode only, "est." label + 노란 테두리 필수**
4. `not_computed` 공간의 metric: **"N/A ────" 표시, 숫자 렌더 금지**
5. capture_world와 rack_world의 숫자를 같은 카드에 혼용하지 않는다

---

## 7. 단계적 채택 계획

### Stage 0 — 현재 상태 (완료)

- `skeleton3d.v1` viewer (`ThreeJSSkeleton.jsx`) inspection-only 유지
- rack motion: schema validation slice만 존재
- Frontend rack motion UI 없음

### Stage 1 — Rack Volume Fixture Viewer

**목표:** synthetic rack-world fixture로 파워랙 3D 볼륨을 표시하고 coordinate space 분리를 검증한다.

구현 범위:
- 신규 `RackMotionViewer` 컴포넌트 (기존 파일 수정 없음)
- `RackAlignmentSummary` fixture (synthetic TOML/JSON) 로드
- 파워랙 volume mesh + frame edges + floor grid + dimension annotation 렌더
- `capture_to_rack = identity_assumed` 상태 명시, dev_assumption 배너
- `skeleton3d.v1` person joint를 draft `ReconstructionTarget3D`로 import해 keypoint 표시
- Provenance Drawer 기초

입력 아티팩트:
- `virtual_power_rack_dev_alignment.json` (synthetic rack dimensions)
- 기존 `skeleton3d.v1`

### Stage 2 — Panoptic Dev Rack Visualization

**목표:** Panoptic fixture (00_11/00_21)를 dev-only virtual rack setup으로 시각화한다.

구현 범위:
- `CalibrationBundleSummary` (PanopticCaptureRig171204Pose1)
- `RackAlignmentSummary` (`VirtualPowerRackDevRig`, status=dev_assumption)
- 카메라 frustum/position 표시 (diagnostic 모드)
- dev_assumption 경고 배너 완성
- 바벨 endpoint synthetic fixture 지원

### Stage 3 — Real Rack Alignment

**목표:** 실제 파워랙 환경 calibration + rack alignment로 production-grade 시각화를 지원한다.

구현 범위:
- 실제 `rack_alignment` artifact (calibrated `capture_to_rack`)
- rack_world metric 표시 (HUD 완성)
- 바벨 endpoint producer 연결 (detector 또는 manual annotation)
- 바벨 trajectory spline, asymmetry indicator, velocity vector
- COM 마커 + 궤적

### Stage 4 — Full Diagnostics + Event Review

**목표:** 분석 루프에서 실제로 쓸 수 있는 완성 뷰어.

구현 범위:
- 관절 각도 arc overlay (OpenSim 스타일)
- support-contact / unrack / rerack 이벤트 타임라인 마커
- ROM zone overlay
- LOS ray + reprojection overlay (per-frame, selected joint)
- 이벤트별 frame jump
- LLM 분석 패널 연동 (rack event context → coaching feedback panel)

---

## 8. 인수 기준

| # | 기준 | 확인 방법 |
| --- | --- | --- |
| 1 | 프론트엔드는 RackWorldSpace를 정의하거나 계산하지 않는다 | 코드 리뷰: skeleton bounds / viewer bounds로 rack 치수 추정 없음 |
| 2 | RackWorldSpace 렌더링은 artifact가 alignment/provenance를 제공한 경우에만 허용된다 | `status === "not_computed"` 이면 rack volume 미표시, degraded placeholder 표시 |
| 3 | `rackToRender`는 display-only module-private const다 | metric 계산 코드에서 `rackToRender` 참조 없음 |
| 4 | missing/degraded 상태가 모두 시각적으로 구분된다 | 각 상태별 배너, 색상, label이 6.1 상태표와 일치 |
| 5 | capture_world와 rack_world 값이 동일 metric 카드에 혼용되지 않는다 | 모든 metric에 spaceId badge 표시 |
| 6 | 모든 숫자 metric에 unit과 space badge가 표시된다 | unit + space badge 없는 숫자 렌더 금지 |
| 7 | `dev_assumption` alignment는 경고 배너와 함께 표시된다 | Stage 2 빌드에서 배너 확인 |
| 8 | `single_camera_estimate`는 calibrated 3D로 표시되지 않고 diagnostic mode에서만 구분된다 | "est." badge, 노란 점선 테두리 |
| 9 | `ThreeJSSkeleton.jsx`는 변경되지 않는다 | diff 없음 |
| 10 | rack volume mesh 치수는 artifact 입력에서만 온다 | 코드 리뷰: hardcoded 치수 상수 없음 |

---

## 동기화 규칙

| 상황 | 처리 |
| --- | --- |
| `RackAlignmentSummary` API schema가 바뀜 | 3.3 계약과 6.1 상태표를 갱신한다 |
| `rack_motion.py` entity shape가 바뀜 | 3.4 RackMotionFrame 계약을 갱신한다 |
| Stage N 구현이 시작됨 | 해당 Stage 목표와 입력 아티팩트를 구현 문서로 승격한다 |
| `ThreeJSSkeleton.jsx`가 수정됨 | skeleton3d.v1 viewer가 rack motion viewer로 오염되지 않았는지 확인한다 |
| 좌표 공간 정책이 바뀜 (`02-coordinate-spaces.md`) | 2.1 공간 분리 원칙과 2.3 판단 로직을 함께 갱신한다 |
| 품질 metric catalog가 확정됨 (`04-quality-metrics.md`) | 6.1 상태표와 5.4 HUD metric 목록을 갱신한다 |
