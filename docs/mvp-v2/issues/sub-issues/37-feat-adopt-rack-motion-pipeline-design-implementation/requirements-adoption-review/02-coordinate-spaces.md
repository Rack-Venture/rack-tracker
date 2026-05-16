# 좌표 공간 채택 검토

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/02_coordinate_spaces_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/02-coordinate-spaces.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
## 문서 관계
- 부모 문서: `../rack-motion-adoption-design.md`
- 원본 참조 문서: `../../32-feat-rack-motion-pipeline-requirements/02_coordinate_spaces_ko.md`
- 원본 제목: `좌표 공간`
- 상태: 사용자 채택 결정 반영 중

## 검토 목적
이 문서는 #32의 좌표 공간 정의를 MVP v2의 현재 2D landmark, calibration, 3D synthesis, frontend viewer, rack motion schema와 비교한다. 핵심은 `skeleton3d.v1` 실험 좌표를 rack-domain 분석 좌표로 착각하지 않도록, source pixel, camera space, capture world, rack world, display transform을 분리하는 것이다.

## 현재 좌표 사용 현황

### 2D source와 detector 좌표
- `backend/service/pose_inference.py`는 MediaPipe landmark를 normalized `x`, `y`, `z`로 저장한다. 이 값은 source image pixel이 아니다.
- `backend/service/skeleton_mapper.py`는 skeleton artifact에 `imageCoordinateSpace.landmarkSpace = mediapipe_normalized_image`와 `pixelBasis.width/height`를 기록한다.
- `backend/service/landmark_observation.py`는 synthesis 시점에 normalized landmark에 image width/height를 곱해 pixel coordinate를 만든다.
- `backend/schema/rack_motion.py`의 `Observation2D`는 `spaceId="source_image_pixels"`만 허용한다. 즉 schema 방향은 #32와 맞지만 producer/store는 아직 없다.

### 3D synthesis 좌표
- `backend/schema/synthesis.py`는 `SynthesisCoordinateSystem = "panoptic_world_cm"`만 허용한다.
- `backend/service/camera_calibration.py`의 `CameraModel`은 Panoptic calibration file의 `K`, `distCoef`, `R`, `t`를 사용하고 `coordinate_system="panoptic_world_cm"`을 기본값으로 둔다.
- `backend/service/triangulation.py`는 camera normalized projection matrix로 3D point를 만들고, `project_world_point()`로 reprojection error를 계산한다.
- `backend/service/skeleton_3d_synthesizer.py`는 `skeleton3d.v1.synthesisInfo.coordinateSystem`에 `panoptic_world_cm`을 기록하고, `viewHint`로 frontend display orientation을 전달한다.

### Frontend display 좌표
- `frontend/src/features/analysis-session/adapters.js`는 `skeleton3d.v1` joint를 `metric3d=true` landmark로 변환한다.
- `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx`는 `viewHint`와 joint bounds를 사용해 Three.js display coordinate로 다시 scale/center한다.
- 이 display transform은 사람에게 보기 좋게 렌더링하기 위한 변환이며, `RackWorldSpace` 또는 analysis coordinate transform이 아니다.

### Rack motion schema 좌표
- `backend/schema/rack_motion.py`는 `source_image_pixels`, `detector_input_pixels`, `camera_space`, `capture_world`, `rack_world` literal을 가진다.
- `ReconstructionTarget3D`는 `capture_world` 또는 `rack_world`를 허용하고 unit을 요구한다.
- `RackAnchor`, `SupportZone`, `BarbellEntity`, `RackMotionFrame`은 rack-world 전제를 갖지만 아직 producer가 없다.

