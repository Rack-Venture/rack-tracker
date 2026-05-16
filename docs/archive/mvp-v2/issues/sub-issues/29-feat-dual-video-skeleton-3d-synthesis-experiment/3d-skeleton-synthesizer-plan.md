# [design] 듀얼 2D 스켈레톤 기반 3D 합성기 계획
Parent: #29

## 문서 관계
- 이 문서는 `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`의 하위 설계 문서다.
- 목적은 두 카메라에서 나온 2D 스켈레톤 결과를 백엔드 파이프라인 안에서 3D 스켈레톤 결과로 합성하기 위한 계약, 구현 청사진, 평가 기준을 정리하는 것이다.
- 커밋 단위 작업 이력과 진행 로그는 부모 관리 문서에 기록하고, 이 문서에는 설계 판단과 구현 기준만 남긴다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## 관련 하위 계획 문서
- [triangulation 구현 계획](triangulation-implementation-plan.md)
- [Three.js 3D 스켈레톤 렌더링 계획](3d-skeleton-rendering-plan.md)
- [3D 합성 API 및 분석 파이프라인 리팩토링 계획](3d-synthesis-api-analysis-pipeline-plan.md)
- [GT 평가 계획](gt-evaluation-plan.md)

## 현재 결론
- 이 합성기는 독립 제품이나 독립 파일 변환기가 아니라, 백엔드 dual-video 파이프라인의 한 stage로 구현한다.
- 다만 구현과 검증을 쉽게 하기 위해 같은 서비스 로직을 호출하는 개발용 CLI/script는 둘 수 있다.
- 제품 입력 방식은 두 카메라 영상을 한 번에 받아 Video A/B 업로드 슬롯으로 묶는 구조로 확정한다.
- manifest shape, 출력 JSON shape, triangulation 절차, GT 평가 지표, 분석 adapter 경계는 구현자가 이 문서 기준으로 정한다.
- 첫 구현은 `171204_pose1` Panoptic Studio 가공 데이터셋, `00_00 + 00_01` 카메라 쌍, GT-aligned clip 조건으로 좁게 시작한다.

## 설계 원칙
- 기존 2D skeleton JSON 포맷을 즉시 바꾸지 않는다.
- 3D 합성 stage는 두 2D job 산출물과 camera binding을 입력으로 받는다.
- Video A 업로드 슬롯은 `sourceJobIdA`와 `cameraIdA`, Video B 업로드 슬롯은 `sourceJobIdB`와 `cameraIdB`로 고정 매핑한다.
- DB가 아직 없으므로 첫 구현은 `job_id`와 파일 기반 artifact repository를 사용한다.
- 나중에 DB나 object storage가 생기면 artifact repository 구현만 교체한다.
- 카메라 캘리브레이션 자동화는 하지 않는다. 이미 주어진 캘리브레이션 정보는 카메라 기하 계층이 런타임 모델로 변환하고, 합성기는 그 결과를 조회해 사용한다.
- frame matching은 timestamp를 1차 기준으로 쓰고, frameIndex는 추적과 sanity check 용도로 남긴다.
- MediaPipe `z`와 `world_landmarks`는 첫 triangulation 계산에 섞지 않는다.

## Implementation Status & Decision Matrix
이 표는 구현 계획 검토용 상태판이다. 행은 작업 항목, 아키텍처 레이어, 구현 단계, 또는 결정 포인트를 나타낸다. `상태`는 아래 값 중 하나만 쓴다.

상태값:
- `결정 완료`: 방향이 확정됐고 추가 판단이 필요 없다.
- `결정 필요`: 구현 전에 사용자나 구현자가 방향을 확정해야 한다.
- `구현 필요`: 방향은 충분히 정해졌고 아직 코드나 문서 구현이 남아 있다.
- `구현 중`: 현재 작업 중이며 아직 완료 기준을 만족하지 않는다.
- `구현 완료`: 구현은 끝났지만 검증이 별도로 남아 있을 수 있다.
- `검증 필요`: 구현 결과를 테스트, 런타임 실행, 데이터 비교, 또는 리뷰로 확인해야 한다.
- `검증 완료`: 정의한 검증 기준을 통과했다.
- `보류`: 지금 범위에서 의도적으로 미뤘다.
- `차단됨`: 외부 의존성, 미결정, 데이터, 권한, 환경 문제로 진행할 수 없다.

