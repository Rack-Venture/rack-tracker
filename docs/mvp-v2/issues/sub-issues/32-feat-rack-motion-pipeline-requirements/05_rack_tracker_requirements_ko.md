# Rack-Tracker 요구사항

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/05_rack_tracker_requirements_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/05-rack-tracker-requirements.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
rack-tracker는 자체 target schema와 entity model을 정의해야 한다. 조사 대상 프로젝트의 일반 human skeleton hierarchy를 복사해서는 안 된다.

## Rack Anchor

목적: 일반 capture-world point를 rack-centered analysis coordinate로 바꾸는 static reference geometry를 정의한다.

필수 계약:

- session마다 최소 하나의 `rack_anchor_set`.
- 각 anchor는 `anchor_id`, `label`, `space_id`, `x`, `y`, `z`, `quality`, source provenance를 가진다.
- Anchor observation은 manual entry, calibration capture, detector output, imported measurement에서 올 수 있다.
- Anchor set은 전체 session 동안 static인지 frame-varying인지 선언해야 한다.
- `CaptureWorldSpace`에서 `RackWorldSpace`로 가는 transform은 어떤 anchor가 사용되었는지 명시해야 한다.

권장 anchor category:

- rack centerline reference
- floor-plane reference
- left/right upright reference
- front/back depth reference
- J-cup 또는 safety-pin location 같은 support feature reference

실패 조건:

- origin과 axis를 정의하기에 anchor가 너무 적음.
- anchor unit mismatch.
- left/right 또는 front/back label이 모호함.
- alignment quality가 계산되지 않음.

## Barbell Endpoint

목적: bar path, bar tilt, rack distance, support-contact event를 지원한다.

필수 target:

- `bar_left_endpoint`
- `bar_right_endpoint`
- derived `bar_center`
- derived `bar_axis`

요구사항:

- Endpoint는 image left/right가 아니라 `RackWorldSpace` 기준으로 side-labeled되어야 한다.
- 각 endpoint에는 position, quality, visibility summary, reconstruction mode가 필요하다.
- `bar_center`는 양쪽 endpoint가 모두 있을 때 endpoint에서 derive해야 한다. 그렇지 않으면 degraded status를 가져야 한다.
- Bar tilt는 rack space의 endpoint height difference와 endpoint separation에서 계산해야 한다.
- Bar-to-rack distance는 image-space distance가 아니라 `RackWorldSpace`를 사용해야 한다.

실패 조건:

- 하나의 endpoint만 사용 가능하고 명시적 single-endpoint policy가 없음.
- endpoint side label이 tracked identity policy 없이 swap됨.
- bar geometry가 설정된 physical constraint를 위반함.

## Person Keypoint Subset

목적: rack과 barbell analysis에 필요한 lifter point만 추적한다.

권장 최소 category:

- wrist and hand contact region
- elbow
- shoulder
- torso reference
- hip
- knee
- ankle 또는 foot reference
- rack clearance 또는 pose context가 필요할 때 head 또는 neck reference

요구사항:

- Keypoint는 person body convention에서 side-labeled되어야 하며 `RackWorldSpace`로 일관되게 mapping되어야 한다.
- Target schema는 optional keypoint 누락이 전체 analysis를 무효화하지 않도록 허용해야 한다.
- Rep counting 또는 event inference 전에 person identity가 frame 전반에서 안정적이어야 한다.
- Person keypoint는 같은 model로 감지되더라도 barbell 및 rack target과 분리되어야 한다.

실패 조건:

- 여러 사람이 있고 lifter identity가 해결되지 않음.
- 선택한 analysis에 필요한 keypoint가 설정된 span 전반에서 누락됨.
- rack distance 또는 height에 의존하는 metric에서 keypoint space가 `RackWorldSpace`가 아님.

## Multi-Camera Keypoint Reconstruction

목적: synchronized multi-camera 2D observation을 rack-tracker 소유 contract와 표준 weighted homogeneous least-squares triangulation으로 3D keypoint로 재구성한다.

Clean-room 요구사항:

- 구현은 새로운 rack-tracker 코드로 작성해야 하며, 조사 대상 프로젝트의 source code, function name, class name, file layout, threshold default, internal control flow, test, sample data, generated artifact를 복사해서는 안 된다.
- 구현은 weighted DLT, homogeneous least squares, SVD 또는 동등한 linear least-squares solver, reprojection error measurement, policy-driven outlier rejection 같은 일반 computer vision 개념을 사용할 수 있다.
- Public API name, schema key, diagnostic은 rack-tracker naming convention을 따라야 한다.
- Threshold와 outlier policy는 synthetic fixture 및 rack-tracker 소유 또는 별도 라이선스가 있는 recording으로 검증한 rack-tracker policy decision이어야 한다.
- 구현 note와 PR text는 이 기능이 표준 weighted homogeneous least-squares triangulation 기반이며 조사 대상 프로젝트의 source code를 복사하지 않았다고 명시해야 한다.

Single frame 또는 frame group을 위한 권장 input contract:

