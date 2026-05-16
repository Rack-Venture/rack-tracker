# [design] 3D 스켈레톤 합성 재설계 검토 계획
Parent: #29

## 문서 관계
- 이 문서는 `3d-skeleton-synthesizer-plan.md`와 `triangulation-implementation-plan.md`에서 파생한 재검토용 설계 문서다.
- 목적은 현재 3D 합성 결과가 기대와 다르게 누워 보이거나, 시점/기준점/측량 방식이 의심될 때 구현을 바로 수정하지 않고 입력 산출물, 시점 정렬, 대조 검증, triangulation 절차를 분리해 다시 판단하는 것이다.
- 커밋 단위 작업 이력과 승인 후 management log는 부모 관리 문서에 기록한다. 이 문서에는 검토 항목, 결정 기준, 필요한 진단 artifact만 남긴다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## 문제 인식
- 현재 관찰된 문제는 단순 렌더링 보정보다 상위의 기하 계약 문제일 수 있다.
- 3D 스켈레톤이 누워 보이는 원인은 최소 네 갈래로 분리해야 한다.
  - 2D 입력 산출물 자체가 잘못된 시점, 해상도, 프레임, 좌우 관절을 담고 있을 가능성
  - 두 시점의 카메라 ID, 위치, 캘리브레이션, timestamp/frame 정합이 틀렸을 가능성
  - triangulation이 사용하는 좌표계, 왜곡 보정, projection matrix, 단위가 서로 어긋났을 가능성
  - backend `skeleton3d.v1` 좌표는 맞지만 Three.js viewer의 world-to-view 변환, floor 기준, camera preset이 잘못됐을 가능성
- 따라서 다음 구현은 "코드 한 곳 수정"이 아니라, 각 단계별로 관측 가능한 중간 결과를 남기고 사용자가 수치와 그림을 검토할 수 있게 해야 한다.

## 종료 메모
- #29에서는 이 문서를 재설계 구현 범위가 아니라 후속 판단을 위한 진단 기록으로 보존한다.
- `skeleton3d.v1`, debug report, camera binding, `viewHint` 기반 viewer correction까지가 #29의 최종 실험 baseline이다.
- `rack_session_world.v1`, session scene manifest, fixed hardware profile, full browser visual regression은 MVP2-03 또는 별도 후속 이슈에서 다시 다룬다.