운영 규칙:
- `상태`에는 복합 값을 쓰지 않는다. 예를 들어 방향은 정해졌지만 구현이 남았다면 `구현 필요`로 두고, 확정된 방향은 `결정된 방향`에 적는다.
- `결정 필요 사항`은 빈칸 대신 `없음`을 명시해 미검토와 구분한다.
- `다음 액션`은 바로 실행 가능한 한 단계로 쓴다.
- `참조`에는 세부 섹션, 관련 파일, 테스트, 또는 후속 계획 문서를 연결한다.

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SYN-01 | 제품 입력 방식 | UX/API 계약 | 결정 완료 | 두 카메라 영상을 한 번에 받고 Video A/B 업로드 슬롯을 각각 A/B job과 camera binding에 고정 매핑한다. | 없음 | 입력 계약 구현 시 이 매핑을 API request shape와 job metadata에 반영한다. | 입력 계약 |
| SYN-02 | pair manifest / `SynthesisInput` | schema | 구현 완료 | API request는 `pairManifest`를 source of truth로 받고, service 내부에서는 같은 내용을 정규화한 `SynthesisInput`으로 넘긴다. manifest는 `sourceJobIdA/B`, `cameraIdA/B`, `calibrationRef`, `sync`, `landmarkSet`, `outputCoordinateSystem`을 가진다. | 없음 | schema 변경 시 controller/frontend request contract를 함께 갱신한다. | 입력 계약 |
| SYN-03 | artifact 저장 | repository | 구현 완료 | 첫 버전은 `backend/tmp` 하위 job artifact와 메모리 상태를 읽는 `SkeletonArtifactRepository`를 둔다. DB나 object storage는 나중에 repository 구현만 교체한다. | 없음 | artifact path/summary 필드가 바뀌면 synthesis result와 viewer adapter를 함께 갱신한다. | 입력 계약 |
| SYN-04 | 카메라 기하 모델 | calibration | 구현 완료 | Panoptic calibration JSON의 `00_00`, `00_01` 카메라 항목을 읽어 `CameraModel`로 제공한다. | projection matrix 해석이 Panoptic world cm 좌표계와 일치하는지 추가 fixture 검증이 남아 있다. | GT fixture 기준 reprojection/좌표계 검증을 보강한다. | 카메라 기하 모델 계약 |
| SYN-05 | 2D 관측점 좌표계 | observation | 구현 완료 | `LandmarkObservationBuilder`가 normalized/pixel 좌표와 `distortionState`를 기록하고, 필요 시 보정 좌표를 만든다. | `distorted_pixel` 기본 계약의 수치 검증은 추가 여지가 있다. | 실제 artifact fixture로 observation contract를 재검토한다. | 2D 관측점 좌표계와 왜곡 상태 |
| SYN-06 | 프레임 정합 | alignment | 구현 완료 | 첫 구현은 timestamp-first aligner로 간다. `frameIndex`는 GT-aligned 실험 데이터의 sanity check와 디버깅 정보로만 쓴다. | 실제 업로드 영상의 timestamp domain은 후속 실제 카메라 단계에서 다시 결정한다. | 실제 업로드 케이스가 생기면 sync 정책을 별도 이슈로 분리한다. | 프레임 정합 기준 |
| SYN-07 | 2D 좌표 변환 | observation | 구현 완료 | MediaPipe normalized 좌표를 이미지 픽셀 좌표로 변환하려면 `videoInfo.width/height`가 필요하다. | width/height 누락 artifact에 대한 보강 정책은 추가 결정 여지가 있다. | 누락 artifact를 허용할지 실패시킬지 운영 규칙만 보강한다. | 2D 좌표 변환 |
| SYN-08 | triangulation | geometry service | 구현 완료 | `CameraModel`과 준비된 2D 관측점을 입력으로 DLT triangulation, reprojection error, joint quality mask를 계산하는 서비스로 분리한다. | 초기 `maxReprojectionErrorPx=8.0`의 적정성은 추가 검증이 남아 있다. | 실데이터 분포를 보고 threshold tuning 메모를 남긴다. | triangulation 청사진 |
| SYN-09 | 3D 출력 스키마 | output schema | 구현 완료 | 기존 2D skeleton JSON을 확장하지 않고 별도 `skeleton3d.v1` JSON으로 저장한다. | 없음 | schema 변경 시 rendering/API/evaluation 문서를 함께 갱신한다. | 3D 출력 스키마 청사진 |
| SYN-10 | GT 평가 | evaluation | 구현 완료 | MediaPipe 33 -> COCO-19 direct subset mapping으로 raw MPJPE와 reprojection summary를 먼저 계산하고, 좌표계 보정 metric은 별도로 분리한다. | derived joint와 rigid alignment metric은 첫 raw metric 후 필요성을 판단한다. | aligned metric 필요 여부를 결과 기반으로 판단한다. | GT 평가 청사진 |
| SYN-11 | 실행 진입점 | orchestration/API | 구현 완료 | 백엔드 stage가 정식 진입점이고, CLI/script는 같은 서비스를 호출하는 개발용 smoke test로 둔다. | pytest 미설치 환경에서 자동 검증 범위가 제한돼 있다. | 런타임/fixture 검증 기준을 별도 정리한다. | 실행 진입점 청사진 |
| SYN-12 | 분석 연결 | analysis adapter | 보류 | 3D 결과를 바로 기존 2D 분석에 섞지 않고 별도 3D feature namespace와 mask를 만드는 adapter는 후속 범위로 둔다. | 없음 | batch synthesis와 viewer 검증 후 별도 work item으로 분리한다. | 분석 연결 청사진 |
| SYN-13 | 실제 카메라 캘리브레이션 자동화 | future scope | 보류 | 첫 구현에서는 Panoptic dataset calibration을 수동 참조한다. | 없음 | MVP 합성기 검증 후 별도 이슈로 분리한다. | 명시적으로 미루는 것 |
| SYN-14 | 실시간 streaming synthesis SSE | future scope | 보류 | 첫 구현에서는 저장된 job artifact 기반 stage와 smoke CLI를 우선한다. | 없음 | batch synthesis가 검증된 뒤 streaming 연결 여부를 결정한다. | 명시적으로 미루는 것 |