- `multi_view_observations[camera_index, target_index, channel]`
- channel `x_pixel`: pixel 단위 horizontal image coordinate
- channel `y_pixel`: pixel 단위 vertical image coordinate
- channel `confidence`: `[0.0, 1.0]` 범위의 normalized observation reliability
- `projection_matrices[camera_index, 3, 4]`
- projection matrix는 active `CalibrationBundle`과 선언된 reconstruction space, 보통 `CaptureWorldSpace`에서 derive해야 한다. reconstruction mode가 명시적으로 rack-relative가 아닌 한 rack alignment를 조용히 encode해서는 안 된다.
- `camera_index`와 정렬된 camera id metadata

Target별 reconstruction 요구사항:

- Active rack-tracker policy를 만족하는 confidence를 가지며 coordinate가 finite인 camera observation만 사용한다.
- Retained camera count가 configured minimum보다 작으면 target을 invalid로 표시하고 failure reason을 기록한다.
- Retained observation과 projection matrix마다 homogeneous linear system에 weighted projection equation 두 개를 추가한다:
  - `confidence * (x_pixel * P_row_2 - P_row_0) * X = 0`
  - `confidence * (y_pixel * P_row_2 - P_row_1) * X = 0`
- Stacked homogeneous system을 SVD 또는 동등한 least-squares method로 풀고 homogeneous point를 3D coordinate로 normalize한다.
- Non-finite solution, invalid homogeneous scale, active camera-depth policy 위반 point는 reject한다.
- Target quality는 retained 2D confidence 값, retained camera count, reconstruction diagnostic으로 계산한다. 이 formula는 조사 대상 프로젝트에서 복사하지 않은 rack-tracker policy여야 한다.
- 3D point를 모든 retained camera에 reproject하고 per-camera reprojection error를 기록한다.
- High-error observation은 rack-tracker policy에 따라 outlier로 표시한다. 충분한 non-outlier view가 남으면 rejected observation을 제외하고 triangulation을 다시 수행하며, audit을 위해 original observation status를 보존한다.

필수 reconstruction output:

- `keypoints3d[target_index, channel]`: channel은 `x`, `y`, `z`, `quality`
- `used_camera_count[target_index]`
- `used_camera_mask[camera_index, target_index]` 또는 동등한 camera id list
- `reprojection_error[target_index]`
- `per_camera_reprojection_error[camera_index, target_index]`
- `observation_reconstruction_status[camera_index, target_index]`
- invalid target을 위한 `failure_reason[target_index]`
- confidence gating, minimum-view requirement, outlier rejection에 대한 policy id

필수 test:

- Synthetic calibrated camera와 synthetic 3D point를 2D로 project한 뒤 선언된 tolerance 안에서 다시 reconstruct한다.
- Geometrically noisy한 low-confidence view는 high-confidence view보다 영향이 작다.
- Confidence policy 미만 view는 reconstruction에서 제외된다.
- Retained view가 너무 적은 target은 invalid이며 stable failure reason을 가진다.
- High-reprojection-error observation은 outlier로 표시되고, policy가 허용할 때 retriangulation은 retained view만 사용한다.

## Safety Pin 및 J-Cup Event

목적: 특정 detector 또는 원본 프로젝트 동작에 분석을 묶지 않고 rack interaction event를 식별한다.

필수 static 또는 tracked feature:

- left/right J-cup location 또는 support zone
- 있는 경우 left/right safety-pin location 또는 support zone
- proximity를 위한 rack upright 또는 reference plane

권장 event type:

- `bar_near_jcup`
- `bar_supported_by_jcup_candidate`
- `bar_unrack_candidate`
- `bar_rerack_candidate`
- `bar_near_safety_pin`
- `bar_contact_safety_pin_candidate`

요구사항:

- Event는 frame range, involved entity, `RackWorldSpace` distance, quality, policy id를 포함해야 한다.
- Proximity threshold, contact threshold, temporal hysteresis는 rack-tracker 정책 결정이다.
- Event output은 candidate event와 confirmed event를 구분해야 한다.
- Rack anchor 또는 bar endpoint 품질이 낮으면 event를 suppress하거나 downgrade할 수 있어야 한다.

## `RackWorldSpace` Output 요구사항

모든 analysis-ready output은 다음을 포함해야 한다.

- `space_id = RackWorldSpace`
- `unit`
- `frame_index`
- 사용 가능한 경우 timestamp
- entity id와 target id
- raw 및 processed provenance
- quality summary
- reconstruction mode
- capture world에서 mapping할 때 사용한 transform id

필수 analysis output:

- center trajectory로서의 bar path
- bar endpoint trajectory
- bar tilt 또는 endpoint height asymmetry
- rack proximity metric
- support-zone event candidate
- 선택된 lift type에 필요한 person-bar relationship metric
- 누락되었거나 degraded된 metric을 설명하는 diagnostic

## 별도로 정의해야 할 Domain Policy

rack-tracker는 다음을 위한 새로운 policy file 또는 schema를 정의해야 한다.

- supported lift type
- lift type별 required 및 optional target
- rack anchor acquisition method
- metric별 acceptable camera count
- metric별 allowed interpolation span
- event threshold와 hysteresis
- single-camera estimate limitation
- metric blocking versus warning behavior
