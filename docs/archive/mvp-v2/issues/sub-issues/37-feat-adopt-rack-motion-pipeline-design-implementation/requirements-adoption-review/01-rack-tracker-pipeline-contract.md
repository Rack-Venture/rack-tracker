# Rack-Tracker 파이프라인 계약 채택 검토

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/01_pipeline_contract_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/01-rack-tracker-pipeline-contract.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
## 문서 관계
- 부모 문서: `../rack-motion-adoption-design.md`
- 원본 참조 문서: `../../32-feat-rack-motion-pipeline-requirements/01_pipeline_contract_ko.md`
- 원본 제목: `Rack-Tracker 파이프라인 계약`
- 상태: 사용자 채택 결정 반영 중

## 검토 목적
이 문서는 #32의 `Rack-Tracker 파이프라인 계약`을 실제 MVP v2 frontend/backend 구현과 비교한 뒤, 어떤 요구는 바로 반영하고, 어떤 요구는 우리 프로젝트의 현재 구조에 맞게 바꾸고, 어떤 요구는 아직 맞지 않아 보류할지 정리한다. 현재 문서의 우선 해석 기준은 `06-open-questions.md`의 `2026-05-07 사용자 채택 결정`이다.

## 현재 MVP v2 구현 요약

### Backend
- `backend/controller/jobs.py`는 단일 비디오 업로드를 `/jobs`로 받고 `JobManager`가 frame extraction, MediaPipe pose inference, skeleton artifact 저장, 2D/general motion 분석을 수행한다.
- `backend/service/job_manager.py`의 기본 product 경로는 현재 `general_motion` 실험 모드이다. squat 분석 로직은 남아 있지만 frontend에서 exercise-specific field를 보내지 않는다.
- `backend/service/skeleton_mapper.py`는 2D pose artifact에 `cameraBinding`, `imageCoordinateSpace`, `videoInfo`를 붙인다. 좌표는 MediaPipe normalized image landmark가 기본이고, source pixel observation store는 아직 없다.
- `backend/controller/synthesis.py`와 `backend/service/skeleton_3d_synthesizer.py`는 두 개의 완료된 2D skeleton job을 입력으로 받아 `skeleton3d.v1` artifact, debug report, 선택적 evaluation artifact를 생성한다.
- `backend/service/frame_alignment.py`는 timestamp delta 기반 pair를 만들고 unmatched frame count를 요약한다. 별도 frame index artifact는 없다.
- `backend/service/camera_calibration.py`는 Panoptic-style calibration JSON을 직접 읽어 `CameraModel`로 바꾼다. rack-tracker 소유 입력 config, `CalibrationBundle` wrapper, calibration quality report는 없다.
- `backend/service/triangulation.py`는 두 카메라 관측을 OpenCV triangulation으로 합성하고 reprojection error, camera depth, epipolar Sampson error를 diagnostic으로 남긴다. multi-camera 일반화, outlier retriangulation, camera contribution weight는 없다.
- `backend/schema/rack_motion.py`에는 `Observation2D`, `ReconstructionTarget3D`, `RackAnchor`, `SupportZone`, `BarbellEntity`, `RackMotionFrame`, `QualityMetric`이 있지만 현재는 schema validation slice이고 producer, repository, API endpoint, frontend consumer가 없다.