### Rack-mounted camera 해석
- 실제 제품에서 카메라가 파워랙 또는 고정 mock rig에 장착되면 camera geometry와 rack real world가 물리적으로 안정적으로 묶일 수 있다.
- 그래도 artifact 계약에서는 `CameraSpace`, `CaptureWorldSpace`, `RackWorldSpace`를 같은 좌표계로 암묵 병합하지 않는다. 카메라 마운트, 렌즈, 해상도, rack 치수, rack anchor, floor 기준이 바뀌면 같은 capture calibration이라도 새 rack alignment가 필요할 수 있기 때문이다.
- 고정 설치 모드에서 `CaptureWorldSpace`와 `RackWorldSpace`가 같은 원점, 축, 단위를 쓰도록 캘리브레이션할 수는 있다. 이 경우에도 `capture_to_rack`은 생략하지 말고 identity 또는 calibrated rigid transform으로 명시하고, calibration id와 rack alignment id를 별도로 추적한다.
- 따라서 `CameraSpace`는 계속 pixel-to-ray, depth, reprojection diagnostic의 근거로 사용하고, analysis-ready 3D output은 `capture_world` 또는 명시된 `rack_world`에 둔다.

### 개발용 Panoptic 가상 파워랙 카메라
- 현재 개발 fixture는 Panoptic Studio `171204_pose1`의 HD camera `00_11`과 `00_21` 영상을 사용해 파워랙 좌상단/우상단 고정 카메라 스트리밍 환경을 가장한다.
- 여기서 `11`, `21`은 배열 인덱스가 아니라 calibration camera name의 node 식별자다. 개발 입력은 `hd_00_11_2min.mp4` -> `name="00_11"`, `panel=0`, `node=11`, `type="hd"`와 `hd_00_21_2min.mp4` -> `name="00_21"`, `panel=0`, `node=21`, `type="hd"`로 매핑한다.
- 두 카메라는 모두 `1920x1080` source image를 사용한다. `00_11` intrinsics는 `K=[[1494.03,0,934.225],[0,1490.4,547.2],[0,0,1]]`, `distCoef=[-0.262456,0.195852,-0.000218069,0.000249353,-0.0304978]`다.
- `00_21` intrinsics는 `K=[[1397.27,0,932.173],[0,1393.45,563.453],[0,0,1]]`, `distCoef=[-0.28791,0.186278,-0.000124931,0.0000841097,-0.050319]`다.
- `calibration_171204_pose1.json`의 extrinsics 기준 camera center는 `panoptic_world_cm`에서 `00_11 ~= (-143.014,-239.688,-205.680) cm`, `00_21 ~= (-241.532,-239.578,75.369) cm`이며 baseline은 약 `297.8 cm`다.
- 이 fixture의 정확한 capture calibration은 `PanopticCaptureRig171204Pose1` 같은 개발용 calibration bundle로 먼저 정의한다. 그 위에 별도의 `VirtualPowerRackDevRig` mapping을 두어 `00_11`과 `00_21`에 `rack_top_left`/`rack_top_right` 같은 logical mount role을 부여한다.
- logical mount role은 제품 카메라 역할을 흉내 내는 개발 가정일 뿐 실제 rack geometry 또는 `RackWorldSpace` 정의가 아니다. 따라서 `panoptic_world_cm`는 `capture_world`로 import하고, rack anchor가 없는 동안 `capture_to_rack`은 `not_computed` 또는 명시적인 dev-only identity assumption으로 기록한다.

