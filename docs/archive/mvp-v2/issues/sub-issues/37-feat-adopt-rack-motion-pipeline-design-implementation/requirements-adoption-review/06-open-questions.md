# 열린 질문 채택 검토

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/06_open_questions_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/06-open-questions.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
## 문서 관계
- 부모 문서: `../rack-motion-adoption-design.md`
- 원본 참조 문서: `../../32-feat-rack-motion-pipeline-requirements/06_open_questions_ko.md`
- 원본 제목: `열린 질문`
- 상태: 사용자 채택 결정 기록됨

## 검토 목적
이 문서는 #32의 열린 질문을 #37의 구현 전 결정 사항으로 재분류한다. 모든 질문이 첫 구현 slice의 blocker는 아니다. 현재 MVP v2는 2D skeleton extraction, two-job `skeleton3d.v1` synthesis, Three.js inspection viewer, rack motion schema validation까지만 구현되어 있으므로, 다음 slice에 필요한 결정과 장기 제품 결정을 구분한다.

## 현재까지 사실상 정리된 전제
- rack motion은 `skeleton3d.v1`을 직접 확장하는 것이 아니라 별도 `rack_motion.*.v1` contract로 둔다.
- 기존 3D synthesis는 production rack motion pipeline이 아니라 person skeleton reconstruction 실험 baseline이다.
- `single_camera_estimate`는 `ReconstructionTarget3D`에서 valid 3D로 표시할 수 없다.
- persisted rack motion 2D observation은 source-image pixel 기준으로 가는 것이 schema상 결정되어 있다.
- rack-world는 schema literal만 있고, 실제 anchor acquisition, rack config, `capture_to_rack` transform은 미정이다.
- frontend에는 rack motion UI가 없고 `skeleton3d.v1` inspection viewer만 있다.

## 2026-05-07 사용자 채택 결정

이 절은 `requirements-adoption-review/01-rack-tracker-pipeline-contract.md` ~ `07-frontend-rack-visualization-design.md`와 사용자의 순차 결정을 반영한다. 아래 결정은 이 문서의 "다음 slice 결정 필요성"과 "권장 분류"를 해석할 때 우선 적용한다.

| 결정 영역 | 채택 결정 | 반영 의미 |
| --- | --- | --- |
| 데이터 및 테스트 asset | 자동 테스트와 공개 sample output은 synthetic 또는 직접 소유 fixture만 사용한다. Panoptic `171204_pose1`은 dev-only external fixture로만 허용하고, barbell validation에는 사용하지 않는다. | Panoptic fixture는 person/camera/reconstruction 개발용이다. product-grade rack-world 또는 barbell 검증 fixture로 승격하지 않는다. |
| 카메라 및 동기화 | MVP v2 rack motion의 valid 3D/reconstruction path는 2-camera 이상만 허용한다. single-camera는 preview/degraded diagnostic으로만 두고, strict equal frame count는 block하지 않으며 timestamp-based partial sync를 허용한다. | dropped/missing frame은 sync quality metric과 warning으로 기록한다. single-camera result는 calibrated 3D로 표시하지 않는다. |
| 좌표 단위 | public `rack_motion.*.v1` 3D 좌표의 canonical numeric unit은 `meter`로 표준화한다. 분석/UI/report 표시 단위는 metric catalog에서 `cm`, `mm`, `m/s`, `m/s^2` 등으로 별도 정의한다. | "meter로 저장"과 "meter로 표시"를 분리한다. Panoptic 등 source unit은 provenance에 보존하고 mapper/import 단계에서 변환한다. |
| RackWorldSpace 생성 | `rack_alignment`는 `camera_calibration`과 분리된 user-authored/imported TOML 또는 JSON artifact로 둔다. MVP v2의 1차 source는 manual/measured rack dimensions와 anchors다. | 영상 기반 rack feature detection은 후속 보강이다. skeleton trajectory로 origin/floor/axis를 자동 정의하지 않는다. |
| Target namespace | `person.*`, `barbell.*`, `rack.*` namespace를 사용한다. Public rack artifact는 MediaPipe 33 전체를 그대로 계약화하지 않고, 헬스 자세/물리의학적 분석용 curated anatomical target set을 노출한다. | curated set에는 head/neck posture, wrist/hand, foot/stance, shoulder/hip/knee/ankle 등 주요 bilateral landmarks를 포함한다. MediaPipe index/name은 provenance/debug로 보존한다. |
| Barbell endpoint | Barbell endpoint는 장기 핵심 target이다. MVP v2 first slice에서는 automatic detector를 구현하지 않고, `barbell.left_endpoint`/`barbell.right_endpoint` contract, provenance, quality, synthetic/manual/imported fixture를 먼저 확정한다. | 실제 barbell detection/acquisition은 후속 핵심 workstream이다. endpoint provenance/quality가 없으면 bar tilt, endpoint asymmetry, rack proximity, support/contact event metric은 생성하지 않는다. |
| Frontend output scope | `07-frontend-rack-visualization-design.md`의 Stage 1 `Rack Volume Fixture Viewer`를 first frontend scope로 채택한다. 별도 `RackMotionViewer`를 만들고 기존 `ThreeJSSkeleton.jsx`와 분리한다. | Stage 2 Panoptic dev rack visualization은 다음 frontend slice 후보이고, Stage 3 real rack alignment/barbell trajectory와 Stage 4 event/biomechanics overlays는 후속이다. |
| Diagnostic visibility | MVP v2에서는 주요 diagnostic을 frontend에서 토글, drawer, inspector, diagnostic mode로 접근 가능하게 한다. 기본 화면은 demo/product-readable summary를 유지한다. | user-facing artifact와 debug artifact는 저장/API 레벨에서 계속 분리하되, frontend에서는 raw reprojection trace, LOS rays, camera frustum, per-camera observation, sync warning, provenance, quality detail을 확인할 수 있게 한다. |
| Schema migration | 새 `rack_motion.*.v1` artifact는 처음부터 explicit `schemaVersion`을 가진다. breaking change는 새 version으로 분리하고 기존 artifact는 importer/adapter로 읽는다. | 기존 2D skeleton artifact는 MVP v2에서 강제 migration하지 않는다. 새 artifact에는 `sessionId`, `sourceRefs`, `coordinateSpaces`, producer/provenance를 포함한다. |