## 검토 순서
1. 각 2D 스켈레톤 추정 결과가 무엇을 의미하는지 고정한다.
2. 두 시점의 카메라 ID, 시간축, 이미지 좌표, world 좌표 기준을 맞춘다.
3. 두 2D 결과가 같은 신체 관절과 같은 순간을 보고 있는지 epipolar/reprojection 관점으로 대조한다.
4. triangulation 방식과 실패 판정 기준을 명시하고, GT 또는 재투영 결과로 검증한다.
5. backend 3D 좌표계와 frontend viewer 좌표계를 별도 단계로 검증한다.

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RED-01 | 2D 출력 계약 재검토 | skeleton artifact | 결정됨 | 2D skeleton artifact는 landmarks와 함께 카메라 binding(`cameraId`, `calibrationRef`, `calibrationCameraId`) 및 이미지 좌표 기준(`videoInfo.width/height`, `imageCoordinateSpace.pixelBasis`, 선택적 `preprocessTransform`)을 가져야 한다. 캘리브레이션 행렬 전체는 참조로 두고, artifact만 봐도 어떤 camera model로 pixel/undistorted 좌표를 복원해야 하는지 알 수 있어야 한다. MediaPipe `z`는 첫 triangulation 계산에 쓰지 않고 필요 시 진단값으로만 취급한다. | `calibrationVersion`/hash를 필수 필드로 둘지, legacy artifact 보정 경로에서만 선택 필드로 둘지 결정해야 한다. | 2D artifact schema/code 변경안에 `cameraBinding`과 `imageCoordinateSpace`를 추가하고, A/B 한 프레임의 normalized, pixel, visibility, frame metadata, binding trace를 남긴다. | 2D 스켈레톤 추정 아웃풋 |
| RED-02 | 시점/카메라 binding | 2D artifact + pair manifest | 결정됨 | 일반 synthesis는 Video A/B slot, source job id, source artifact camera id, request camera id, session manifest camera id, calibration camera id를 한 줄로 추적한다. `171204_pose1` Panoptic fixture 실험은 업로드 파일에서 카메라를 매번 추론하지 않고 `fixedPanopticFixtureRig="171204_pose1.front_oblique_00_21_00_11.v1"`를 source of truth로 사용한다. 이 fixed fixture에서 `front_left=00_21`, `front_right=00_11`이다. | 제품 런타임에서 사용자 명시 선택 UI를 둘지, session scene manifest 선택으로 제한할지 결정해야 한다. | fixed fixture path에서는 `hd_00_21_2min.mp4`와 `hd_00_11_2min.mp4`를 사용해 `sourceJobIdA/B`, rig slot, calibration camera id, calibration ref를 보여주는 `synthesis_pair_manifest_debug.v1`을 만든다. | 시점 및 위치 정렬, Panoptic Fixture Camera Rig |
| RED-03 | 시간 정합 | frame alignment | 검증 필요 | 첫 검토는 timestamp와 frameIndex를 모두 출력해 같은 순간을 pairing하는지 검증한다. GT-aligned fixture에서는 `frameIndex`와 media-local `timestampMs`가 sanity check 기준이며, 실제 업로드 영상에서는 media-local timestamp만으로 충분한지 별도 검증한다. | 실제 영상에서 capture timestamp 또는 offset 보정이 필요한지 결정해야 한다. | paired frame sample 10개에 대해 A/B `frameIndex`, `timestampMs`, `timestampDeltaMs`, `frameIndexDelta`를 `frame_alignment_debug.v1`로 기록한다. | 시점 및 위치 정렬 |
| RED-04 | 이미지 좌표계와 왜곡 보정 | observation/camera geometry | 결정됨 | 관측 trace는 normalized 좌표, pixel 좌표, undistorted normalized camera coordinate, camera/world ray를 분리해 기록한다. 첫 구현의 triangulation 입력은 `K`, `distCoef`로 보정한 undistorted normalized 좌표와 각 camera의 normalized projection matrix(`[R|t]`)를 기준으로 한다. | resize/crop/letterbox/rotate가 있는 artifact의 `preprocessTransform` schema를 실제 코드 계약으로 확정해야 한다. | 한 관절 기준 `normalized -> pixel -> undistorted -> camera ray -> world ray -> reprojection` 숫자와 camera model id를 `observation_trace_debug.v1`로 남긴다. | 2D 출력, triangulation |
| RED-05 | 두 시점 대조 | cross-view validation | 구현 필요 | triangulation 전에 epipolar/Sampson residual, 양쪽 visibility/presence, image bounds, 관절 이름 대응, 좌우 뒤집힘 가능성을 검사하는 diagnostic layer를 둔다. 좌우 swap 의심은 실패 판정과 분리해 `swap_suspicion=true` 같은 진단 플래그로 남긴다. | epipolar threshold는 fixture p95/p99 분포를 보고 확정한다. low-visibility 기본 기준은 `visibility`/`presence` 중 하나라도 `< 0.5`이면 제외하는 초안으로 시작한다. | frame/joint별 epipolar distance, visibility, bounds result, swap suspicion을 `cross_view_validation_debug.v1`로 정의한다. | 두 개를 대조하는 방법 |
| RED-06 | triangulation 방식 | geometry service | 결정됨 | 첫 기준선은 calibrated two-view DLT triangulation이다. 입력은 undistorted normalized 좌표이고, projection matrix convention은 Panoptic calibration의 `x = K * (R * X + t)`, camera center `-R^T * t`, world unit `cm`를 따른다. homogeneous `w`, cheirality, reprojection error를 모두 검증한다. | OpenCV `triangulatePoints` wrapper와 직접 SVD 구현의 비교는 구현 검증용 선택 작업으로 남긴다. | GT 3D point -> camera reprojection -> DLT triangulation round trip fixture를 만들고 `triangulation_trace_debug.v1`에 `X_h`, `X_world`, camera depth, reprojection error, failure reason을 남긴다. | 3D 합성 삼각측량 |
| RED-07 | 기준점/좌표계 | output coordinate system | 결정됨 | `panoptic_world_cm`은 fixture evaluation/regression 전용 좌표계로만 유지한다. 제품/runtime 합성 결과는 세션 단위 world인 `rack_session_world.v1`을 명시해야 하며, backend output은 world coordinate와 body-local/viewer 좌표계를 섞지 않는다. `outputCoordinateSystem`은 literal `panoptic_world_cm`에 고정하지 않는다. | `rack_session_world.v1`의 제품 기준 origin, unit, up/forward axis, rack/floor anchor를 최종 확정해야 한다. | `skeleton3d.v1`에 `outputCoordinateSystem`, world coordinate, optional display transform, floor/reference metadata를 분리하는 schema 변경안을 만든다. | 기준점 및 위치 정렬, Decision: Session World Separation |
| RED-08 | 누워 보임 진단 | rendering boundary | 결정됨 | backend world coordinate와 frontend/Three.js viewer transform을 분리한다. Three.js는 Y-up viewer coordinate를 사용하되, backend의 `rack_session_world.v1` 또는 fixture world는 `toViewTransform`에서만 변환한다. | dataset별/manifest별 axis metadata를 어느 필드명으로 전달할지 확정해야 한다. | 한 frame의 `nose`, `mid_hip`, `ankle` world 좌표와 viewer 좌표, axis mapping, OrbitControls target을 동시에 덤프하는 `viewer_transform_debug.v1` overlay를 만든다. | 렌더링 경계 |
| RED-09 | 품질/실패 판정 | quality contract | 결정됨 | `success=false` 관절은 renderable position과 진단용 후보 좌표를 분리한다. 실패 사유는 `low_visibility`, `out_of_bounds`, `degenerate_homogeneous_point`, `behind_camera`, `high_reprojection_error`, `epipolar_mismatch` 같은 명시 코드로 남긴다. | viewer에서 실패 관절을 숨길지, ghost로 보여줄지, smoothing 후보로만 남길지 UX 정책을 결정해야 한다. | frame/joint별 `failureReason`, reprojection error, epipolar residual, source visibility/presence, renderable flag를 debug report에 요약한다. | triangulation, rendering |
| RED-10 | 사용자 검토 artifact | debug output | 구현 필요 | MVP 검토용 debug artifact 묶음은 `synthesis_pair_manifest_debug.v1`, `frame_alignment_debug.v1`, `observation_trace_debug.v1`, `cross_view_validation_debug.v1`, `triangulation_trace_debug.v1`, `viewer_transform_debug.v1`을 기본 목록으로 둔다. JSON summary와 CSV table을 우선하고, A/B overlay 이미지와 3D axis screenshot은 사람이 확인해야 하는 단계에서 생성한다. | 각 artifact를 API 응답, job artifact repository, 개발용 파일 중 어디에 저장할지 결정해야 한다. | 위 debug artifact들을 묶는 `synthesis_debug_report.v1` envelope 초안을 작성하고, fixed fixture `00_21/00_11` 재검증 결과를 연결한다. | 전체 검토 흐름, Required Debug Artifact |

## 2D 스켈레톤 추정 아웃풋