### RackWorldSpace 입력 artifact 확장
- 다음 개발 단계에서 실제 파워랙 환경을 구성할 예정이므로 `RackWorldSpace`는 코드 상수나 hard-coded viewer transform으로 만들지 않고 별도 TOML 또는 JSON 입력 artifact로 확장 가능하게 둔다.
- 파일 책임은 `camera_calibration`과 `rack_alignment`로 분리한다. `camera_calibration`은 camera intrinsics, distortion, image size, `camera_to_capture` 또는 `capture_to_camera`, capture-world unit/axis convention을 소유한다. `rack_alignment`는 rack dimensions, rack anchors, floor/vertical reference, `capture_to_rack` 또는 `rack_to_capture`, alignment quality/provenance를 소유한다.
- Panoptic 개발 단계에서는 예를 들어 `panoptic_171204_pose1_camera_bundle.toml`이 `00_11`/`00_21`의 정확한 calibration을 담고, `virtual_power_rack_dev_alignment.toml`이 logical camera role과 `capture_to_rack.status="not_computed"` 또는 `status="dev_assumption"`을 담는 구조가 적합하다.
- 실제 파워랙 단계에서는 같은 `rack_alignment` schema에 measured rack width/depth/height, origin definition, axis definition, anchor observations, calibrated rigid 또는 similarity transform을 채운다.
- 이 분리는 Panoptic fixture, 개발용 mock rack, 실제 product rack을 같은 pipeline contract로 다루기 위한 확장 지점이다. artifact consumer는 `rack_world`가 필요할 때 rack alignment id와 상태를 확인해야 하며, `not_computed` 또는 `dev_assumption` 상태를 production-grade rack analysis로 승격하면 안 된다.

