# 데이터 Shape 채택 검토

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/03_data_shapes_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/03-data-shapes.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
## 문서 관계
- 부모 문서: `../rack-motion-adoption-design.md`
- 원본 참조 문서: `../../32-feat-rack-motion-pipeline-requirements/03_data_shapes_ko.md`
- 원본 제목: `데이터 Shape`
- 상태: 사용자 채택 결정 반영 중

## 검토 목적
이 문서는 #32의 data shape 요구를 현재 MVP v2의 2D skeleton artifact, `skeleton3d.v1`, synthesis debug report, `rack_motion.*.v1` schema와 비교한다. 목표는 지금 있는 JSON record/list 기반 구조를 무시하고 dense array만 도입하는 것이 아니라, rack-tracker가 실제로 join, validate, persist, paginate하기 쉬운 shape를 고르는 것이다.

## 현재 shape 현황

### 2D skeleton artifact
- Producer: `backend/service/skeleton_mapper.py`, 저장: `backend/service/job_manager.py`의 `SKELETON_DIR/{job_id}.json`.
- Shape: `{ frames, videoInfo, nextTimestampCursorMs, cameraBinding?, imageCoordinateSpace? }`.
- `frames[]`는 `{ frameIndex, timestampMs, poseDetected, landmarks[] }`이고 `landmarks[]`는 MediaPipe 33 landmark의 normalized `x`, `y`, `z`, `visibility`, `presence`를 담는다.
- 현재 raw 2D skeleton artifact에는 top-level `schemaVersion`과 `sessionId`가 없다. `job_id`와 file path가 사실상 join key 역할을 한다.

### 3D synthesis artifact
- Producer: `backend/service/skeleton_3d_synthesizer.py`, 저장/조회: `SkeletonArtifactRepository`.
- Shape: `skeleton3d.v1` top-level `{ schemaVersion, synthesisInfo, timeline, frames, qualitySummary, debugReport }`.
- `frames[]`는 frame별 `joints[]`를 담고, joint는 `position`, `diagnosticPosition`, `success`, `failureReason`, `reprojectionErrorPx`, `cameraDepths`, `observations`를 가진다.
- API는 `/synthesis/jobs/{job_id}/skeleton3d?offset=&limit=`로 paged frames를 반환한다.

### Synthesis debug/evaluation artifact
- Debug: `synthesis_debug_report.v1`에 `frameAlignmentDebug`, `observationTraceDebug`, `crossViewValidationDebug`, `triangulationTraceDebug`가 분리되어 있다.
- Evaluation: `skeleton3d_evaluation.v1`은 GT 평가와 reprojection summary를 별도 artifact로 저장한다.
- 이 분리는 #32의 "diagnostic과 user export 분리" 방향과 맞다.

### Rack motion schema
- `backend/schema/rack_motion.py`는 Pydantic record schema 중심이다. dense ndarray storage schema가 아니다.
- `Observation2D`: source-image pixel point 또는 missing/rejected status를 camera/frame/target 단위 record로 검증한다.
- `ReconstructionTarget3D`: frame/target 단위 3D point, mode, used camera ids, reprojection error, quality metrics를 검증한다.
- `RackMotionFrame`: session/frame 단위 rack anchors, support zones, barbell entity, quality metrics를 담는다.
- 현재 repository, endpoint, frontend adapter는 없다.