### 설계 수정 방안: 2D 관측값과 카메라 캘리브레이션 binding
2D skeleton은 각 카메라 이미지 평면에서 감지된 관절 관측값이므로, 그 값만으로는 절대좌표 3D skeleton을 만들 수 없다. 3D 합성은 반드시 해당 관측값이 나온 카메라의 내부 파라미터(`K`), 왜곡 계수(`distCoef`), 외부 파라미터(`R`, `t`)와 같은 캘리브레이션 정보를 기준으로 pixel 좌표를 보정하고, 두 시점의 관측선을 교차시켜야 한다.

단일 카메라의 2D 관절점을 역투영한 결과는 완성된 3D point가 아니라 깊이가 아직 결정되지 않은 camera ray/관측선이다. 실제 3D 관절점은 같은 frame/joint에 대한 두 카메라의 관측선을 session world에서 대조하고 triangulation해 추정한다.

따라서 2D skeleton artifact의 계약은 다음처럼 수정한다.

- 2D artifact는 `frames[].landmarks[]`뿐 아니라 이 관측값이 어떤 카메라에서 나온 것인지 나타내는 binding metadata를 가져야 한다.
- 캘리브레이션 행렬 전체를 2D artifact에 복사하지는 않는다. 대신 `calibrationRef`, `cameraId`, `calibrationCameraId`, 가능하면 calibration file hash/version을 저장해 같은 카메라 모델을 재현 가능하게 참조한다.
- `cameraId`는 사용자가 명시 선택한 값을 우선하고, filename 추론은 legacy artifact 또는 개발용 fallback으로만 취급한다. `171204_pose1` fixed fixture path에서는 filename 추론을 쓰지 않고 `00_21`/`00_11` rig binding을 고정 사용한다.
- 3D synthesis request의 `cameraIdA/B`는 2D artifact 안의 `cameraId` 또는 `calibrationCameraId`와 일치해야 한다. 불일치하면 잘못된 절대좌표 환산 위험이 있으므로 합성을 실패시킨다.
- `videoInfo.width/height`는 normalized 좌표를 pixel 좌표로 바꾸는 기준이며, calibration의 이미지 해상도와 다르면 resize/crop/letterbox transform이 명시되어야 한다.
- preprocessing이 원본 이미지를 resize, crop, letterbox, rotate 했다면 `preprocessTransform`을 artifact에 저장한다. 이 정보가 없으면 `x * width`, `y * height`만으로 camera model 좌표에 올리는 것이 틀릴 수 있다.

권장 schema 초안:

```json
{
  "cameraBinding": {
    "sourceCameraId": "00_01",
    "calibrationRef": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
    "calibrationCameraId": "00_01",
    "calibrationVersion": "sha256:...",
    "bindingSource": "user_selected"
  },
  "imageCoordinateSpace": {
    "landmarkSpace": "mediapipe_normalized_image",
    "pixelBasis": {
      "width": 1920,
      "height": 1080
    },
    "preprocessTransform": null
  }
}
```

합성기는 이 binding을 사용해 아래 순서로 절대좌표를 복원한다.

1. `landmarks[].x/y`를 `pixelBasis.width/height` 기준 pixel 좌표로 변환한다.
2. `calibrationRef + calibrationCameraId`로 camera model을 로드한다.
3. `K`, `distCoef`로 pixel 좌표를 undistorted normalized camera coordinate로 보정한다.
4. 각 카메라의 `R`, `t` 또는 normalized projection matrix로 2D 관측값을 session world의 camera ray/관측선으로 역투영한다.
5. 같은 frame/joint의 두 관측선을 epipolar/reprojection 기준으로 대조한 뒤 triangulation한다.
6. 결과를 `outputCoordinateSystem`에 명시된 world 좌표계, 예: `rack_session_world.v1`, 로 저장한다.

핵심 결정은 "2D skeleton에 캘리브레이션 행렬을 내장할지"가 아니라 "2D 관측값과 카메라 캘리브레이션 참조가 끊기지 않게 보존할지"다. MVP 재설계에서는 참조형 binding을 기본으로 두고, 디버그 artifact에서만 실제 `K/distCoef/R/t` 요약을 덤프한다.

### 반드시 확인할 필드
- `videoInfo.width`, `videoInfo.height`: normalized 좌표를 pixel 좌표로 바꾸는 기준이다.
- `videoInfo.sourceFps`, `effectiveSamplingFps`: timestamp와 frameIndex 정합을 해석하는 기준이다.
- `cameraBinding.sourceCameraId`: 2D 관측값이 나온 실제 카메라 ID다.
- `cameraBinding.calibrationRef`, `cameraBinding.calibrationCameraId`: pixel 좌표를 보정하고 절대좌표로 환산할 camera model 참조다.
- `imageCoordinateSpace.pixelBasis`: normalized 좌표를 pixel 좌표로 변환할 기준 해상도다.
- `imageCoordinateSpace.preprocessTransform`: resize, crop, letterbox, rotate가 있었는지 설명하는 선택 필드다.
- `frameIndex`, `timestampMs`: 두 카메라의 같은 순간을 찾는 기준이다.
- `poseDetected`: frame 전체를 triangulation 후보로 쓸 수 있는지 판단한다.
- `landmarks[].x`, `landmarks[].y`: MediaPipe normalized image coordinate로 본다.
- `landmarks[].z`: 첫 재설계 검토에서는 metric depth로 쓰지 않는다. 필요한 경우 진단 값으로만 남긴다.
- `landmarks[].visibility`, `landmarks[].presence`: 관절별 신뢰도와 실패 판정의 입력이다.