## #32 좌표 요구와 현재 시스템 차이
| #32 좌표 항목 | #32 요구 내용 | MVP v2 현재 대응 | 현재 시스템과의 차이 또는 부적합 | 권장 방향 | 후속 산출물 |
| --- | --- | --- | --- | --- | --- |
| `ImageSpace` / source image pixel | decoding 이후 원본 이미지 픽셀 좌표를 persisted 2D observation의 기본으로 사용한다. | skeleton artifact는 MediaPipe normalized landmark를 저장하고, synthesis 중 `LandmarkObservationBuilder`가 pixel로 변환한다. `Observation2D` schema는 source pixel만 허용한다. | 현재 영구 2D artifact는 source pixel이 아니라 normalized landmark다. pixel 변환은 재구성 중 메모리에서만 발생한다. | 채택 권장. rack motion observation store는 source-image pixel을 공식 좌표로 삼고, 기존 skeleton normalized coordinate는 input provenance로만 둔다. | skeleton-to-`Observation2D` mapper, source image size validation |
| `PreprocessedImageSpace` | detector input resize/crop/padding 이후 좌표이며 저장 관측의 기본 좌표가 되어서는 안 된다. | MediaPipe adapter 내부 전처리는 artifact에 드러나지 않는다. `imageCoordinateSpace.preprocessTransform`은 `None`이다. | detector input transform을 복원할 수 없으므로 #32의 reversible transform 계약을 지금 만족하지 못한다. | 보류 권장. 현재 MediaPipe pose path에서는 source pixel observation을 먼저 만들고, detector-specific transform은 bar/rack detector 도입 시 추가한다. | `PreprocessTransform` schema와 adapter-private diagnostics |
| `CameraSpace` | camera optical center 기준 3D coordinate/ray/depth를 camera id와 calibration id로 추적한다. | `CameraModel.undistort_pixel_to_normalized()`, camera depth check, debug ray 계산이 camera geometry를 사용한다. `TriangulatedJoint.camera_depth_*`가 있다. | camera-space 값은 diagnostic으로만 존재하고 독립 artifact가 아니다. camera convention도 rack-tracker schema로 명시되지 않고 Panoptic file convention에 묶여 있다. | 부분 채택 권장. public rack artifact에는 camera depth, projection convention, camera id를 diagnostic으로 남기되 camera-space point store는 아직 만들지 않는다. | camera diagnostic field policy |
| `CaptureWorldSpace` | calibration이 정의하는 공통 reconstruction space이며 rack-centered라고 가정하지 않는다. | `panoptic_world_cm`가 사실상 raw reconstruction world다. `skeleton3d.v1` output과 debug report가 이 좌표를 사용한다. | 이름이 dataset-specific이고 rack-tracker-owned `capture_world`가 아니다. unit도 이름에 암시되어 있으며 schema field로 강제되지 않는다. | 채택 결정. `panoptic_world_cm`은 import/source coordinate label과 provenance로 보존하고, public `rack_motion.*.v1` 3D 좌표의 canonical numeric unit은 `meter`로 정규화한다. UI/report 표시 단위는 metric catalog에서 별도로 정한다. | capture-world wrapper, unit/display policy |
| `RackWorldSpace` | rack origin, axes, dimensions, floor/vertical reference, `capture_to_rack` transform으로 정의되는 analysis coordinate다. | `rack_motion.py` literal과 rack entity schema만 있다. 실제 rack anchor acquisition, rack config, transform service는 없다. | frontend viewer는 rack-world를 만들지 않는다. skeleton joint bounds로 scale/center하는 행위도 rack-world 정의가 아니다. | 채택 결정. `rack_alignment`는 `camera_calibration`과 분리된 user-authored/imported TOML 또는 JSON artifact로 두고, 1차 source는 manual/measured rack dimensions와 anchors다. rack analysis output은 rack-world 없이는 valid로 만들지 않는다. | rack config schema, rack anchor acquisition policy, `capture_to_rack` artifact |
| Skeleton entity | skeleton은 `RackWorldSpace`를 정의하지 않고 그 안에서 움직이는 dynamic entity다. | 현재 `skeleton3d.v1` viewer가 skeleton bounds와 `viewHint`로 display frame을 만든다. | skeleton bounds를 rack origin/floor/axis로 사용하면 #32 금지 조건을 위반한다. 현재 code comment도 ground/up은 coordinate system hint에서 오며 joint에서 추정하지 않는다고 적고 있다. | 채택 권장. skeleton은 rack-world input entity일 뿐 world definition source가 아니라고 문서와 mapper에 고정한다. | mapper non-goal note, validation rule |
| Pixel-to-ray 재구성 | pixel -> undistort -> camera ray -> capture world ray -> triangulation -> optional rack transform 흐름을 명시한다. | `LandmarkObservationBuilder` pixel 변환, `CameraModel.undistort_pixel_to_normalized`, `cv2.triangulatePoints`, reprojection scoring이 있다. | 현재 implementation은 2-view pose joint path에 한정되고, public artifact에 ray/projection provenance가 완전하게 남지는 않는다. | 부분 채택 권장. 기존 triangulation debug를 보강해 pixel-to-ray 흐름의 주요 id와 failure reason을 rack schema로 옮긴다. | reconstruction debug-to-rack mapping |
| Transform 방향 | `image_to_preprocessed`, `preprocessed_to_image`, `camera_to_capture`, `capture_to_camera`, `capture_to_rack`, `rack_to_capture`를 명시한다. | calibration file의 `R`, `t`를 사용하지만 canonical transform field는 없다. `CameraModel.project_world_point()`와 debug ray 계산이 내부적으로 direction을 사용한다. | 현재 transform 방향은 code convention과 debug string에 흩어져 있다. artifact consumer가 안전하게 역변환을 알 수 없다. | 채택 권장. rack-tracker-owned calibration/rack alignment artifact에는 transform direction을 field로 강제한다. | transform direction policy |
| 단위 선언 | 좌표 값은 unit이 없으면 유효하지 않다. | `synthesisInfo.coordinateSystem="panoptic_world_cm"`가 단위를 이름에 암시한다. `ReconstructionTarget3D.unit`은 필수다. | 현재 `skeleton3d.v1` frames의 joint position에는 per-point unit field가 없다. rack schema는 더 엄격하지만 producer가 없다. | 채택 결정. public `rack_motion.*.v1` 3D 좌표는 `meter`로 저장하고, source unit과 cm/mm 등 표시 단위는 provenance 및 metric catalog에 분리한다. | unit/display policy |
| 좌표계 provenance | `space_id`, unit, axis convention, transform source를 provenance로 남긴다. | `synthesisInfo.calibrationRef`, `sourceBindings`, `debugReport.triangulationTraceDebug.projectionConvention`, `viewHint`가 일부 역할을 한다. | provenance가 `skeleton3d.v1` debug 중심이고 rack motion artifact envelope에는 없다. | 채택 권장. coordinate space manifest 또는 session manifest에 provenance를 묶는다. | coordinate-space manifest |