## 입력 계약

### 백엔드 stage 입력
첫 구현의 정식 입력은 파일 경로가 아니라 job artifact 참조다.
제품에서는 두 카메라 입력을 한 번에 받고, 업로드 슬롯을 camera binding에 고정 매핑한다.
API 계층에서는 이 입력을 `pairManifest` wrapper로 받고, 합성 service는 validation 후 같은 내용을 내부 `SynthesisInput`으로 정규화해 사용한다.

내부 `SynthesisInput` 예시는 다음과 같다.

```json
{
  "sourceJobIdA": "job_video_a",
  "sourceJobIdB": "job_video_b",
  "cameraIdA": "00_00",
  "cameraIdB": "00_01",
  "calibrationRef": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
  "sync": {
    "mode": "timestamp",
    "timestampDomain": "media_time_ms",
    "maxDeltaMs": 16.7,
    "fallback": "frameIndex_for_gt_aligned_dataset_only"
  },
  "landmarkSet": "mediapipe_pose_33",
  "outputCoordinateSystem": "panoptic_world_cm"
}
```

고정 매핑:
- Video A upload slot -> `sourceJobIdA`, `cameraIdA`
- Video B upload slot -> `sourceJobIdB`, `cameraIdB`

### 왜 샘플 경로를 고정하지 않는가
- 이 합성기는 사용자가 직접 두 JSON 경로를 넣는 제품이 아니다.
- 현재 DB가 없으므로 산출물은 우선 `backend/tmp`나 job manager 내부 artifact로 존재한다.
- 따라서 문서에 특정 샘플 skeleton 파일 경로를 고정하면 오히려 구현을 좁힌다.
- 필요한 것은 "어디에 저장됐는가"가 아니라 "어떤 job artifact를 읽을 수 있는가"다.

첫 구현에서는 다음 인터페이스를 둔다.

```text
SkeletonArtifactRepository
- get_skeleton_summary(job_id) -> videoInfo
- iter_skeleton_frames(job_id) -> frame payload stream
- write_skeleton3d(job_id, payload) -> artifact ref
- write_evaluation(job_id, payload) -> artifact ref
```

파일 기반 구현은 지금 바로 가능하고, DB 기반 구현은 나중에 같은 인터페이스 뒤로 넣는다.

## 카메라 기하 모델 계약

### 현재 있는 것
Panoptic 데이터셋에는 카메라와 실험 환경 정보가 있다.