### 검토 원칙
- 2D output은 "사람의 3D 위치"가 아니라 "각 카메라 이미지 평면에서 감지된 관절 관측값"이다.
- 단일 카메라 2D 관측값의 역투영 결과는 3D point가 아니라 camera ray이며, depth는 두 시점 이상의 관측선을 대조해야 결정된다.
- 2D 관측값을 3D로 올리기 전에는 반드시 camera model과 같은 해상도 기준의 pixel 좌표로 변환해야 한다.
- 2D artifact와 camera model의 binding이 없으면, 해당 관측값을 절대좌표로 환산할 근거가 없으므로 triangulation 입력으로 쓰면 안 된다.
- request에서 별도로 받은 camera id는 2D artifact의 binding을 대체하는 값이 아니라 검증해야 하는 값이다.
- 영상 resize, crop, letterbox, 회전 metadata가 있으면 `x * width`, `y * height`만으로는 틀릴 수 있다. 이 경우 preprocessing transform을 output artifact에 남겨야 한다.
- left/right 관절이 특정 시점에서 뒤집히는지 확인해야 한다. 특히 측면 영상에서는 팔/다리 occlusion 때문에 MediaPipe가 좌우를 바꿀 수 있다.

## 시점 및 위치 정렬

### 카메라 binding
두 source job은 아래 내용을 한 묶음으로 추적해야 한다.

```json
{
  "slot": "A",
  "sourceJobId": "job_ad691fa7",
  "sourceVideoName": "hd_00_01_gt.mp4",
  "artifactCameraId": "00_01",
  "requestCameraId": "00_01",
  "calibrationRef": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
  "calibrationCameraId": "00_01",
  "bindingSource": "user_selected"
}
```

검토 기준:
- source video name에서 추론한 camera id, 2D artifact의 camera id, request의 camera id가 일치해야 한다.
- `cameraIdA`와 `cameraIdB`가 서로 달라야 한다.
- calibration file 안에 두 camera id가 모두 있어야 한다.
- calibration camera의 `resolution`과 2D artifact의 `imageCoordinateSpace.pixelBasis` 또는 `videoInfo.width/height`가 일치해야 한다. 다르면 preprocessing transform이 있어야 한다.
- 같은 source job을 두 slot에 중복으로 넣으면 실패해야 한다.
- 2D artifact에 camera binding이 없으면 일반 legacy fallback으로 filename 추론을 시도할 수 있지만, debug summary에 `bindingSource="filename_inferred"`를 명시해야 한다. `171204_pose1` fixed fixture path에서는 이 fallback을 허용하지 않는다.
- 2D artifact의 binding과 request camera id가 다르면 synthesis를 중단한다. 이 경우 `camera_binding_mismatch` 실패 사유를 반환한다.

### 시간 정렬
- GT-aligned fixture에서는 `frameIndex`와 media-local `timestampMs`가 거의 같은 의미를 가진다.
- 실제 업로드 영상에서는 두 영상 시작점이 다를 수 있으므로, media-local timestamp만으로 정합하면 틀릴 수 있다.
- 재설계 검토 중에는 각 paired frame마다 아래 값을 남긴다.

```json
{
  "pairIndex": 0,
  "A": { "frameIndex": 118, "timestampMs": 3937.27 },
  "B": { "frameIndex": 118, "timestampMs": 3937.27 },
  "timestampDeltaMs": 0.0,
  "frameIndexDelta": 0
}
```

### 좌표계와 기준점
- camera coordinate, Panoptic world coordinate, body-local coordinate, Three.js view coordinate를 섞지 않는다.
- backend `skeleton3d.v1`는 우선 world coordinate cm만 저장한다.
- 화면 표시용 골반 중심 정렬, 발바닥 floor 정렬, scale normalization은 viewer transform으로 분리한다.
- 최종 제품 기준점은 별도 결정해야 한다. 후보는 world origin, mid-hip, left/right foot floor, rack 기준점이다.

## 두 개를 대조하는 방법

### triangulation 전 대조
- 같은 관절이 양쪽 frame에 존재하는지 확인한다.
- 양쪽 visibility/presence가 threshold 이상인지 확인한다.
- 각 관절의 pixel 좌표가 카메라별 이미지 bounds 안에 있는지 확인한다.
- epipolar line distance를 계산해 두 관측값이 같은 3D point에서 온 것인지 사전 점검한다.
- 좌우 관절 swap 의심 조건을 둔다. 예를 들어 `left_wrist`보다 `right_wrist`가 epipolar residual이 훨씬 낮으면 진단 플래그를 남긴다.

### triangulation 후 대조
- 3D point를 양쪽 카메라로 다시 project한다.
- 각 카메라에서 observed pixel과 reprojected pixel의 차이를 px 단위로 기록한다.
- frame별 평균만 보지 말고 관절별 residual을 함께 본다.
- GT가 있는 fixture에서는 reprojection error와 MPJPE를 분리해서 본다. reprojection error가 낮아도 잘못된 3D 위치일 수 있고, MPJPE가 낮아도 특정 관절의 2D 대응이 나쁠 수 있다.

### 진단 표 초안
| frameIndex | joint | A visibility | B visibility | epipolarPx | reprojectionApx | reprojectionBpx | success | failureReason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 118 | left_wrist | 0.91 | 0.88 | 1.4 | 1.2 | 1.6 | true | 없음 |

## 3D 합성 삼각측량 방법

### 기하/벡터 구현 계약
이 문서의 목적은 구현을 바로 바꾸기 전에 잘못된 가정을 분리하는 것이다. 따라서 아래 계약은 재설계 검토 중 임시 기준선으로 고정하고, 실제 코드가 다르게 동작하면 debug artifact에 차이를 드러내야 한다.

