# 품질 Metric 채택 검토

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/04_quality_metrics_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/04-quality-metrics.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
## 문서 관계
- 부모 문서: `../rack-motion-adoption-design.md`
- 원본 참조 문서: `../../32-feat-rack-motion-pipeline-requirements/04_quality_metrics_ko.md`
- 원본 제목: `품질 Metric`
- 상태: 사용자 채택 결정 반영 중

## 검토 목적
이 문서는 #32의 quality metric 요구를 현재 MVP v2 backend/frontend에서 실제로 생산하거나 표시하는 품질 정보와 비교한다. 목표는 console log나 viewer 색상에 흩어진 값을 rack motion artifact와 policy로 승격할 수 있는지 판단하는 것이다.

## 현재 품질 정보 현황

### 2D 분석 및 skeleton extraction
- `backend/service/pose_inference.py`는 frame별 `poseDetected`, landmark별 `visibility`, `presence`를 저장한다.
- `backend/service/analysis_pipeline.py`의 `general_motion` summary는 `detectionRatio`, `usableFrameCount`, `frameCount`, `sampledFps`를 제공한다.
- `backend/service/benchmarking.py` 경로는 `poseDetectedRatio`, `avgVisibility` 같은 benchmark quality summary를 만든다.
- 이 값들은 2D pose extraction 품질이지 rack/barbell reconstruction 품질은 아니다.

### 3D synthesis
- `backend/service/frame_alignment.py`는 paired frame count, unmatched counts, max/mean timestamp delta를 반환한다.
- `backend/service/triangulation.py`는 joint별 reprojection error, camera depth, epipolar Sampson error, `behind_camera`, `high_reprojection_error`, `low_visibility`, `out_of_bounds` 같은 failure reason을 만든다.
- `backend/service/skeleton_3d_synthesizer.py`는 `qualitySummary`에 `pairedFrameCount`, `usableFrameCount`, `validFrameRatio`, `usableJointRatio`, `successfulJointCount`, `totalJointCount`, `meanReprojectionErrorPx`, `failureReasonCounts`를 담는다.
- `synthesis_debug_report.v1`은 alignment, observation, cross-view, triangulation trace를 분리한다.