- `K`: intrinsic matrix
- `distCoef`: 렌즈 왜곡 계수
- `R`, `t`: world coordinate와 camera coordinate 사이의 extrinsic 정보
- 단위: Panoptic 문서 기준 `t`와 GT 좌표는 cm로 본다.

### 구현할 것
구현 방향은 정해져 있다. `00_00`, `00_01` 카메라 항목을 사용하고, 합성기가 직접 Panoptic JSON을 해석하지 않도록 카메라 기하 계층이 `CameraModel`을 제공한다.

구현 항목:
- `cameraId`로 카메라 항목 선택
- `K`, `distCoef`, `R`, `t`를 numeric matrix로 로드
- projection matrix 구성
- 좌표계 방향과 단위 검증
- OpenCV 함수에 넣을 수 있는 camera matrix와 distortion coefficients 제공
- GT 3D point를 각 카메라로 reprojection 하는 테스트로 해석이 맞는지 확인

`CameraCalibrationService` 책임:
- `calibrationRef`를 읽는다.
- `cameraId`로 카메라 항목을 찾는다.
- Panoptic JSON 값을 `CameraModel`로 변환한다.
- 좌표계, 단위, 카메라 ID 유효성을 검증한다.
- triangulation과 reprojection에 필요한 matrix를 제공한다.

`Skeleton3DSynthesizer` 책임:
- 입력 계약의 `cameraIdA/B`와 `calibrationRef`를 검증한다.
- `CameraCalibrationService`에서 `CameraModel`을 조회한다.
- 조회한 모델을 observation builder와 triangulation stage에 넘긴다.
- 카메라 모델 조회 실패를 synthesis job 실패로 기록한다.

권장 런타임 모델:

```text
CameraModel
- camera_id
- image_width
- image_height
- K
- dist_coeffs
- R
- t
- projection_matrix
- coordinate_system = panoptic_world_cm
```

## 2D 관측점 좌표계와 왜곡 상태
여기서 말하는 왜곡은 pose inference 결과가 프레임마다 튀는 현상을 뜻하지 않는다.

렌즈 왜곡은 카메라 광학계 때문에 이미지의 2D 픽셀 좌표가 실제 pinhole camera model과 어긋나는 문제다. Panoptic calibration의 `distCoef`는 이 광학 왜곡을 설명하는 값이다.

구분:
- 렌즈 왜곡: 카메라 광학계 때문에 이미지 좌표가 휘는 문제. 카메라 기하 전처리에서 `K`, `distCoef`로 다룬다.
- pose inference noise: MediaPipe가 관절 위치를 프레임마다 부정확하게 찍거나 튀는 문제. visibility, presence, temporal smoothing, reprojection error로 다룬다.

따라서 합성기의 책임은 OpenCV 전처리를 직접 요구하는 것이 아니라, triangulation에 들어가는 2D 관측점의 좌표계와 왜곡 상태를 명확히 하는 것이다. 실제 보정 함수는 `CameraCalibrationService` 또는 `LandmarkObservationBuilder` 같은 카메라 기하 계층에 둔다.

첫 구현의 관측점 준비 흐름은 다음처럼 둔다.

1. MediaPipe normalized 좌표를 픽셀 좌표로 변환한다.
2. 관측값에 `distortionState`를 기록한다.
3. 카메라 기하 계층이 필요하면 `K`, `distCoef`를 사용해 triangulation용 undistorted point를 만든다.
4. 결과 3D point를 다시 각 카메라로 project해 reprojection error를 계산한다.

권장 `distortionState` 값:
- `distorted_pixel`: 원본 이미지 픽셀 좌표다. triangulation 전 카메라 기하 계층에서 보정이 필요하다.
- `undistorted_normalized`: 카메라 모델 기준으로 보정된 normalized point다. 중복 보정하면 안 된다.
- `unknown`: 입력 상태를 확정할 수 없으므로 합성기를 실패 처리한다.

## 프레임 정합 기준

### frameIndex와 timestamp의 차이
- `frameIndex`는 영상 안에서 몇 번째 프레임인지 나타내는 순번이다.
- `timestampMs`는 그 프레임이 어느 시각의 관측인지 나타내야 하는 값이다.
- 같은 fps라도 두 카메라의 시작 시점이 다르거나 중간에 drop frame이 있으면 같은 frameIndex가 같은 순간을 뜻하지 않는다.
- 따라서 실제 카메라 도입까지 고려하면 timestamp가 더 올바른 1차 기준이다.