## #32 열린 질문 재분류
| #32 질문 영역 | #32 질문 요지 | MVP v2 현재 대응 | 다음 slice 결정 필요성 | 권장 분류 | 후속 산출물 |
| --- | --- | --- | --- | --- | --- |
| 라이선스 및 의존성 | 목표 라이선스, 배포 형태, 허용 third-party library, model/data license를 정해야 한다. | #37 문서는 clean-room boundary를 명시한다. 기존 backend는 OpenCV, NumPy, MediaPipe, FastAPI, frontend는 React/Three.js를 사용한다. | 중간. 문서/mapper/schema slice는 진행 가능하지만, 외부 dataset/model/sample 사용 확대 전에는 필요하다. | 장기 제품/법무 결정. 구현 slice에서는 외부 source project material 금지를 유지한다. | dependency/license audit checklist |
| 데이터 및 테스트 asset | synthetic, 직접 capture, public data 중 무엇을 test에 쓸지 결정해야 한다. | `backend/tests/test_rack_motion_schema.py`, triangulation/synthesis tests는 synthetic fixtures를 사용한다. local `171204_pose1` dataset과 generated tmp artifacts가 존재한다. | 부분 해결. 자동 테스트/공개 sample은 synthetic 또는 owned fixture만 사용한다. Panoptic은 dev-only external fixture로 허용한다. | 채택 결정. Panoptic은 person/camera/reconstruction 개발용이며 barbell validation이나 product-grade rack-world 분석으로 승격하지 않는다. | synthetic rack/session fixture plan, dev-only fixture policy |
| 카메라 및 동기화 | single vs multi camera, timestamp availability, dropped/variable frame handling, strict sync 여부를 정해야 한다. | `/jobs`는 single video job, `/synthesis`는 two completed jobs를 timestamp delta로 align한다. strict equal frame count는 요구하지 않는다. | 부분 해결. valid 3D/reconstruction은 2-camera 이상, timestamp-based partial sync 허용으로 결정했다. | 채택 결정. single-camera는 preview/degraded diagnostic으로만 두고 calibrated 3D로 표시하지 않는다. | sync policy catalog |
| 캘리브레이션 | 첫 calibration target, canonical unit, distortion correction 위치, rack anchor source, quality summary를 정해야 한다. | `CameraCalibrationService`가 Panoptic-style JSON을 읽는다. unit/quality/rack anchor는 rack-tracker artifact로 정리되지 않았다. | 부분 해결. 좌표 canonical unit과 rack anchor source는 결정했다. calibration target과 distortion correction 위치, quality summary는 남아 있다. | 일부 채택. public 3D canonical unit은 meter, 표시 단위는 metric별 cm/mm/SI로 분리한다. rack anchor는 manual/measured `rack_alignment` artifact를 1차 source로 둔다. | calibration bundle wrapper, unit/display policy, rack alignment artifact |
| 좌표 공간 | rack origin/axis/vertical, session-global 여부, unit conversion 검증을 정해야 한다. | `panoptic_world_cm` output과 display `viewHint`가 있다. `rack_world` producer는 없다. `02-coordinate-spaces.md`는 camera calibration과 rack alignment 분리를 구체화했다. | 부분 해결. rack-world는 별도 `rack_alignment` artifact로 만들고, 없으면 `not_computed` 또는 `dev_assumption`으로 표시한다. | 채택 결정 일부. skeleton trajectory로 rack origin/floor/axis를 자동 정의하지 않는다. 정확한 origin/axis convention과 unit conversion 검증 방식은 rack alignment schema에서 확정한다. | rack-world policy, rack alignment schema, placeholder/degraded status |
| Target Schema | bar endpoint detectability, lift별 person keypoint, rack feature source, endpoint identity, multi-person 여부를 정해야 한다. | MediaPipe 33 person joints만 있다. bar/rack detector는 없다. MediaPipe default `num_poses=1`로 단일 athlete 가정에 가깝다. | 부분 해결. `person.*`, `barbell.*`, `rack.*` namespace와 curated anatomical target set 방향을 결정했다. | 채택 결정 일부. Public rack artifact는 MediaPipe 33 전체를 그대로 계약화하지 않고 물리의학적 자세 분석에 필요한 head/hand/foot/bilateral posture target set을 둔다. Barbell detector는 후속 핵심 workstream이다. | target namespace policy, curated anatomical target set, barbell endpoint contract |
| Reconstruction 및 Quality | metric별 camera count, block/warning behavior, reprojection summary, contribution weight, single-camera label을 정해야 한다. | `TriangulationService`는 2-view synthesis와 failure reason을 제공한다. `QualityMetric`은 warning/failed에 policyId를 요구한다. | 부분 해결. valid 3D camera count와 single-camera label policy는 결정했다. contribution weight는 보류한다. | 채택 결정 일부. 2-camera 이상을 valid reconstruction 기준으로 두고, single-camera는 preview/degraded diagnostic label을 강제한다. | reconstruction quality policy, metric catalog |
| Temporal Processing | interpolation span, smoothing/raw metric 구분, velocity/acceleration persistence를 정해야 한다. | rack trajectory artifact가 없다. 2D squat pipeline에는 smoothing/rep segmentation이 있으나 rack motion과 분리되어 있다. | 낮음. raw artifact slice에는 필요하지 않다. | 보류. raw observation/reconstruction/entity artifact 이후 결정. | temporal postprocessor plan |
| Rack Event Policy | near/contact threshold, evidence, hysteresis, event dependency, confidence 결합 방식을 정해야 한다. | support zone schema만 있고 event analyzer는 없다. | 낮음-중간. bar endpoint/rack-world 없이는 구현 불가. | 보류. endpoint + rack-world 이후 결정. Endpoint provenance/quality가 없으면 bar tilt, endpoint asymmetry, rack proximity, support/contact event metric은 생성하지 않는다. | support-contact event policy |
| Output 및 Product | 첫 output format, diagnostic visibility, schema migration, export metadata, UI/report 범위를 정해야 한다. | `/jobs`와 `/synthesis` API, paged skeleton3d, debug/evaluation endpoints가 있다. `07-frontend-rack-visualization-design.md`가 별도 `RackMotionViewer` Stage 1~4를 설계한다. | 부분 해결. first frontend scope는 Stage 1 `Rack Volume Fixture Viewer`로 결정했다. Diagnostic은 토글/모드로 frontend 접근 가능하게 한다. Schema migration은 새 rack motion artifact부터 엄격히 적용한다. | 채택 결정 일부. Backend artifact/API와 Stage 1 demo frontend를 함께 두고, Stage 2~4는 후속 slice로 둔다. | rack motion repository/API plan, Stage 1 RackMotionViewer plan, schema version policy |

