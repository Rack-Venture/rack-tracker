# Rack-Tracker 요구사항 채택 검토

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/05_rack_tracker_requirements_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/05-rack-tracker-requirements.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
## 문서 관계
- 부모 문서: `../rack-motion-adoption-design.md`
- 원본 참조 문서: `../../32-feat-rack-motion-pipeline-requirements/05_rack_tracker_requirements_ko.md`
- 원본 제목: `Rack-Tracker 요구사항`
- 상태: 사용자 채택 결정 반영 중

## 검토 목적
이 문서는 #32의 rack-tracker 전용 요구사항을 현재 MVP v2 제품 방향, frontend/backend 구현, 3D synthesis 실험, `rack_motion.*.v1` schema와 비교한다. 특히 현재 시스템이 잘하는 `person skeleton extraction/reconstruction`과 아직 없는 `barbell/rack domain entity`를 분리해, 우리 프로젝트에 맞는 구현 우선순위를 정한다.

## 현재 domain 구현 현황

### Person skeleton
- 2D: MediaPipe pose 33 landmarks를 `PoseInferenceService`가 생성하고, `SkeletonMapperService`가 job artifact로 저장한다.
- 3D: `Skeleton3DSynthesizer`가 두 개의 2D skeleton job을 frame align 후 `skeleton3d.v1.frames[].joints[]`로 합성한다.
- Frontend: `SkeletonViewer`, `LiveSyncSection`, `Skeleton3DSynthesisSection`, `ThreeJSSkeleton`이 person skeleton을 표시한다.

### Barbell
- 실제 barbell endpoint detector 또는 mapper는 없다.
- `backend/service/analysis_features.py`에는 shoulder/elbow/wrist 기반 2D `bar_path_x`, `bar_y`, `bar_confidence` proxy가 있다. 이것은 squat legacy/analysis proxy이며 실제 barbell endpoint가 아니다.
- `backend/schema/rack_motion.py`에는 `BarbellEntity`와 left/right endpoint shape가 있지만 producer가 없다.

### Rack
- 실제 rack anchor acquisition, rack config, J-cup/safety pin detector, support-contact analyzer는 없다.
- `backend/schema/rack_motion.py`의 `RackAnchor`와 `SupportZone`은 static rack feature를 담을 수 있고, `RackMotionFrame`은 support zone anchor reference를 검증한다.

### Events and reps
- 기존 `analysis_reps.py`는 2D hip/knee trajectory 기반 squat rep segmentation이다.
- 기존 `analysis_events.py`는 pose lost/recovered와 rep start/bottom/end event를 만든다.
- rack support-contact, unrack/rerack, bar-near-J-cup, safety-pin proximity event는 없다.