### 단, timestamp도 조건이 있다
timestamp가 충분하려면 두 카메라의 timestamp가 같은 시간 기준을 공유해야 한다.

좋은 timestamp:
- 같은 capture clock에서 나온 monotonic timestamp
- hardware sync 또는 software sync 후 같은 time origin으로 환산된 timestamp
- 녹화 파일의 PTS가 공통 기준으로 정렬된 timestamp

위험한 timestamp:
- 각 영상 파일을 decode하면서 `frame_index / fps`로 새로 만든 timestamp
- 각 영상 시작점을 0ms로 둔 media-local timestamp
- 촬영 시작 오프셋이 제거되지 않은 timestamp

현재 `backend/service/video_reader.py`의 `timestampMs`는 `frame_index * 1000 / source_fps`로 계산된다. 즉 현재 값은 실제 capture timestamp가 아니라 media-local derived timestamp다. GT-aligned clip에서는 두 영상이 이미 같은 시작점으로 잘려 있으므로 이 timestamp와 frameIndex가 거의 같은 의미를 가진다.

### 결정
첫 합성기는 timestamp-first로 설계한다.

- 기본 alignment mode: `timestamp`
- 허용 오차: 기본 `maxDeltaMs = half_frame_interval`
- Panoptic GT-aligned 데이터셋에서는 `frameIndex`도 함께 비교해 sanity check로 남긴다.
- 실제 카메라 도입 시 timestamp 기준과 동기화 방식은 그 단계에서 별도 결정한다.

권장 sync metadata:

```json
{
  "mode": "timestamp",
  "timestampDomain": "capture_time_ms",
  "maxDeltaMs": 16.7,
  "driftCorrection": "none",
  "fallback": "drop_unmatched"
}
```

## 2D 좌표 변환
MediaPipe `landmarks[].x`와 `landmarks[].y`는 보통 이미지 크기에 대한 normalized 좌표다. 예를 들어 `x=0.5`, `y=0.5`는 이미지 중앙을 뜻한다.

하지만 카메라 캘리브레이션의 `K`와 OpenCV triangulation 입력은 픽셀 좌표 또는 카메라 normalized 좌표를 요구한다. 그래서 이미지 해상도가 필요하다.

변환:

```text
pixel_x = landmark.x * videoInfo.width
pixel_y = landmark.y * videoInfo.height
```

따라서 `videoInfo.width`와 `videoInfo.height`는 단순 표시 정보가 아니라 2D 관측값을 카메라 모델 좌표로 옮기는 데 필요한 값이다. 이 값이 없으면 합성기는 해당 job artifact를 거부하거나 원본 video metadata에서 보강해야 한다.

## triangulation 청사진

### 서비스 구성
- `CameraCalibrationService`
  - Panoptic calibration JSON을 읽고 `CameraModel`을 제공한다.
- `FrameAlignmentService`
  - 두 skeleton frame stream을 timestamp 기준으로 pairing한다.
- `LandmarkObservationBuilder`
  - normalized landmark를 pixel point로 변환하고, triangulation 입력 좌표계와 `distortionState`를 명시한다.
- `TriangulationService`
  - 관절별 2D 관측값 두 개로 3D point를 복원한다.
- `ReprojectionScorer`
  - 3D point를 각 카메라에 다시 투영하고 reprojection error를 계산한다.
- `Skeleton3DSynthesizer`
  - 전체 orchestration과 output JSON 생성을 담당한다.

### 처리 순서
1. `SynthesisInput`을 검증한다.
2. source job artifact에서 `videoInfo`와 frame stream을 연다.
3. `CameraCalibrationService`에서 `cameraIdA/B`의 `CameraModel`을 조회한다.
4. timestamp 기준으로 A/B frame을 pairing한다.
5. 한쪽 `poseDetected=false`면 frame은 유지하고 joints는 실패 처리한다.
6. 관절별로 양쪽 landmark를 찾는다.
7. visibility/presence가 threshold 미만이면 해당 joint를 실패 처리한다.
8. normalized 좌표를 pixel 좌표로 변환한다.
9. 관측점이 `distorted_pixel`이면 카메라 기하 계층에서 triangulation용 undistorted point를 만든다.
10. DLT 기반 triangulation으로 3D point를 구한다.
11. 3D point를 양쪽 카메라로 재투영한다.
12. reprojection error가 threshold를 넘으면 `success=false`로 둔다.
13. frame과 전체 quality summary를 누적한다.