## 다음 구현 slice에 필요한 최소 결정
| 결정 | 현재 추천 | 이유 | 결정 후 구현 가능 |
| --- | --- | --- | --- |
| `skeleton3d.v1` 재사용 범위 | raw input 또는 import source로만 사용하고, rack artifact는 `rack_motion.*.v1`로 새로 생성한다. | 기존 viewer/API를 깨지 않고 rack-domain ownership을 확보한다. | skeleton3d-to-rack reconstruction mapper |
| public rack artifact shape | sparse JSON record batch를 우선 사용한다. dense array는 internal adapter로 보류한다. | 현재 FastAPI/React/paged artifact 구조와 맞다. | observation/reconstruction repository |
| target namespace | `person.*`, `barbell.*`, `rack.*` prefix를 사용한다. MediaPipe name/index는 source metadata와 debug로 둔다. Public person targets는 물리의학적 자세 분석을 고려한 curated anatomical target set으로 정의한다. | person joint와 rack/bar domain target 혼동을 막으면서 head/neck, hand/wrist, foot/stance, bilateral posture 분석을 보존한다. | target id validation, curated target set validation |
| session id | rack motion artifact에는 `sessionId`를 필수로 두고, source job id는 `sourceRefs`에 둔다. | backend job id를 artifact domain id로 과사용하지 않는다. | session manifest/envelope |
| coordinate policy | `panoptic_world_cm`은 input/source coordinate label, rack artifact는 `capture_world`/`rack_world`로 명시한다. Public 3D canonical numeric unit은 `meter`, UI/report 표시 단위는 metric catalog로 분리한다. | dataset-specific 좌표명을 domain 좌표로 승격하지 않고, 물리량 계산과 물리의학적 표시 단위를 분리한다. | coordinate-space manifest, unit/display policy |
| first quality catalog | sync, observation visibility, reconstruction reprojection/failure reason만 먼저 catalog화한다. | 현재 구현에서 실제 산출 가능한 metric이다. | quality metric mapper |
| rack-world availability | rack-world가 없으면 rack metrics/events는 생성하지 않고 `not_computed` diagnostic으로 남긴다. | fake rack analysis를 방지한다. | safe incomplete artifact |
| single camera policy | preview/coarse estimate는 가능하더라도 valid calibrated 3D로 표시하지 않는다. | schema validation과 #32 요구가 이미 맞는다. | degraded mode handling |
| frontend scope | `07-frontend-rack-visualization-design.md` Stage 1 `Rack Volume Fixture Viewer`를 first scope로 둔다. | MVP v2 landing-page demo 수준의 visible rack motion experience를 제공하되, 없는 rack/bar metric을 완성된 분석처럼 보이지 않게 한다. | `RackMotionViewer` Stage 1 implementation |
| diagnostic visibility | 주요 diagnostic은 frontend에서 토글, drawer, inspector, diagnostic mode로 접근 가능하게 한다. | MVP v2 시연과 검증에는 diagnostic 접근성이 필요하지만 기본 화면은 readable summary로 유지해야 한다. | diagnostic mode, provenance drawer, quality detail |
| schema migration | 새 `rack_motion.*.v1` artifact부터 explicit `schemaVersion`과 adapter/importer 정책을 적용한다. 기존 2D skeleton artifact는 강제 migration하지 않는다. | 새 contract는 안정적으로 시작하고 기존 MVP v2 경로는 깨지지 않게 한다. | rack motion artifact envelope |