| 좌표계 | 의미 | 원점/축 | 단위 | 사용 범위 |
| --- | --- | --- | --- | --- |
| `image_normalized` | MediaPipe `landmarks[].x/y` | 좌상단 origin, `x` 오른쪽, `y` 아래, `[0, 1]` 기준 | normalized | raw 2D artifact |
| `image_pixel` | source image plane의 pixel 좌표 | 좌상단 origin, `u` 오른쪽, `v` 아래 | px | bounds check, reprojection 비교 |
| `camera_normalized` | distortion 제거 후 normalized camera plane | optical axis 앞쪽이 positive depth인 camera convention | unitless | triangulation 입력 |
| `camera_3d` | 각 카메라 로컬 3D 좌표 | `X_c = R X_w + t`로 정의 | world와 동일 | cheirality/depth 판정 |
| `rack_session_world.v1` | 제품/session 기준 3D world | session manifest의 `origin`, `upAxis`, `forwardAxis`가 source of truth | cm 또는 m | backend 합성 결과 |
| `viewer_world` | Three.js/Unreal 표시 좌표 | viewer별 up-axis와 handedness를 `toViewTransform`에 명시 | 표시 단위 | frontend 표시 전용 |

외부 파라미터는 우선 **world-to-camera** convention으로 고정한다.

```text
X_w = [X, Y, Z]^T in rack_session_world.v1
X_c = R X_w + t
x_px ~ K [R | t] [X_w, 1]^T
C_w = -R^T t
```

`R/t`가 camera-to-world 형식으로 들어오는 calibration 또는 manifest를 쓰는 경우, 합성 전에 반드시 world-to-camera `R/t`로 변환하고 `extrinsicsConvention`을 debug artifact에 남긴다. 이 convention이 불명확하면 triangulation을 실행하지 않는다.

### Projection Matrix Convention
재설계 기준선은 **undistorted normalized 좌표 + normalized projection matrix** 방식이다.

1. `image_normalized`에서 `image_pixel`로 변환한다.
   - `u = x * pixelBasis.width`
   - `v = y * pixelBasis.height`
2. `K`, `distCoef`로 `(u, v)`를 OpenCV undistort equivalent의 `camera_normalized` 좌표 `(x_n, y_n)`로 변환한다.
3. triangulation에는 `P_norm = [R | t]`를 사용한다.
4. reprojection debug에는 `X_w -> X_c -> x_n -> K/distCoef -> image_pixel` 경로를 사용해 observed pixel과 비교한다.

pixel 좌표와 full projection matrix `P_px = K [R | t]`를 쓰는 구현도 비교 fixture로 둘 수 있지만, MVP 재검토 기준선은 위 normalized 방식을 우선한다. 둘을 비교할 때는 distortion 보정 적용 여부를 분리해서 기록해야 한다.

### 2D Observation to World Ray
단일 카메라의 2D 관측값은 3D point가 아니라 ray다. 한 관절에 대한 trace는 아래 값을 모두 남긴다.

```text
landmark normalized:
  x=0.5123, y=0.4312

pixel:
  u=983.62, v=465.70

undistorted normalized:
  x_n=0.1031, y_n=-0.0418

camera ray:
  r_c = normalize([x_n, y_n, 1])

world ray:
  C_w = -R^T t
  r_w = R^T r_c
  ray(lambda) = C_w + lambda * r_w
```

이 trace가 실제 camera orientation과 맞지 않으면 triangulation 결과를 보기 전에 `R/t`, axis, calibration 해석을 먼저 수정한다.

### 기준선
첫 재검토 기준선은 calibrated two-view DLT triangulation이다.

1. MediaPipe normalized 좌표를 source image pixel 좌표로 변환한다.
2. `K`, `distCoef`로 pixel 좌표를 undistorted normalized camera coordinate로 변환한다.
3. 각 카메라의 normalized projection matrix를 준비한다.
4. 두 관측점으로 homogeneous 3D point를 구한다.
5. homogeneous `w`가 0에 가깝거나, 카메라 앞쪽 조건을 만족하지 않으면 실패 처리한다.
6. 3D point를 양쪽 카메라에 재투영한다.
7. reprojection error, visibility, presence, epipolar residual을 함께 보고 성공 여부를 판단한다.

### DLT 수식 계약
두 관측값은 `camera_normalized` 좌표로 둔다.

```text
x1 = [u1, v1, 1]^T
x2 = [u2, v2, 1]^T
P1 = [R1 | t1]
P2 = [R2 | t2]

A =
  u1 * P1[2,:] - P1[0,:]
  v1 * P1[2,:] - P1[1,:]
  u2 * P2[2,:] - P2[0,:]
  v2 * P2[2,:] - P2[1,:]

Solve A X_h = 0 by SVD.
X_h = last row of Vt.
X_w = X_h[0:3] / X_h[3].
```

`X_h[3]`가 0에 가깝거나 NaN/Inf가 생기면 실패 처리한다. 성공 후보라도 각 카메라에서 `Z_c > 0` cheirality 조건을 만족하지 않으면 renderable position으로 쓰지 않는다.

### 검증 threshold 초안
초기 threshold는 fixture 분포를 보기 위한 기준선이다. 값은 debug report의 p50/p95/p99를 보고 조정한다.

| 항목 | 초기 기준 | 실패 또는 경고 처리 |
| --- | --- | --- |
| `visibility` / `presence` | 둘 중 하나라도 `< 0.5`면 후보 제외 | `low_visibility` |
| image bounds | `0 <= u < width`, `0 <= v < height` | `out_of_bounds` |
| homogeneous `w` | `abs(w) < 1e-8`면 실패 | `degenerate_homogeneous_point` |
| cheirality | 두 카메라 모두 `Z_c > 0` | `behind_camera` |
| reprojection error | `<= 5px` 통과, `5-15px` 경고, `> 15px` 실패 후보 | `high_reprojection_error` |
| epipolar/Sampson distance | fixture p95를 기준으로 확정 | `epipolar_mismatch` |

좌우 swap 진단은 실패 판정과 분리한다. 예를 들어 같은 frame에서 `left_wrist`보다 `right_wrist`가 left observation의 epipolar residual을 현저히 낮추면 `swap_suspicion=true`로 남기되, 자동 교체는 후속 결정으로 둔다.