## 우리 프로젝트에 안 맞는 해석
- `panoptic_world_cm`를 그대로 `RackWorldSpace`로 부르는 것은 맞지 않는다. 이 좌표는 calibration dataset의 capture world이지 rack-centered analysis coordinate가 아니다.
- Three.js에서 scale/center/floor를 잡는 display transform은 domain transform이 아니다. 이 값을 metric 계산이나 event 계산에 재사용하면 안 된다.
- MediaPipe normalized landmark를 source image pixel observation으로 간주하면 안 된다. source pixel은 width/height와 transform provenance가 함께 있어야 한다.
- camera calibration file에 rack dimensions와 rack anchor를 섞는 방향은 피한다. #32와 현재 #37 설계 모두 camera calibration과 rack alignment를 분리하는 쪽이 맞다.
- rack-mounted setup에서 camera geometry와 rack real world가 일치하도록 설계했더라도 이를 파일 경로나 설치 관례로 암시하면 안 된다. `capture_to_rack`이 identity에 가까운 경우도 명시적 transform과 alignment provenance로 기록한다.
- skeleton trajectory로 floor, vertical axis, rack origin을 자동 정의하는 방식은 rack motion pipeline 요구와 맞지 않는다.

## 우선 반영하면 좋은 부분
- `Observation2D.spaceId="source_image_pixels"` 정책은 유지하고, 기존 skeleton normalized coordinate에서 pixel observation을 생성하는 mapper를 만든다.
- `skeleton3d.v1`의 `panoptic_world_cm` output은 source coordinate provenance로 보존하고, public rack motion 3D output은 `meter` 단위의 `capture_world` 또는 `rack_world` record로 변환한다.
- 모든 rack motion 3D record에 `spaceId`, `unit`, `calibrationId`, 필요 시 `rackAlignmentId`를 둔다.
- `rack_world` artifact는 `RackAnchor`/`SupportZone`/rack config가 있을 때만 valid로 만들고, 없을 때는 `not_computed` 또는 degraded로 기록한다.
- `RackWorldSpace`는 별도 TOML/JSON `rack_alignment` 입력 artifact로 확장 가능하게 두고, camera calibration bundle과 같은 파일에 섞지 않는다.
- rack-mounted camera mode는 후속 설계에서 별도 policy로 다루되, 같은 물리 설치를 사용하더라도 `CalibrationBundle`과 rack alignment/config 산출물을 분리한다.
- frontend에는 rack-world가 생기기 전까지 현재 3D skeleton viewer가 "3D synthesis inspection"임을 유지하고, rack analysis UI로 오해될 output을 추가하지 않는다.

## 동기화 규칙
| 상황 | 처리 |
| --- | --- |
| 원본 `02_coordinate_spaces_ko.md`가 수정됨 | 좌표 공간 명칭, 단위, transform 정책 변경 여부를 이 문서에 반영한다. |
| `backend/schema/synthesis.py`의 coordinate system이 바뀜 | `panoptic_world_cm`와 `capture_world` 매핑 설명을 갱신한다. |
| `backend/schema/rack_motion.py`의 coordinate literal 또는 unit validation이 바뀜 | 이 문서의 rack motion schema 좌표 현황과 채택 매트릭스를 갱신한다. |
| frontend viewer transform이 바뀜 | display transform과 domain transform의 분리 여부를 다시 확인한다. |
| 좌표계 채택 결정이 내려짐 | MVP v2 artifact별 `spaceId`, `unit`, provenance, transform 방향을 확정한다. |