## 현재 보류해도 되는 질문
- commercial distribution, final product license, public dataset publication policy.
- barbell endpoint detector 방식 선택. 단, `barbell.left_endpoint`/`barbell.right_endpoint` contract, provenance, quality, synthetic/manual/imported fixture는 먼저 확정한다.
- J-cup/contact threshold와 hysteresis. rack-world/bar endpoint trajectory가 먼저 필요하다.
- velocity/acceleration persistence. temporal artifact가 먼저 필요하다.
- multi-person support. MVP v2 rack motion은 single lifter required로 제한하는 편이 현실적이다.
- camera contribution weight. 현재 triangulation service는 weighted contribution을 생산하지 않는다.

## 현재 막히면 안 되는 작업
- `Observation2D` producer/store 설계.
- `skeleton3d.v1` joint를 `ReconstructionTarget3D`로 변환하는 mapper 설계.
- rack motion envelope/session id/sourceRefs/coordinateRefs 설계.
- synthetic rack anchor/support zone fixture와 schema validation.
- sync/reconstruction quality metric catalog 초안.
- `07-frontend-rack-visualization-design.md` Stage 1 `RackMotionViewer` 설계 구체화.

## 동기화 규칙
| 상황 | 처리 |
| --- | --- |
| 원본 `06_open_questions_ko.md`가 수정됨 | 새 질문, 해결된 질문, 제거된 질문을 이 문서의 매트릭스에 반영한다. |
| 사용자가 방향을 결정함 | 권장 분류를 채택, 보류, 제외, 해결 중 하나로 갱신하고 근거를 짧게 기록한다. |
| `requirements-adoption-review`의 01-05 문서 방향이 바뀜 | 이 문서의 최소 결정표와 보류 질문을 함께 갱신한다. |
| 구현 문서로 승격함 | 해결된 질문은 implementation task나 non-goal로 이동하고, 남은 질문은 risk로 분리한다. |