### 반드시 분리할 것
- triangulation 계산 좌표계와 viewer 표시 좌표계
- world 좌표와 body-local 좌표
- lens distortion 보정과 pose inference noise 보정
- GT 기반 3D 정확도와 reprojection 기반 2D 일관성
- 실패 관절의 진단용 후보 좌표와 실제 renderable position

### 검증 fixture
- GT 3D point를 calibration으로 양쪽 카메라에 project한다.
- project된 2D point를 다시 triangulation한다.
- 복원된 3D point가 원래 GT point와 cm 단위로 얼마나 차이 나는지 본다.
- 이 round trip이 맞지 않으면 실제 MediaPipe output을 보기 전에 camera model 또는 projection matrix 해석부터 수정한다.

## 렌더링 경계
- Three.js는 Y-up 좌표계를 사용한다.
- backend world coordinate의 up axis가 무엇인지 metadata로 명시해야 한다.
- viewer는 world 좌표를 직접 수정하지 않고 `toViewTransform` 단계에서만 중심 이동, scale, floor 배치를 수행한다.
- backend가 `rack_session_world.v1`에서 `Z-up`, `Y-forward`를 쓰고 Three.js가 `Y-up` 표시를 요구하면 축 재배치는 `toViewTransform`으로만 수행한다. 예시 mapping은 `viewer.x = world.x`, `viewer.y = world.z`, `viewer.z = -world.y`이며, 실제 제품 mapping은 session manifest의 axis metadata와 함께 기록한다.
- 누워 보임 진단은 아래 세 값을 동시에 확인해야 한다.
  - backend world 좌표의 `nose`, `mid_hip`, `ankle` 축 방향
  - viewer 변환 후 같은 관절의 Y 좌표 순서
  - camera preset이 바라보는 방향과 OrbitControls target

## 필요한 Debug Artifact
- `synthesis_pair_manifest_debug.v1`: source job, source video, artifact camera id, request camera id, calibration camera id, calibration ref, binding source, mismatch 여부
- `frame_alignment_debug.v1`: paired frame list, timestamp delta, frameIndex delta
- `observation_trace_debug.v1`: raw normalized landmark, pixel coordinate, camera id, `K/distCoef` hash 또는 요약, undistorted normalized coordinate, camera center `C_w`, world ray direction `r_w`, visibility/presence
- `cross_view_validation_debug.v1`: epipolar residual 또는 Sampson distance, swap suspicion, missing/low-quality joints, image bounds result
- `triangulation_trace_debug.v1`: `projectionConvention`, `extrinsicsConvention`, `P1/P2` 요약, homogeneous `X_h`, final `X_world`, camera depths `Zc1/Zc2`, reprojected pixel A/B, reprojection error A/B, cheirality, failure reason
- `viewer_transform_debug.v1`: world coordinate, `toViewTransform` matrix 또는 axis mapping, Three.js view coordinate, floor/reference metadata 비교

## 다음 작업 후보
1. 2D skeleton artifact에 `cameraBinding`과 `imageCoordinateSpace` metadata를 추가하는 schema/code 변경안을 만든다.
2. synthesis request의 `cameraIdA/B`와 2D artifact binding이 불일치할 때 `camera_binding_mismatch`로 실패시키는 검증을 추가한다.
3. 실제 A/B artifact와 synthesis request를 기준으로 `synthesis_pair_manifest_debug.v1` 초안을 만든다.
4. 한 frame, 핵심 관절 6개(nose, shoulders, hips, ankles)에 대한 observation trace를 뽑는다.
5. GT projection round trip fixture로 camera model과 triangulation direction을 먼저 검증한다.
6. backend world 좌표와 frontend view 좌표를 한 화면에서 비교하는 임시 debug overlay를 만든다.
7. 검토 결과에 따라 `3d-skeleton-synthesizer-plan.md`, `triangulation-implementation-plan.md`, `3d-skeleton-rendering-plan.md`, `gt-evaluation-plan.md`를 갱신한다.

## 보류
- 3개 이상 카메라 일반화
- learned pose correction
- temporal smoothing을 통한 실패 관절 보간
- 실제 랙 기준점 자동 인식
- 실시간 카메라 하드웨어 sync 설계

## Decision: Session World Separation

`panoptic_world_cm`은 검증 fixture 전용 좌표계로 취급한다. 이 값은 현재 테스트 자산이 사용하는 CMU Panoptic 데이터셋 world를 설명할 뿐이며, 제품 런타임의 기준 공간이 아니다. 제품 파이프라인은 별도의 세션 단위 3D world를 가져야 하며, 임시 명칭은 `rack_session_world.v1`로 둔다. 모든 합성 job은 대상 world를 명시해야 한다.

### Coordinate System Boundaries

- `panoptic_world_cm`: dataset 및 GT evaluation fixture 전용.
- `rack_session_world.v1`: 실제 또는 시뮬레이션 랙 환경을 위한 product/session runtime world.
- camera-local coordinate system: projection, undistortion, triangulation에 쓰는 각 카메라 내부 geometry.
- viewer coordinate system: frontend, Three.js, Unreal 표시용 좌표계. source-of-truth 합성 공간이 아니라 view transform으로 다룬다.

Backend는 `panoptic_world_cm`을 제품 좌표계로 가정하면 안 된다. Panoptic 데이터를 검증에 사용할 때는 output을 fixture 평가용 `panoptic_world_cm`에 남기거나, 명시적인 `panoptic_world_cm -> rack_session_world.v1` transform을 적용하고 기록해야 한다.

### Rack Session World Contract

Product/session world는 다음을 정의해야 한다.

- `coordinateSystem`: 예: `rack_session_world.v1`
- `unit`: `cm` 또는 `m`; calibration, synthesis, analysis 전체에서 고정
- `origin`: 예: `rack_center_floor`
- `upAxis`: 예: `z`
- `forwardAxis`: 예: `y`
- 선택적 physical anchors: rack center, rack uprights, platform/floor plane, barbell reference, capture volume bounds