## #32 rack-domain 요구와 현재 시스템 차이
| #32 요구 항목 | #32 요구 내용 | MVP v2 현재 대응 | 현재 시스템과의 차이 또는 부적합 | 권장 방향 | 후속 산출물 |
| --- | --- | --- | --- | --- | --- |
| Rack Anchor | session별 `rack_anchor_set`을 두고 anchor id, label, space, position, quality, provenance를 저장한다. | `RackAnchor` schema가 있고 `SupportZone`이 anchor id reference를 검증한다. service/repository는 없다. | schema는 방향이 맞지만 anchor acquisition method, rack dimensions, `capture_to_rack` transform은 없다. | 채택 결정. `rack_alignment`는 camera calibration과 분리된 user-authored/imported TOML 또는 JSON artifact로 두고, MVP v2의 1차 source는 manual/measured rack dimensions와 anchors다. | rack config schema, anchor acquisition policy, synthetic anchor fixture |
| Barbell Endpoint | left/right endpoint, derived center, axis, endpoint quality, reconstruction mode를 갖는다. | `BarbellEntity` schema가 endpoint와 center를 담을 수 있다. 실제 detector/mapper는 없다. 기존 2D bar proxy는 endpoint가 아니다. | current person skeleton만으로 endpoint를 안정적으로 만들 수 없다. proxy를 endpoint로 승격하면 metric 의미가 틀린다. | 채택 결정. `barbell.left_endpoint`/`barbell.right_endpoint` contract, provenance, quality, synthetic/manual/imported fixture를 먼저 확정한다. MVP v2 first slice에서는 automatic detector를 구현하지 않는다. | barbell endpoint contract, endpoint provenance/quality fixture |
| Person Keypoint Subset | rack/bar analysis에 필요한 lifter point subset을 target schema로 정의한다. | MediaPipe pose 33 전체가 저장되고 3D 합성된다. frontend key joint table은 일부 joint만 표시한다. | full MediaPipe landmark list와 rack-domain person target subset이 분리되지 않았다. face landmark 등 불필요 target도 artifact에 포함된다. | 채택 결정. `person.*`, `barbell.*`, `rack.*` namespace를 사용하고 public rack artifact는 MediaPipe 33 전체가 아니라 curated anatomical target set을 노출한다. MediaPipe index/name은 provenance/debug로 보존한다. | person target subset policy |
| Multi-Camera Keypoint Reconstruction | synchronized multi-camera 2D observation을 weighted homogeneous least squares 등 일반 CV 방식으로 3D 재구성하고 diagnostics를 남긴다. | `TriangulationService`가 2-view OpenCV triangulation, reprojection error, camera depth, failure reason을 구현한다. tests도 synthetic camera fixture를 쓴다. | 현재는 두 카메라, MediaPipe pose joint, fixed thresholds 중심이다. weighted multi-view, outlier retriangulation, arbitrary target reconstruction은 없다. | 채택 결정. MVP v2 rack motion의 valid 3D/reconstruction path는 2-camera 이상만 허용하고, single-camera는 preview/degraded diagnostic으로만 둔다. | target-agnostic reconstruction interface |
| Safety Pin 및 J-Cup Event | support zone proximity, support-contact candidate, unrack/rerack candidate를 frame range와 quality/policy로 저장한다. | `SupportZone` schema만 있다. event analyzer는 pose lost/rep events만 만든다. | rack-world, support zone geometry, bar endpoint가 없으므로 event를 계산할 수 없다. | 보류 권장. rack anchor + bar endpoint + temporal continuity가 생긴 뒤 구현한다. | support event schema and analyzer |
| RackWorldSpace Output | analysis-ready output은 `space_id=RackWorldSpace`, unit, timestamp, entity id, provenance, quality, transform id를 가진다. | `ReconstructionTarget3D`와 rack entity schema는 rack_world를 허용/요구한다. 실제 output은 없다. `skeleton3d.v1`은 `panoptic_world_cm`이다. | current 3D output은 rack-world가 아니고 transform id도 없다. | 우선 채택 권장. rack analyzer output은 rack-world 없이는 valid로 만들지 않는 정책을 세운다. | rack-world output contract |
| Domain Policy | lift type, target requirement, camera count, interpolation span, event threshold/hysteresis, single-camera limitation, blocking/warning behavior를 정의한다. | `SynthesisThresholds`, squat analysis constants, `QualityMetric.policyId` validation이 흩어져 있다. rack-domain policy file은 없다. | current constants는 rack-domain policy가 아니고, 일부는 2D squat legacy에 묶여 있다. | 채택 결정. policy catalog는 2-camera 이상 valid reconstruction, timestamp-based partial sync warning, single-camera degraded diagnostic, metric blocking/warning behavior를 우선 담는다. | rack motion policy catalog |
| Endpoint asymmetry | bar endpoint height/velocity difference와 tilt를 rack-world에서 계산한다. | Barbell endpoint producer가 없다. | current `bar_path_x` proxy로 endpoint asymmetry를 계산할 수 없다. | 보류 권장. endpoint source 확보 후 채택한다. | asymmetry metric design |
| Rack proximity | rack anchor/support zone 기준 bar/person proximity를 계산한다. | support zone schema만 있다. | rack-world transform과 bar endpoint가 없어 계산 불가. | 보류 권장. anchor + endpoint 이후 구현한다. | rack proximity analyzer |
| Person identity | multi-person 상황 전까지 lifter identity policy를 명시한다. | MediaPipe `num_poses=1` 기본이고 frontend/backend는 단일 athlete 가정에 가깝다. | 현재 multi-person support가 없다. 이를 암묵적 한계로 두면 later metric이 흔들린다. | 채택 권장. MVP v2 rack motion은 single lifter required로 명시한다. | identity scope decision |