## #32 data shape와 현재 시스템 차이
| #32 shape 항목 | #32 요구 내용 | MVP v2 현재 대응 | 현재 시스템과의 차이 또는 부적합 | 권장 방향 | 후속 산출물 |
| --- | --- | --- | --- | --- | --- |
| versioned artifact envelope | 모든 영구 artifact에 `schema_version`, `session_id`, coordinate `space_id`, axis/channel metadata를 둔다. | `skeleton3d.v1`, debug/evaluation, `rack_motion.*.v1`은 version을 가진다. raw 2D skeleton artifact는 top-level schemaVersion이 없다. | 2D skeleton은 기존 product artifact라 바로 깨뜨리기 어렵다. rack motion artifact는 처음부터 versioned envelope로 만들 수 있다. | 채택 결정. 새 `rack_motion.*.v1` artifact는 처음부터 explicit `schemaVersion`, `sessionId`, `sourceRefs`, `coordinateSpaces`, producer/provenance를 가진다. 기존 2D skeleton artifact는 MVP v2에서 강제 migration하지 않는다. | rack motion artifact envelope policy |
| dense `Observation2D[camera, frame, target, channel]` | offline batch에는 dense array를 권장하고 channel metadata를 요구한다. | 현재 2D skeleton은 `frames[].landmarks[]` record/list shape다. `Observation2D` schema도 per-observation record다. | dense array는 NumPy 연산에는 좋지만 현재 API/frontend/persistence는 JSON pagination과 record validation에 맞춰져 있다. | 부분 채택 권장. 내부 batch 계산에는 dense 변환을 허용하되 public artifact는 record JSON 또는 chunked record batch로 시작한다. | record batch schema, optional dense internal adapter |
| `PreprocessTransform` | source frame과 detector input frame 사이 transform record를 저장한다. | `imageCoordinateSpace.preprocessTransform`은 `None`; detector input transform artifact는 없다. | 현재 MediaPipe adapter가 internal preprocessing을 숨기므로 transform을 정확히 채울 수 없다. | 보류 권장. bar/rack detector 도입 시 source pixel observation의 provenance로 추가한다. | `rack_motion.preprocess_transform.v1` |
| `CalibrationBundle` | calibration id, camera ids, intrinsics/distortion/extrinsics, capture world, target, quality를 묶는다. | `CameraCalibrationService`가 external calibration JSON을 바로 읽고 `CameraModel`을 만든다. | current shape는 rack-tracker-owned schema가 아니고 quality/report field가 없다. | 채택 권장. 외부 file import는 adapter로 숨기고 내부 bundle shape를 새로 둔다. | `rack_motion.calibration_bundle.v1` |
| `Reconstruction3D[frame, target, channel]` | raw 3D target 위치, quality, sidecar reprojection/used camera/status arrays를 저장한다. | `skeleton3d.v1.frames[].joints[]` record shape가 유사 정보를 가진다. `ReconstructionTarget3D`는 per-target record schema다. | current 3D output은 person joints에 묶여 있고 bar/rack target을 포함하지 않는다. dense shape보다 record shape가 현재 API에 맞다. | 부분 채택 권장. public rack artifact는 `ReconstructionTarget3D` record batch로 시작하고, 필요 시 internal dense view를 만든다. | skeleton3d-to-reconstruction mapper |
| `EntityFrame3D` | frame 단위 person/barbell/rack entity, events, quality를 담는다. | `RackMotionFrame`은 rack anchor/support zone/barbell만 담고 person entity와 events field는 아직 없다. | schema가 #32 전체 entity frame보다 좁다. 이 상태로 rack analyzer를 만들면 person-bar relationship과 event provenance가 부족하다. | 채택 보강 권장. 단기에는 `RackMotionFrame`에 person subset과 candidate events 확장 계획을 문서화하고, 실제 구현은 bar/rack source가 생긴 뒤 진행한다. | entity frame schema extension plan |
| sparse representation | live stream 또는 optional target이 많은 경우 sparse record 허용, 그래도 ids/status/quality 필수. | 현재 `Observation2D`, `ReconstructionTarget3D`는 sparse record에 가깝다. `/jobs` streaming pipeline도 chunk 단위로 처리한다. | artifact storage는 아직 chunked rack motion store가 없다. | 채택 결정. public rack artifact는 sparse JSON record batch를 우선 사용하고, dense array는 internal adapter로 보류한다. | chunked artifact repository |
| camera/frame/target ids | 모든 shape가 camera id, frame id, target id, entity id로 다시 join 가능해야 한다. | `skeleton3d.v1`은 camera pair, frameIndex, landmarkIndex/name을 가진다. `Observation2D`/`ReconstructionTarget3D`는 ids를 가진다. | `targetId` namespace가 아직 정해지지 않았다. MediaPipe landmark name과 rack target id가 섞일 위험이 있다. | 채택 결정. `person.*`, `barbell.*`, `rack.*` namespace를 사용하고, public rack artifact는 MediaPipe 33 전체가 아니라 curated anatomical target set을 노출한다. MediaPipe index/name은 provenance/debug로 보존한다. | target/entity id naming policy |
| missing numeric coordinate as `NaN` | numeric array에서 missing coordinate는 `NaN`, confidence 실패는 `0.0`을 권장한다. | Pydantic record schema는 missing coordinate를 `None`으로 표현한다. `Observation2D`는 non-detected일 때 x/y를 금지한다. | JSON API에서 `NaN`은 표준 JSON 호환성이 나쁘다. 현재 project shape는 `None/null`과 status/failureReason이 더 자연스럽다. | 제외 또는 변형 채택 권장. public JSON artifact는 `null` + status/failureReason을 쓰고, internal NumPy dense view에서만 `NaN`을 허용한다. | missing value policy |
| quality metric shape | metric name, unit, aggregation, value, status, policy id를 가진다. | `QualityMetric`은 metricName, value, status, unit, policyId, detail을 가진다. warning/failed에는 policyId를 요구한다. | aggregation level, space id, session id는 현재 `QualityMetric`에 없다. frame/entity context에 매달리는 구조다. | 채택 보강 권장. 현재 schema는 좋은 시작점이지만 metric catalog와 aggregation metadata가 필요하다. | metric catalog, `aggregationLevel` field 검토 |
| diagnostics shape | 사용자 export와 developer diagnostic을 분리한다. | `SkeletonArtifactRepository`가 skeleton3d, evaluation, debug를 별도 directory와 endpoint로 분리한다. | rack motion artifact repository는 아직 없어 같은 분리가 적용되지 않았다. | 채택 권장. rack motion repository도 `frames`, `quality`, `debug`를 분리한다. | rack motion repository layout |