정확한 origin과 axis는 제품 결정사항이지만, 실제 multi-camera synthesis를 신뢰하려면 먼저 명시되어야 한다.

### Camera Placement Rule

각 source video는 session world 안에 배치된 camera와 binding되어야 한다. Camera는 단순한 영상 파일 label이 아니며 다음 정보를 가져야 한다.

- `cameraId`
- `sessionId`
- image resolution
- intrinsics 및 distortion reference
- session world 기준 extrinsics: `R/t`, `position + rotation`, 또는 문서화된 동등 표현
- 2D artifact, source stream/video, request camera id, calibration camera id를 연결하는 binding metadata

Triangulation 결과는 camera extrinsics가 정의한 world coordinate system으로 나온다. 따라서 production camera extrinsics는 Panoptic fixture space가 아니라 `rack_session_world.v1` 기준이어야 한다.

### MVP Hardware Profile: Mirrored Front Oblique

MVP2의 제품 기준 3D 합성은 "아무 두 영상"을 입력받는 구조가 아니라, 같은 rack session world에 고정 배치된 두 카메라를 전제로 한다. 첫 하드웨어 프로파일은 `mirrored_front_oblique.v1`로 둔다.

- 두 카메라는 모두 파워랙 전면 쪽 바깥에 둔다.
- 좌/우 대각 시점으로 배치하고, 시선은 랙 중앙에서 교차시킨다.
- 두 카메라 높이는 비슷하게 맞춘다.
- 카메라 target은 대략 `rack_center`의 mid-hip ~ chest 높이로 둔다.
- pitch는 약간 하향으로 둔다.
- 전신, 바벨 양끝, 바닥 접지점이 두 카메라 모두의 frame 안에 들어와야 한다.

초기 권장값:

```text
hardwareProfile: mirrored_front_oblique.v1
camera_left:
  placement: front-left outside rack
  yawFromFront: -35deg to -45deg
  height: 1.4m to 1.8m
  pitch: downward 5deg to 15deg
  target: rack_center_mid_hip_to_chest
camera_right:
  placement: front-right outside rack
  yawFromFront: +35deg to +45deg
  height: same as camera_left
  pitch: downward 5deg to 15deg
  target: rack_center_mid_hip_to_chest
```

후면 카메라는 불필요하다는 뜻이 아니라, 두 대만 쓰는 MVP 범위에서는 기본값으로 쓰지 않는다. 후면 대각 카메라는 등 각도, hip hinge, bar path occlusion 보완에는 유리할 수 있으므로 `front_rear_diagonal.v1` 같은 대안 hardware profile로 남긴다. 단, 이 대안은 2D landmark 좌우 대응, 후면 시점 pose 안정성, 설치 공간 및 안전성을 별도로 검증한 뒤 선택한다.

### Panoptic Fixture Camera Rig

CMU Panoptic fixture는 제품 하드웨어 공간이 아니다. Panoptic의 `00_00` ~ `00_30` HD camera id는 semantic placement label이 아니며, 공식 문서 기준으로 camera index 순서는 위치와 무관하다. 따라서 "전면 좌/우 대각"에 대응하는 Panoptic pair는 camera id 숫자 순서가 아니라 각 sequence calibration의 `R/t`로 계산한 camera center, viewing geometry, 실제 영상 검토를 기준으로 고른다.

`171204_pose1` 실험환경에서는 두 업로드 영상의 파일명이나 사용자 입력에서 카메라를 매번 추론하지 않는다. 실험 fixture rig를 다음 두 고정 위치로 확정한다.

- `front_left`: Panoptic HD camera `00_21`
- `front_right`: Panoptic HD camera `00_11`

Pipeline contract:

- source video A/B는 이 fixed fixture rig의 `front_left`/`front_right` slot에 명시적으로 바인딩한다.
- calibration은 항상 `171204_pose1/171204_pose1/calibration_171204_pose1.json`에서 `name == "00_21"` 및 `name == "00_11"` 항목의 `K`, `distCoef`, `R`, `t`를 사용한다.
- upload filename 기반 camera inference, arbitrary pair selection, per-upload calibration lookup은 이 Panoptic fixed fixture path에서 사용하지 않는다.
- request 또는 artifact metadata에 다른 camera id가 들어오면 fixed fixture contract 위반으로 취급한다.

Panoptic 공식 calibration convention:

```text
x = K * (R * X + t)
camera_center_world = -R^T * t
world unit = cm
```

참조: <https://domedb.perception.cs.cmu.edu/develop/tools.html>

`171204_pose1` fixture에서 Panoptic HD camera id는 전면/후면 의미를 직접 제공하지 않는다. 따라서 Panoptic world의 고정 축만으로 전면을 정하지 않고, 실제 영상 검토와 GT 3D 관절의 얼굴 방향 추정을 함께 사용했다.

`hd_00_21`은 실제 영상 검토에서 활동자 전면 좌상단 시점으로 확인되었다. 기존 후보였던 `hd_00_18`은 calibration상 `00_21`의 dome 좌우 대칭에 가깝지만, 실제 영상에서는 활동자의 후면 시점으로 확인되어 `mirrored_front_oblique.v1` 기본 pair에서 제외한다.

`00_21`의 전면 좌상단 anchor에 대응하는 고정 우상단 카메라는 `00_11`로 확정한다. `00_11`은 GT 기반 활동자 전면축 추정에서 전면 반공간에 있고, `00_21`과 비슷한 높이의 반대쪽 시점으로 분류된다.