### Frontend 표시
- `frontend/src/features/analysis-session/adapters.js`는 `skeleton3d.v1` joint를 renderable landmark로 바꾸면서 `success`, `failureReason`, `reprojectionErrorPx`를 유지한다.
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`는 A/B joint visibility와 delta를 표로 보여준다.
- `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx`는 `reprojectionErrorPx`와 threshold를 사용해 joint 색상을 바꾼다.
- 이 UI 표시는 diagnostic inspection이고 rack-domain acceptance policy는 아니다.

### Rack motion schema
- `backend/schema/rack_motion.py`의 `QualityMetric`은 `metricName`, `value`, `status`, `unit`, `policyId`, `detail`을 가진다.
- warning/failed metric에는 `policyId`를 요구한다.
- 아직 metric catalog, aggregation level, producer service, API response는 없다.

## #32 quality metric과 현재 시스템 차이
| #32 metric 항목 | #32 요구 내용 | MVP v2 현재 대응 | 현재 시스템과의 차이 또는 부적합 | 권장 방향 | 후속 산출물 |
| --- | --- | --- | --- | --- | --- |
| `detection_confidence` | detector confidence 또는 adapter-normalized confidence를 2D observation에 저장한다. | MediaPipe landmark `visibility`, `presence`가 있다. `Observation2D.confidence` schema도 있다. | MediaPipe `visibility`/`presence`는 rack/barbell detector confidence가 아니다. barbell endpoint나 rack feature detector confidence는 없다. | 부분 채택 권장. person keypoint observation에는 visibility/presence 기반 adapter confidence를 쓰되, target type별 confidence 의미를 catalog에 분리한다. | observation confidence policy |
| `per_camera_visibility` | camera/frame/target별 관측 가능 여부와 missing reason을 기록한다. | `poseDetected`, landmark visibility, joint `observations`가 있다. `Observation2D.status`는 detected/missing/outside_roi/rejected_by_policy를 지원한다. | 현재 raw skeleton에는 target별 missing reason이 약하고, `Observation2D` store가 없다. | 채택 권장. `Observation2D.status`를 producer에서 채우고 camera/target/session aggregation을 만든다. | visibility summary artifact |
| `sync_warnings` | frame count, timestamp, FPS, offset 문제를 warning record로 남긴다. | `FrameAlignmentService`가 paired/unmatched count와 timestamp delta summary를 만든다. debug sample도 있다. | warning/failed status와 policy id가 없다. | 채택 결정. strict equal frame count는 block하지 않고 timestamp-based partial sync를 허용한다. dropped/missing frame은 sync quality metric과 warning으로 기록한다. | sync metric catalog, partial sync policy |
| `reprojection_error` | target-level 및 per-camera reprojection error를 저장한다. | joint별 `reprojectionErrorPx`, `reprojectionErrorByCameraPx`, debug trace가 있다. | current artifact는 person joint 중심이고 rack target id에는 아직 연결되지 않는다. invalid point와 high-error point는 분리되어 있지만 policy catalog가 없다. | 우선 채택 권장. `ReconstructionTarget3D.reprojectionErrorPx`와 per-camera detail mapping을 만든다. | reconstruction quality mapper |
| `used_camera_count` | 3D target에 기여한 camera 수를 노출한다. | 현재 synthesis는 항상 두 카메라 입력이고 success joint는 두 view를 사용한다. `ReconstructionTarget3D.usedCameraIds`는 list를 요구한다. | 현재 `skeleton3d.v1` joint payload에는 explicit used camera count field가 없고 observations map으로 추론해야 한다. | 채택 결정. MVP v2 rack motion의 valid 3D/reconstruction path는 2-camera 이상만 허용한다. single-camera는 preview/degraded diagnostic으로만 남기고 calibrated 3D로 표시하지 않는다. | used-camera metric |
| `camera_contribution` | camera별 normalized contribution, weight, retained/rejected state를 기록한다. | 현재 confidence weighting이나 contribution weight는 없다. per-camera reprojection error만 있다. | 2-view OpenCV triangulation에서 weight/contribution을 public metric처럼 말하면 구현과 맞지 않는다. | 보류 권장. outlier rejection 또는 weighted reconstruction을 구현할 때 추가한다. | camera contribution design |
| `dropped_observations` | 제외/누락 관측을 detector absence와 구분해 audit한다. | failureReasonCounts와 low_visibility/out_of_bounds/missing_landmark가 있다. raw dropped observation store는 없다. | 현재 dropped reason은 joint reconstruction 결과에 붙고, observation-level audit artifact는 없다. | 채택 권장. Observation2D store와 함께 retained/rejected status를 추가한다. | dropped observation audit |
| `interpolation_spans` | temporal processing으로 채운 span을 raw measurement와 구분한다. | rack motion temporal artifact는 없다. 2D analysis에는 smoothing/rep segmentation이 있지만 interpolation provenance는 없다. | 현 MVP v2에는 raw rack trajectory가 없어 temporal metric을 계산할 기반이 없다. | 보류 권장. raw rack entity frame과 temporal postprocessor 이후 도입한다. | temporal metric policy |
| `world_space_alignment_quality` | capture world를 rack world로 mapping하는 fit quality를 보고한다. | `RackAnchor`와 `QualityMetric` schema는 있으나 rack alignment service가 없다. | rack-world transform이 없으므로 metric을 계산할 수 없다. dummy confidence를 넣으면 오해를 만든다. | 보류 결정. `rack_alignment`는 camera calibration과 분리된 user-authored/imported artifact로 두며, MVP v2 first slice에서는 manual/measured rack dimensions와 anchors를 1차 source로 삼는다. | rack alignment quality report |
| required quality fields | `schema_version`, `session_id`, metric name/unit, `space_id`, aggregation, value, status, `policy_id`를 포함한다. | `QualityMetric`에는 name/value/status/unit/policyId/detail이 있다. session/space/aggregation은 parent artifact context에 의존한다. | metric만 떼어내면 context가 부족하다. | 채택 보강 권장. parent artifact context + optional aggregation/space fields를 정한다. | quality metric envelope |

## 현재 threshold와 policy 해석
- `backend/schema/synthesis.py`의 `SynthesisThresholds`는 `minVisibility=0.5`, `minPresence=0.5`, `maxReprojectionErrorPx=8.0` 기본값을 가진다.
- 이 값들은 현재 `skeleton3d.v1` 실험 경로의 동작값이다. rack-domain policy catalog로 확정된 값이 아니다.
- `ThreeJSSkeleton.jsx`도 threshold를 색상 표시 기준으로 사용하지만, 이것은 viewer inspection rule이지 rack motion acceptance criterion이 아니다.
- #37 clean-room 방향상 threshold default는 외부 프로젝트나 기존 실험값을 무비판적으로 복사하지 말고 synthetic fixture, rack-tracker 소유 recording, 사용자 review로 정해야 한다.

## 우리 프로젝트에 안 맞는 부분
- 2D pose `detectionRatio`를 rack motion 전체 품질로 부르는 것은 맞지 않는다. person keypoint coverage와 bar/rack target quality는 분리해야 한다.
- reprojection error가 낮다고 rack-world alignment가 좋다고 볼 수 없다. calibration/capture reconstruction quality와 rack alignment quality는 별도 metric이다.
- frontend color threshold를 backend policy로 역수입하면 안 된다. UI threshold는 visual aid일 뿐이다.
- camera contribution metric은 현재 구현하지 않은 weighted reconstruction을 암시하므로 지금 public artifact에 넣지 않는 편이 낫다.
- temporal/interpolation metric은 raw/processed rack entity frame이 생기기 전까지 계산할 수 없다.

## 우선 반영하면 좋은 부분
- `QualityMetric` catalog를 만들고 metric별 `aggregationLevel`, `targetType`, `spaceId` 필요 여부, `policyId` 필요 여부를 정한다.
- `FrameAlignmentService` summary를 sync quality metric으로 승격한다.
- `TriangulationService`의 reprojection/failure reason을 `ReconstructionTarget3D.qualityMetrics`로 옮기는 mapper를 만든다.
- `Observation2D` store가 생기면 detection confidence, visibility, missing/rejected reason aggregation을 생성한다.
- user-facing quality summary와 developer debug report를 계속 분리한다.

## 동기화 규칙
| 상황 | 처리 |
| --- | --- |
| 원본 `04_quality_metrics_ko.md`가 수정됨 | metric 이름, 임계값 정책, failure status 변경 여부를 이 문서에 반영한다. |
| `SynthesisThresholds` 또는 triangulation failure reason이 바뀜 | current threshold/policy 해석과 reconstruction metric mapping을 갱신한다. |
| frontend viewer quality 표시가 바뀜 | UI 표시와 backend policy의 분리 설명을 다시 확인한다. |
| 품질 metric 채택 결정이 내려짐 | `QualityMetric.policyId`와 metric catalog 초안을 갱신한다. |
| 구현 문서로 승격함 | metric 산출 위치, 실패 조건, 테스트 fixture를 명시한다. |