## 우리 프로젝트에 안 맞는 부분
- public API artifact를 당장 dense ndarray shape로 만드는 것은 현재 React frontend와 FastAPI JSON pagination 구조에 맞지 않는다.
- JSON artifact에서 missing coordinate를 `NaN`으로 저장하는 것은 피하는 편이 낫다. 현재 code와 Pydantic schema는 `None/null` + status/failureReason에 맞춰져 있다.
- 기존 2D skeleton artifact에 즉시 `schemaVersion`, `sessionId`, dense channel metadata를 강제하면 기존 `/jobs/{job_id}/skeleton` frontend hydration을 깨뜨릴 수 있다.
- `skeleton3d.v1`의 joint list를 그대로 rack motion entity frame으로 부르면 안 된다. target namespace와 entity binding이 다르다.

## 우선 반영하면 좋은 부분
- 새 rack motion artifact는 처음부터 versioned envelope, `sessionId`, `schemaVersion`, `producer`, `sourceRefs`, `coordinateSpaces`를 가진다. public 3D 좌표의 canonical numeric unit은 `meter`로 저장하고, display unit은 metric catalog로 분리한다.
- public rack motion storage는 sparse/record batch JSON으로 시작하고, 내부 reconstruction 계산에서는 필요할 때 dense NumPy view를 만든다.
- `Observation2D` producer를 만들 때 source skeleton `job_id`, `cameraBinding`, `imageCoordinateSpace`, `frameIndex`, `landmarkIndex/name`을 `targetId`로 정규화한다.
- `ReconstructionTarget3D` mapper는 `skeleton3d.v1` joint payload의 `success/failureReason/reprojectionErrorPx/cameraDepths/observations`를 잃지 않아야 한다.
- rack motion repository는 현재 `SkeletonArtifactRepository`처럼 user-facing frame payload와 debug/quality payload를 분리한다.

## 동기화 규칙
| 상황 | 처리 |
| --- | --- |
| 원본 `03_data_shapes_ko.md`가 수정됨 | artifact envelope, join key, 필수 필드 변경 여부를 이 문서에 반영한다. |
| `backend/schema/rack_motion.py` shape가 바뀜 | 이 문서의 rack motion schema 현황과 채택 매트릭스를 갱신한다. |
| `/jobs/{job_id}/skeleton` 또는 `/synthesis/jobs/{job_id}/skeleton3d` payload가 바뀜 | 현재 shape 현황과 migration risk를 갱신한다. |
| shape 채택 결정이 내려짐 | `backend/schema/`, repository, frontend adapter 변경 후보와 migration 필요 여부를 기록한다. |