### 기본 threshold
- `minVisibility`: `0.5`
- `minPresence`: `0.5`
- `maxTimestampDeltaMs`: `1000 / fps / 2`
- `maxReprojectionErrorPx`: 첫 실행 결과를 보고 조정하되 초기값은 `8.0`

## 3D 출력 스키마 청사진
3D 결과는 기존 2D skeleton JSON을 확장하지 않고 별도 schema로 저장한다.

```json
{
  "schemaVersion": "skeleton3d.v1",
  "synthesisInfo": {
    "sourceJobIds": ["job_video_a", "job_video_b"],
    "cameraPair": ["00_00", "00_01"],
    "calibrationRef": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
    "landmarkSet": "mediapipe_pose_33",
    "coordinateSystem": "panoptic_world_cm",
    "sync": {
      "mode": "timestamp",
      "timestampDomain": "media_time_ms",
      "maxDeltaMs": 16.7
    },
    "thresholds": {
      "minVisibility": 0.5,
      "minPresence": 0.5,
      "maxReprojectionErrorPx": 8.0
    }
  },
  "frames": [
    {
      "frameIndex": 118,
      "timestampMs": 3937.27,
      "timestampDeltaMs": 0.0,
      "source": {
        "00_00": { "frameIndex": 118, "timestampMs": 3937.27, "poseDetected": true },
        "00_01": { "frameIndex": 118, "timestampMs": 3937.27, "poseDetected": true }
      },
      "joints": [
        {
          "name": "left_hip",
          "landmarkIndex": 23,
          "position": { "x": 0.0, "y": 0.0, "z": 0.0 },
          "success": true,
          "failureReason": null,
          "observations": {
            "00_00": {
              "normalized": { "x": 0.5, "y": 0.5 },
              "pixel": { "x": 960.0, "y": 540.0 },
              "visibility": 0.93,
              "presence": 0.91,
              "reprojectionErrorPx": 1.2
            },
            "00_01": {
              "normalized": { "x": 0.52, "y": 0.49 },
              "pixel": { "x": 998.4, "y": 529.2 },
              "visibility": 0.9,
              "presence": 0.89,
              "reprojectionErrorPx": 1.4
            }
          }
        }
      ],
      "quality": {
        "successfulJointCount": 25,
        "failedJointCount": 8,
        "meanReprojectionErrorPx": 2.1
      }
    }
  ],
  "qualitySummary": {
    "pairedFrameCount": 3479,
    "usableFrameCount": 3400,
    "usableJointRatio": 0.82,
    "meanReprojectionErrorPx": 2.4,
    "failureReasonCounts": {
      "low_visibility": 0,
      "missing_landmark": 0,
      "high_reprojection_error": 0,
      "unmatched_timestamp": 0
    }
  }
}
```

## GT 평가 청사진

### 평가 범위
- GT 파일: `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json`
- GT frame range: `118 ~ 3596`
- GT skeleton: COCO-19, 단위 cm
- 합성 결과: MediaPipe 33 기반 skeleton3d

### 관절 매핑
첫 버전은 직접 매칭 가능한 관절만 평가한다.

- nose
- left_shoulder / right_shoulder
- left_elbow / right_elbow
- left_wrist / right_wrist
- left_hip / right_hip
- left_knee / right_knee
- left_ankle / right_ankle
- left_eye / right_eye
- left_ear / right_ear

`neck`, `mid_hip`처럼 MediaPipe에 직접 없는 COCO 관절은 첫 raw metric에서 제외한다. 필요하면 양쪽 어깨 또는 엉덩이 평균으로 derived metric을 별도 계산한다.

### 지표
- MPJPE mean / median / p95
- per-joint MPJPE
- per-frame MPJPE
- valid joint ratio
- valid frame ratio
- reprojection error mean / median / p95
- failure reason histogram

### 좌표계 처리
- 합성 결과가 Panoptic world coordinate cm로 바로 나오는지 먼저 raw metric으로 확인한다.
- 축 방향이나 원점 차이가 드러나면 rigid alignment metric을 별도로 추가한다.
- raw metric과 aligned metric은 섞지 않는다.

평가 출력:

```json
{
  "schemaVersion": "skeleton3d_evaluation.v1",
  "evaluationInfo": {
    "gtRef": "171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json",
    "mappingVersion": "mediapipe33_to_coco19_subset.v1",
    "unit": "cm"
  },
  "metrics": {
    "mpjpeMeanCm": 0.0,
    "mpjpeMedianCm": 0.0,
    "mpjpeP95Cm": 0.0,
    "validJointRatio": 0.0,
    "meanReprojectionErrorPx": 0.0
  },
  "byJoint": [],
  "byFrame": []
}
```

## 실행 진입점 청사진

### 정식 파이프라인
1. Video A/B analysis job을 실행한다.
2. 각 job의 skeleton artifact가 생성된다.
3. dual synthesis stage가 `sourceJobIdA/B`와 camera binding을 받는다.
4. `SkeletonArtifactRepository`가 두 skeleton frame stream을 제공한다.
5. `Skeleton3DSynthesizer`가 3D skeleton artifact를 쓴다.
6. 선택적으로 `Skeleton3DEvaluator`가 evaluation artifact를 쓴다.
7. API는 synthesis status, skeleton3d page, evaluation summary를 조회한다.

### 개발용 CLI
CLI는 제품 진입점이 아니라 같은 서비스를 재현하기 위한 smoke test다.

```text
python backend/scripts/run_3d_synthesis.py --input synthesis_input.json --output backend/tmp/synthesis_debug
```

CLI는 다음 상황에만 쓴다.
- API 없이 calibration, alignment, triangulation을 빠르게 검증할 때
- CI나 로컬에서 작은 fixture로 단위 동작을 확인할 때
- GT 평가 script를 반복 실행할 때

## 분석 연결 청사진
첫 버전에서는 3D 결과를 기존 `analysis_pipeline.py`에 직접 넣지 않는다.

단계:
1. `skeleton3d` 원본 artifact를 안정화한다.
2. `Skeleton3DAnalysisAdapter`를 만든다.
3. adapter는 성공한 관절만 feature로 내보내고 실패 관절은 mask로 전달한다.
4. 기존 2D feature namespace와 별도 3D feature namespace를 쓴다.
5. 3D 분석 지표가 안정되면 `analysis_pipeline.py`가 2D/3D 입력 모드를 구분하도록 확장한다.

Adapter 출력 초안:

```json
{
  "mode": "general_motion_3d",
  "coordinateSystem": "panoptic_world_cm",
  "frames": [
    {
      "timestampMs": 3937.27,
      "features3d": {
        "left_hip": { "x": 0.0, "y": 0.0, "z": 0.0, "valid": true }
      },
      "quality": {
        "usableJointRatio": 0.82,
        "meanReprojectionErrorPx": 2.1
      }
    }
  ]
}
```

## 권장 구현 순서

### Phase A. 계약과 캘리브레이션
- `backend/schema/synthesis.py`
- `backend/service/skeleton_artifact_repository.py`
- `backend/service/camera_calibration.py`
- calibration loader 단위 테스트

### Phase B. 정합과 triangulation
- `backend/service/frame_alignment.py`
- `backend/service/landmark_observation.py`
- `backend/service/triangulation.py`
- timestamp alignment, 좌표 변환, reprojection 단위 테스트

### Phase C. 합성 결과와 평가
- `backend/service/skeleton_3d_synthesizer.py`
- `backend/service/skeleton_3d_evaluator.py`
- `backend/scripts/run_3d_synthesis.py`
- skeleton3d fixture와 GT subset 평가 테스트

### Phase D. API와 분석 adapter
- synthesis job status API
- skeleton3d page API
- evaluation summary API
- `Skeleton3DAnalysisAdapter`

## 명시적으로 미루는 것
- 실제 카메라 캘리브레이션 자동화
- 3개 이상 카메라 일반화
- 동적 카메라 선택 UI
- 실시간 streaming synthesis SSE
- MediaPipe `world_landmarks`와 triangulated landmark 융합
- 기존 2D 분석 파이프라인 전면 개조

## 참고 경로
- `backend/service/job_manager.py`
- `backend/service/video_reader.py`
- `backend/service/skeleton_mapper.py`
- `backend/service/dual_video_synthesis_coordinator.py`
- `backend/service/analysis_pipeline.py`
- `backend/service/analysis_preprocess.py`
- `backend/schema/frame.py`
- `backend/schema/pose.py`
- `171204_pose1/171204_pose1/calibration_171204_pose1.json`
- `171204_pose1/171204_pose1/hdVideos_gt_aligned/metadata.json`
- `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json`
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`