## 우리 프로젝트에 안 맞는 부분
- 기존 2D squat pipeline을 rack motion analyzer로 그대로 확장하는 것은 맞지 않는다. 해당 pipeline은 normalized 2D pose와 squat-specific feature에 묶여 있다.
- `analysis_features.py`의 barbell proxy를 실제 barbell endpoint, bar tilt, rack proximity metric의 input으로 사용하면 안 된다.
- support-contact event를 image-space distance로 계산하면 rack camera angle에 따라 의미가 달라진다. rack-world가 먼저 필요하다.
- person skeleton full 33 landmarks를 rack-domain target schema로 그대로 노출하면 domain target namespace가 불명확해진다.
- single-camera estimate를 calibrated multi-camera 3D처럼 보여주면 안 된다. 현재 `ReconstructionTarget3D`가 `single_camera_estimate`를 valid로 금지하는 방향은 유지해야 한다.

## 우선 반영하면 좋은 부분
- 첫 domain slice는 `rack_anchor_set`과 `person keypoint subset`을 문서/fixture로 확정하는 것이 가장 안전하다.
- `skeleton3d.v1` person joints를 `ReconstructionTarget3D`로 import하는 mapper를 만들고, target namespace를 rack-domain 이름으로 바꾼다.
- rack-world가 없을 때는 rack-domain metric을 생성하지 않고 `not_computed` 품질 metric이나 missing alignment diagnostic을 남긴다.
- barbell endpoint는 source가 확정될 때까지 synthetic/manual fixture 기반 validation만 둔다.
- domain policy catalog에 single lifter assumption, required cameras, allowed degraded mode, metric blocking/warning behavior를 먼저 둔다.

## MVP v2 권장 구현 순서
| 순서 | 구현 단위 | 이유 | 입력 | 출력 |
| --- | --- | --- | --- | --- |
| 1 | target/entity namespace policy | 기존 MediaPipe joint와 rack/bar target을 섞지 않기 위함 | #32 requirements, current skeleton artifact | target id naming policy |
| 2 | skeleton3d-to-reconstruction mapper | 이미 있는 3D person synthesis를 rack schema로 안전하게 연결 | `skeleton3d.v1` | `ReconstructionTarget3D` record batch |
| 3 | rack anchor/config synthetic fixture | rack-world transform 전제와 validation을 먼저 고정 | synthetic rack dimensions/anchors | `RackAnchor`, `SupportZone`, quality metric |
| 4 | rack-world alignment placeholder | rack-world 없음을 명시적으로 다루기 위함 | capture world + rack config | `not_computed` or alignment artifact |
| 5 | barbell endpoint contract/provenance fixture | detector보다 먼저 endpoint contract, provenance, quality, synthetic/manual/imported fixture를 확정해야 downstream metric이 의미를 가짐 | `barbell.left_endpoint`/`barbell.right_endpoint` decision | endpoint contract and fixture plan |
| 6 | support/contact/rerack analyzer | endpoint와 rack-world 이후에만 의미 있음 | RackMotionFrame trajectory | event candidates |

## 동기화 규칙
| 상황 | 처리 |
| --- | --- |
| 원본 `05_rack_tracker_requirements_ko.md`가 수정됨 | rack-specific event, metric, entity 요구 변경 여부를 이 문서에 반영한다. |
| `backend/service/analysis_*` 로직이 rack motion과 연결됨 | 2D legacy analysis와 rack-domain analysis의 경계가 유지되는지 이 문서에 반영한다. |
| `backend/schema/rack_motion.py`가 person entity 또는 event shape를 추가함 | 현재 domain 구현 현황과 구현 순서표를 갱신한다. |
| 제품/분석 우선순위가 결정됨 | 채택 항목을 MVP v2 구현 순서로 재배열한다. |
| 구현 문서로 승격함 | 각 rack-domain 요구의 input artifact, output artifact, validation 기준을 명시한다. |