```text
fixedPanopticFixtureRig: "171204_pose1.front_oblique_00_21_00_11.v1"
fixedPanopticPair: ["00_21", "00_11"]
calibrationRef: "171204_pose1/171204_pose1/calibration_171204_pose1.json"

00_21:
  rigSlot: front_left
  cameraCenterCm: [-241.5, -239.6, 75.4]
  visualCheck: front-left-high
  estimatedSubjectFrontScore: 176.3
  estimatedSubjectSideScore: -118.0

00_11:
  rigSlot: front_right
  cameraCenterCm: [-143.0, -239.7, -205.7]
  visualCheck: fixed fixture right-side view
  estimatedSubjectFrontScore: 153.0
  estimatedSubjectSideScore: 178.9

rejectedForFrontObliqueDefault:
  00_18:
    cameraCenterCm: [240.1, -238.9, 87.1]
    reason: visual review shows rear view of the active subject
```

이 pair는 `171204_pose1` Panoptic 실험 fixture의 fixed rig다. 이후 #29 실험에서 업로드되는 두 영상은 이 fixed rig의 `00_21`/`00_11` 카메라로 촬영된 것으로 취급하고, pipeline은 해당 고정 calibration을 사용한다. 다른 camera pair를 실험하려면 별도 fixture rig id와 management note를 추가해야 한다.

현재 로컬 subset에서 사용한 `00_01 + 00_02`는 다운로드된 제한 영상으로 실험 가능한 fallback pair일 뿐이다. 이 pair는 한쪽이 우전면, 다른 한쪽이 거의 전면 중앙/상단에 가까우므로 `mirrored_front_oblique.v1`의 기준 pair로 취급하지 않는다.

```text
fallbackLocalSubsetPair: ["00_01", "00_02"]
purpose: local subset experiment only
```

### Session Scene Manifest Draft

```json
{
  "schemaVersion": "session_scene_manifest.v1",
  "sessionId": "rack-session-001",
  "sessionWorld": {
    "coordinateSystem": "rack_session_world.v1",
    "unit": "cm",
    "origin": "rack_center_floor",
    "upAxis": "z",
    "forwardAxis": "y"
  },
  "cameras": [
    {
      "cameraId": "front_left",
      "sessionId": "rack-session-001",
      "imageWidth": 1920,
      "imageHeight": 1080,
      "intrinsicsRef": "calibration/intrinsics/front_left.json",
      "distortionRef": "calibration/intrinsics/front_left.json",
      "extrinsics": {
        "coordinateSystem": "rack_session_world.v1",
        "position": [-120.0, 80.0, 160.0],
        "rotation": {
          "type": "matrix_3x3",
          "value": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
          ]
        }
      }
    },
    {
      "cameraId": "front_right",
      "sessionId": "rack-session-001",
      "imageWidth": 1920,
      "imageHeight": 1080,
      "intrinsicsRef": "calibration/intrinsics/front_right.json",
      "distortionRef": "calibration/intrinsics/front_right.json",
      "extrinsics": {
        "coordinateSystem": "rack_session_world.v1",
        "position": [120.0, 80.0, 160.0],
        "rotation": {
          "type": "matrix_3x3",
          "value": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
          ]
        }
      }
    }
  ],
  "worldTransforms": [
    {
      "from": "panoptic_world_cm",
      "to": "rack_session_world.v1",
      "status": "fixture_only_optional",
      "transform": null
    }
  ]
}
```

### Required Schema Direction

- `outputCoordinateSystem`을 일반화한다. `panoptic_world_cm` literal에 고정하면 안 된다.
- `calibrationRef`를 교체하거나 확장해 dataset calibration file뿐 아니라 session scene/camera rig manifest를 참조할 수 있게 한다. 단, `171204_pose1` fixed fixture path에서는 `calibration_171204_pose1.json`의 `00_21`/`00_11` camera model을 고정 사용한다.
- 2D skeleton artifact의 camera binding이 request camera id 및 session manifest camera id와 일치하는지 검증한다. 단, fixed fixture path에서는 request camera id를 업로드 파일에서 추론하지 않고 rig slot이 `00_21`/`00_11`로 고정되어야 한다.
- `panoptic_world_cm` 지원은 fixture evaluation과 regression test 용도로만 유지한다.
- Display transform은 synthesis coordinate와 분리한다. Frontend, Three.js, Unreal은 viewing을 위해 `rack_session_world.v1`을 변환할 수 있지만 backend world coordinate를 조용히 재해석하면 안 된다.

### Implementation Consequence

MVP2 3D pipeline은 "dual video parallel processing plus triangulation"이 아니라 "session-world camera rig synthesis"로 재정의한다. 올바른 처리 순서는 다음과 같다.

1. Load the session scene manifest.
2. Bind each stream/video artifact to a camera in that session.
3. Convert 2D landmarks into camera observations using the matching camera model.
4. Triangulate into the session world defined by the camera extrinsics.
5. Emit `skeleton3d` results with the session coordinate system and quality diagnostics.
6. Apply optional viewer transforms only after the backend result is complete.

### Fixed Fixture Input

- `171204_pose1` fixed fixture input은 `hd_00_21_2min.mp4`와 `hd_00_11_2min.mp4`다.
- 두 영상으로 2D skeleton artifact를 다시 생성한 뒤, `fixedPanopticFixtureRig="171204_pose1.front_oblique_00_21_00_11.v1"` 기준으로 synthesis fixture를 재검증한다.
- 이 fixed fixture에서 `front_left`는 `00_21`, `front_right`는 `00_11`이다.
- Pipeline은 업로드된 두 영상의 카메라를 그때그때 확인하거나 추론하지 않고, 위 고정 rig slot과 calibration camera id를 사용한다.
- `hd_00_18`은 후면 시점으로 확인되었으므로 `mirrored_front_oblique.v1` 기본 pair에서는 제외하고, 필요할 경우 `front_rear_diagonal.v1` 같은 대안 profile 검토용으로만 사용한다.
- `00_01 + 00_02` 결과는 fallback subset baseline으로 보존하되, 제품 하드웨어 프로파일 검증 결과로 해석하지 않는다.
