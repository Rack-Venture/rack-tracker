# 품질 Metric

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/04_quality_metrics_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/04-quality-metrics.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
Quality metric은 로그에만 나타나지 말고 데이터와 함께 이동해야 한다. Threshold는 rack-tracker 정책 결정이며 조사 대상 구현에서 복사해서는 안 된다.

## Metric 계약

| Metric | 범위 | Shape / Record | 의미 | 용도 |
| --- | --- | --- | --- | --- |
| `detection_confidence` | 2D observation | `[camera, frame, target]` | 하나의 타깃 관측에 대한 detector-reported 또는 adapter-normalized confidence. | 낮은 confidence point gate, detector reliability 요약, camera-specific failure 디버깅. |
| `per_camera_visibility` | 2D observation | `[camera, frame, target]` boolean 또는 0/1 | 타깃이 카메라 프레임에서 관측되었고 사용 가능한지 여부. | 누락된 3D point 설명과 camera coverage 계산. |
| `sync_warnings` | session/frame group | frame group을 key로 하는 record | frame count, timestamp, FPS 또는 offset 문제. | 조용한 multi-view mismatch를 막고 reconstruction risk를 표시. |
| `reprojection_error` | 3D target | `[frame, target]` 및 선택적 `[camera, frame, target]` | 관측된 2D point와 projected 3D result의 차이. image pixel 또는 선언된 단위. | reconstruction reliability 순위화와 나쁜 camera/target 조합 찾기. |
| `used_camera_count` | 3D target | `[frame, target]` | 3D target에 기여한 카메라 수. | 강한 multi-view point와 약하거나 누락된 reconstruction 구분. |
| `camera_contribution` | 3D target | 선택적 `[camera, frame, target]` | 카메라별 normalized contribution, weight 또는 retained/rejected state. | occlusion, bad calibration, per-camera outlier 동작 진단. |
| `dropped_observations` | 2D 또는 reconstruction | camera/frame/target을 key로 하는 record | 정책에 의해 제외되었거나 source data 누락으로 사용할 수 없는 관측. | data loss audit와 rejected data를 detector absence와 혼동하지 않기. |
| `interpolation_spans` | temporal output | entity/target과 frame range를 key로 하는 record | 시간축 후처리로 채워진 연속 frame. | interpolated point가 raw measurement로 취급되는 것을 방지. |
| `world_space_alignment_quality` | coordinate mapping | session-level 및 anchor-level record | `CaptureWorldSpace`를 `RackWorldSpace`로 mapping하는 fit quality. | rack-anchor reliability 검증과 불안정한 rack analysis 경고. |

## 필수 Quality Field

각 quality report는 다음을 포함해야 한다.

- `schema_version`
- `session_id`
- `metric_name`
- `metric_unit`
- metric이 좌표계에 의존할 때 `space_id`
- `aggregation_level`: observation, camera, target, entity, frame, session
- `value`
- `status`: ok, warning, failed, not_applicable, not_computed
- 사용된 threshold 또는 rule set에 대한 `policy_id`

## Detection Confidence

- detector-provided value는 adapter normalization 이후에만 저장한다.
- raw detector score가 다른 의미를 가진다면 adapter-private diagnostic에 보관한다.
- confidence만으로 3D reliability를 암시해서는 안 된다. visibility, calibration, reprojection diagnostic과 결합해야 한다.

## Per-Camera Visibility

- visible target은 `ImageSpace`에서 사용할 수 있는 `x`, `y`, confidence를 가진 타깃이다.
- visibility는 no detection, outside region of interest, masked by preprocessing, rejected by policy, unavailable frame을 구분해야 한다.
- visibility summary는 camera별, target별, session별로 보고해야 한다.

## Sync Warnings

Sync diagnostic은 다음을 기록해야 한다.

- frame count mismatch
- missing timestamp
- timestamp discontinuity
- FPS disagreement
- dropped 또는 duplicated frame
- 적용되었거나 필요한 camera offset

Warning record는 영향을 받는 camera와 frame range를 이름으로 지정해야 하며, persistence를 console log에 의존해서는 안 된다.

## Reprojection Error

- target-level aggregate reprojection error를 저장한다.
- 사용 가능한 경우 per-camera reprojection error를 저장한다.
- 단위를 기록한다. 보통 `ImageSpace`의 pixel이다.
- 누락되었거나 유효하지 않은 3D point는 high-error 3D point와 별도로 취급한다.

## Confidence-Weighted Reconstruction Quality

- Multi-camera reconstruction은 표준 homogeneous least-squares triangulation system에서 normalized 2D observation confidence를 weight로 사용할 수 있다.
- Confidence weighting은 visibility, calibration quality, camera count, reprojection diagnostic을 대체하지 않는다.
- 3D target의 public quality 값은 retained observation confidence, retained camera count, reprojection diagnostic을 rack-tracker policy id에 따라 결합해야 한다.
- policy는 어떤 observation이 retained, rejected for low confidence, rejected as reprojection outlier, unavailable인지 기록해야 한다.
- 기본 threshold와 outlier behavior는 조사 대상 프로젝트에서 복사하지 않고 rack-tracker validation data로 선택해야 한다.

## Used Camera Count

- Multi-view reconstruction은 각 target에 몇 대의 카메라가 기여했는지 노출해야 한다.
- 너무 적은 카메라로 재구성된 target은 정상 3D로 조용히 방출하지 말고 정책에 따라 label해야 한다.
- Single-camera estimate는 별도의 reconstruction mode와 quality interpretation을 가져야 한다.

## Dropped Observations

Dropped observation은 다음을 기록해야 한다.

- camera id
- frame index
- target id
- drop reason
- 원본 관측이 디버깅용으로 아직 사용 가능한지 여부

Storage policy가 명시적으로 요구하지 않는 한 dropped raw observation을 삭제하지 않는다.

## Interpolation Spans

Temporal processing은 다음을 기록해야 한다.

- entity id
- target id
- start frame
- end frame
- span length
- fill method category
- fill 전후의 source quality

Interpolated point는 measured 또는 reconstructed point와 계속 구분 가능해야 한다.

## World-Space Alignment Quality

Rack-world alignment는 다음을 보고해야 한다.

- 사용된 rack anchor 수
- capture 및 rack 단위에서의 anchor residual
- 사용된 경우 ground-plane fit quality
- vertical-axis confidence
- calibration frame 또는 manual edit 전반의 transform stability
- transform이 automatic, manual, imported 중 무엇인지

Alignment가 unknown 또는 underdetermined이면 rack analysis는 metric을 downgrade하거나 block해야 한다.