### Frontend
- `frontend/src/App.jsx`는 두 개의 `useAnalysisSession()`을 만들고 `CoreDemoSection`, `LiveSyncSection`, `Skeleton3DSynthesisSection`에 넘긴다.
- `frontend/src/features/analysis-session/useAnalysisSession.js`는 `/jobs` 생성, SSE status stream, result/skeleton page hydration, benchmark loading을 담당한다.
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`는 두 2D session이 완료되면 camera id를 추론해 `/synthesis/jobs`를 자동 생성하고 paged `skeleton3d.v1`을 읽는다.
- `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx`는 skeleton joint를 Three.js로 표시한다. rack anchor, barbell endpoint, support zone, rack event, rack-world 분석 UI는 아직 없다.

## #32 계약과 현재 시스템 차이
| #32 계약 항목 | #32 요구 내용 | MVP v2 현재 대응 | 현재 시스템과의 차이 또는 부적합 | 권장 방향 | 후속 산출물 |
| --- | --- | --- | --- | --- | --- |
| `SessionManifest` | 하나의 분석 실행에 camera source, target schema, output space, artifact 위치, 설정을 묶는다. | `SynthesisPairManifest`가 두 source job, camera id, calibrationRef, sync 설정만 묶는다. `/jobs` 2D 분석에는 session-level manifest가 없다. | 현재 job id는 backend runtime job id이고, rack-domain session id나 artifact join key 역할을 안정적으로 하지 못한다. #32의 manifest 개념은 필요하지만 현재 synthesis manifest를 그대로 rack motion manifest로 키우면 2D job, 3D synthesis job, rack artifact가 섞인다. | 채택 결정. 새 `rack_motion.*.v1` artifact에는 `sessionId`, `sourceRefs`, `coordinateSpaces`, producer/provenance를 포함하고 기존 2D skeleton artifact는 강제 migration하지 않는다. | session manifest schema, source binding policy, artifact path/index policy |
| `CameraSource` | 원본 미디어를 수정하지 않고 frame stream과 camera metadata를 노출한다. | `VideoReaderService`가 OpenCV metadata를 읽고 sampled frame stream을 만든다. `SkeletonMapperService`가 filename에서 Panoptic camera id를 추론할 수 있다. | 현재 rack motion은 원본 media source가 아니라 완료된 skeleton artifact를 주로 소비한다. 원본 media probe report가 영구 artifact로 남지 않고, camera id 추론도 Panoptic filename 패턴에 의존한다. | 부분 채택 권장. 첫 rack motion slice에서는 기존 skeleton artifact의 `cameraBinding`을 읽고, 원본 media inventory는 새 detector/bar endpoint 단계 전까지 보류한다. | media source inventory 또는 skeleton source binding summary |
| `FrameIndex` | camera-local frame을 shared logical time으로 매핑하고 frame availability table과 sync warning을 남긴다. | `FrameAlignmentService.align()`이 timestamp 기반 pair, unmatched primary/secondary count, mean timestamp delta를 계산한다. `synthesis_debug_report.v1`에 alignment sample이 있다. | pair summary는 있지만 camera별 frame availability table, sync warning status artifact가 없다. frontend도 sync 품질을 rack motion policy로 표시하지 않는다. | 채택 결정. strict equal frame count는 block하지 않고 timestamp-based partial sync를 허용하며, dropped/missing frame은 sync quality metric과 warning으로 기록한다. | `rack_motion.frame_index.v1`, sync metric catalog |
| `FramePreprocessor` | detector input image를 만들고 source image와 detector input 사이 reversible transform을 기록한다. | `VideoReaderService`는 BGR-to-RGB 변환과 sampling을 수행하고, MediaPipe adapter가 내부 model input을 만든다. `imageCoordinateSpace.preprocessTransform`은 현재 `None`이다. | 현재 product path는 detector input image를 별도 artifact로 다루지 않는다. MediaPipe adapter 내부 resize/crop을 rack-tracker transform으로 복원하지도 않는다. | 보류 권장. barbell/rack detector를 직접 운영할 때 필요한 계약이다. 지금 3D synthesis 또는 rack schema 첫 slice에 넣으면 구현 부담만 커진다. | detector adapter 도입 시 `PreprocessTransform` schema |
| `TargetDetector2D` | detector별 출력을 rack-tracker `Observation2D`로 정규화한다. | `PoseInferenceService`는 MediaPipe pose 33 landmarks를 normalized coordinate로 저장한다. `LandmarkObservationBuilder`가 synthesis 중 normalized landmark를 pixel로 변환한다. | 현재 detector target은 person skeleton뿐이다. rack anchor, barbell endpoint, J-cup, safety pin detector가 없다. 합성 중 만든 pixel observation도 저장되지 않는다. | 부분 채택 권장. MediaPipe pose는 `person_keypoint` adapter로만 다루고, barbell/rack target은 별도 adapter 또는 manual/synthetic 입력으로 분리한다. | observation adapter boundary, target id naming policy |
| `ObservationStore2D` | camera/frame/target별 원시 2D 관측을 저장해 reconstruction과 debug에 재사용한다. | 2D skeleton artifact는 `frames[].landmarks[]`를 저장한다. `skeleton3d.v1`에는 joint별 per-camera observation debug가 들어가지만 별도 store는 없다. `Observation2D` schema만 존재한다. | 현재 관측은 MediaPipe landmark 중심이고 source-image pixel 기준 store가 아니다. reconstruction을 다시 하려면 skeleton artifact를 다시 읽고 변환해야 한다. | 우선 채택 권장. `rack_motion.observation2d.v1` 저장소는 #32 중 현재 시스템에 가장 잘 맞는 다음 구현 slice다. | `RackMotionObservationRepository`, skeleton-to-observation mapper |
| `CalibrationBundle` | intrinsics, distortion, extrinsics, capture-world, target, unit, quality를 묶는다. | `CameraCalibrationService`가 calibration file을 직접 읽어 `CameraModel`을 만든다. calibration id는 파일 경로나 hash가 일부 metadata에 남는다. | 현재 calibration schema는 rack-tracker 소유가 아니고 품질 요약도 없다. Panoptic file layout을 product contract처럼 노출하면 #37 clean-room/ownership 목표와 맞지 않는다. 실제 카메라 기반 streaming으로 확장할 때도 "파일 하나를 읽어 CameraModel로 변환"하는 경계만으로는 source/session/calibration version과 품질 판정을 안정적으로 연결하기 어렵다. | 채택 결정. 사전 입력은 rack-tracker 소유 JSON 또는 TOML config로 분리하고, Panoptic-style 파일은 external import adapter의 입력 중 하나로만 둔다. public 3D 좌표는 `meter`로 정규화하고 source unit은 provenance에 보존한다. | `calibration.toml` 또는 calibration input JSON, `rack_motion.calibration_bundle.v1.json`, import adapter, `rack_motion.calibration_quality_report.v1.json` |
| `ReconstructionEngine3D` | 다중 2D 관측을 3D target으로 합성하고 used camera, visibility, reprojection quality를 기록한다. | `TriangulationService`가 2-view pose joint를 재구성한다. 실패 joint는 `position=None`, `diagnosticPosition`, `failureReason`으로 분리한다. | #32의 일반 multi-camera target reconstruction과 달리 현재 구현은 두 카메라, MediaPipe pose joint, `skeleton3d.v1` payload에 묶여 있다. outlier 제거와 retriangulation도 없다. | 채택 결정. MVP v2 rack motion의 valid 3D/reconstruction path는 2-camera 이상만 허용하고, single-camera는 preview/degraded diagnostic으로만 둔다. | `ReconstructionTarget3D` producer, used camera id/status mapping |
| `EntityFrame3D` | 3D target을 person, barbell, rack entity로 조립한다. | `skeleton3d.v1`은 `frames[].joints[]` 중심이다. `RackMotionFrame` schema는 rack anchor, support zone, barbell entity를 담을 수 있지만 producer가 없다. | rack-world entity 자체는 목표 구조와 맞지만, 현재 `skeleton3d.v1` 결과를 곧바로 entity frame으로 간주하면 의미가 섞인다. 현재 3D 결과에는 barbell endpoint와 rack feature provenance가 없고, person entity도 MediaPipe joint list 그대로라 rack-domain target subset과 분리되지 않았다. | 채택 권장. 단, 기존 `skeleton3d.v1` payload를 entity frame으로 승격하지 않고, `ReconstructionTarget3D`, rack config, rack anchor provenance를 거친 별도 `RackMotionFrame` producer로 단계적으로 도입한다. 첫 slice는 synthetic/manual rack anchor + mapped person keypoint부터 시작하고, barbell은 detector나 cleared fixture가 생긴 뒤 확장한다. | `RackMotionFrame` mapper, person subset contract, rack anchor provenance |
| `WorldSpaceMapper` | capture-world 3D를 rack-centered analysis 좌표로 변환한다. | 현재 synthesis output은 `panoptic_world_cm`이고 `viewHint`로 Three.js 표시 방향을 알려준다. `rack_motion.py`에는 `capture_world`, `rack_world` literal이 있다. | `panoptic_world_cm`은 dataset-specific capture world에 가깝고 rack origin/axis를 정의하지 않는다. frontend의 display transform도 analysis coordinate transform이 아니다. | 우선 채택 권장. rack motion 분석은 `capture_world`와 `rack_world`를 분리해야 하며, skeleton으로 rack world를 추정하지 않는다. | rack config schema, `capture_to_rack` alignment artifact |
| `TemporalPostProcessor` | raw entity frame provenance를 유지하면서 smoothing/interpolation/velocity-ready trajectory를 만든다. | 3D synthesis는 frame별 joint payload 중심이다. 2D squat pipeline에는 smoothing과 rep segmentation이 있지만 rack motion artifact와 연결되지 않는다. | current smoothing은 2D squat feature 로직이고, rack entity trajectory provenance를 보존하지 않는다. | 보류 권장. raw rack artifact와 quality metric이 먼저 필요하다. | temporal trajectory artifact, interpolation policy |
| `RackAnalyzer` | rack-world entity에서 bar path, endpoint asymmetry, rack proximity, support-contact event, rep candidate를 계산한다. | `AnalysisPipelineService`는 general motion summary 또는 2D squat pipeline을 반환한다. `analysis_features.py`의 barbell proxy는 shoulder/wrist 기반 2D 추정치다. | 2D bar proxy를 rack-domain barbell endpoint로 취급하면 product 의미가 틀린다. rack anchor와 endpoint가 없어서 support-contact event도 계산할 수 없다. | 보류 권장. rack/bar/person entity frame이 생긴 뒤 별도 `RackMotionAnalyzer`로 구현한다. | rack-domain analyzer backlog, event policy |

## 현재 구현에 바로 연결하면 위험한 부분
- #32의 전체 media-to-rack-analysis 파이프라인 방향은 유효하지만, 한 번에 기존 MVP v2 경로에 합치는 방식은 위험하다. 현재 backend는 이미 `/jobs` 2D skeleton extraction과 `/synthesis` batch 3D synthesis로 나뉘어 있고, rack motion은 schema-only 상태라 session manifest, observation store, reconstruction target, entity frame을 단계적으로 연결해야 한다.
- `FramePreprocessor`와 detector input transform은 barbell/rack detector를 직접 붙일 때 필요한 계약이다. 현재 MediaPipe-only product path에서는 선행 구현보다 observation/reconstruction/entity boundary를 먼저 세우는 편이 낫다.
- rack-world entity와 `RackAnalyzer`는 목표 구조와 맞다. 다만 `RackAnalyzer`를 기존 `AnalysisPipelineService`에 바로 섞으면 2D pose/squat legacy 분석과 rack-domain 분석의 provenance가 섞인다. 먼저 `RackMotionFrame` producer와 rack-world entity contract를 만든 뒤 별도 `RackMotionAnalyzer`로 연결해야 한다.
- `panoptic_world_cm`을 rack world로 취급하면 안 된다. 현재 3D viewer가 그 좌표를 보기 좋게 바꾸는 것은 rendering transform이지 domain transform이 아니다. rack-world는 rack config, rack anchor, `capture_to_rack` provenance를 통해 별도로 만들어야 한다.
- 기존 2D bar proxy를 실제 barbell endpoint로 승격하면 안 된다. endpoint, bar tilt, rack proximity는 rack-world 좌표와 barbell target provenance가 있어야 한다.

## 우선 반영하면 좋은 부분
- session-level manifest 또는 registry를 새로 두고 job id, source skeleton id, camera binding, calibration id, rack config id, output artifact ref를 join 가능하게 만든다.
- `rack_motion.observation2d.v1` producer/store를 만들어 MediaPipe person keypoint라도 source-image pixel observation으로 보존한다.
- calibration은 user-authored JSON/TOML 입력과 external format import adapter를 분리하고, 영구 산출물은 rack-tracker 소유 `rack_motion.calibration_bundle.v1.json`과 `rack_motion.calibration_quality_report.v1.json`로 남긴다.
- 기존 `TriangulationService` 결과를 `ReconstructionTarget3D`로 변환하는 얇은 mapper를 만들고, used camera ids, failure reason, reprojection error, mode를 rack schema로 정리한다.
- `capture_world`와 `rack_world`를 문서와 schema에서 계속 분리하고, `capture_to_rack`은 rack anchor/config가 생길 때까지 명시적으로 missing 또는 not_computed로 둔다.
- frontend는 당분간 `skeleton3d.v1` viewer를 유지하고, rack motion artifact가 생긴 뒤 별도 rack overlay 또는 rack motion panel을 추가한다.

## 동기화 규칙
| 상황 | 처리 |
| --- | --- |
| 원본 `01_pipeline_contract_ko.md`가 수정됨 | 이 문서의 매트릭스를 다시 검토하고 변경 여부를 기록한다. |
| backend `/jobs` 또는 `/synthesis` payload가 바뀜 | 현재 구현 요약과 관련 계약 항목의 `MVP v2 현재 대응`을 갱신한다. |
| `backend/schema/rack_motion.py` producer, repository, API가 추가됨 | `ObservationStore2D`, `ReconstructionEngine3D`, `EntityFrame3D` 행의 상태를 구현 기준으로 갱신한다. |
| 사용자가 채택 방향을 결정함 | `권장 방향`을 채택, 보류, 제외 중 하나로 확정하고 후속 산출물을 구현 문서로 승격한다. |
