# 데이터 Shape

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/03_data_shapes_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/03-data-shapes.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
이 문서는 rack-tracker 데이터 계약을 정의한다. 아래의 이름과 shape는 새로운 rack-tracker 계약이며, 원본 프로젝트 API 이름이 아니다.

## 일반 Convention

- Numeric array는 compact storage에는 `float32`를 사용하고, calibration 또는 reconstruction precision이 필요할 때는 `float64`를 사용해야 한다. dtype은 반드시 기록해야 한다.
- 누락된 numeric coordinate는 `NaN`이어야 한다.
- 누락되었거나 실패한 confidence는 `0.0`이어야 한다.
- 관측이 없을 때 boolean visibility flag는 `false`여야 한다.
- 영구 저장되는 모든 array는 `schema_version`, `session_id`, coordinate `space_id`, axis id, channel definition에 대한 메타데이터를 포함해야 한다.
- 아래 기본 shape를 사용하더라도 array axis order는 메타데이터에 선언해야 한다.

## `Observation2D`

목적: 원본 이미지 픽셀에서의 camera-frame-target 관측.

권장 dense shape:

```text
[camera_index, frame_index, target_index, channel]
```

Channel 의미:

| Channel | 의미 | 단위 | 누락값 |
| --- | --- | --- | --- |
| `x` | `ImageSpace`의 가로 픽셀 좌표 | pixel | `NaN` |
| `y` | `ImageSpace`의 세로 픽셀 좌표 | pixel | `NaN` |
| `confidence` | detector confidence 또는 정규화된 관측 신뢰도 | 0.0 to 1.0 | `0.0` |

필수 메타데이터:

- `camera_ids[camera_index]`
- `frame_ids[frame_index]`
- `target_ids[target_index]`
- `space_id = ImageSpace`
- 전처리가 적용된 경우 camera/frame별 `preprocess_transform_id`
- detector adapter id와 detector model provenance

권장 sidecar array:

- `visibility[camera_index, frame_index, target_index]`: boolean.
- `observation_status[camera_index, frame_index, target_index]`: detected, missing, outside_roi, rejected_by_policy 같은 enum.
- `source_timestamp[camera_index, frame_index]`: 초 단위 또는 monotonic timestamp.

## `PreprocessTransform`

목적: 하나의 source frame이 하나의 detector input frame으로 변환된 방식을 설명한다.

권장 field:

| Field | 의미 |
| --- | --- |
| `transform_id` | 관측을 전처리 메타데이터에 다시 join하기 위한 stable id. |
| `camera_id` | source camera id. |
| `frame_index` | source frame index. |
| `source_space_id` | 보통 `ImageSpace`. |
| `target_space_id` | 보통 `PreprocessedImageSpace`. |
| `original_image_size` | 전처리 전 width와 height. |
| `model_input_size` | detector에 전달된 width와 height. |
| `crop_rect_xywh` | 사용된 경우 source pixel의 crop rectangle. |
| `scale_xy` | source-to-model scale factor. |
| `padding_xy` | model-input pixel에서 적용된 padding. |
| `rotation_degrees` | 있는 경우 선언된 rotation. |
| `distortion_correction_id` | 있는 경우 calibration-linked correction id. |
| `image_to_preprocessed_transform` | 명시적 forward transform 표현. |
| `preprocessed_to_image_transform` | 명시적 inverse transform 표현. |
| `valid` | transform이 양방향으로 point를 안전하게 map할 수 있는지 여부. |

## `CalibrationBundle`

목적: 카메라 캘리브레이션, 타깃 정보, capture-world 정의를 바인딩한다.

권장 field:

| Field | 의미 |
| --- | --- |
| `calibration_id` | stable id. |
| `camera_ids` | 이 bundle이 포함하는 카메라. |
| `unit` | calibration 값이 사용하는 길이 단위. |
| `intrinsics_by_camera` | 카메라별 camera matrix 또는 동등한 intrinsic model. |
| `distortion_by_camera` | 카메라별 distortion model과 coefficient. |
| `extrinsics_by_camera` | camera-to-capture 및/또는 capture-to-camera transform. |
| `capture_world_space` | `CaptureWorldSpace`의 origin, axis, unit. |
| `calibration_target` | target type, dimension, marker layout summary, physical scale. |
| `calibration_quality` | error summary와 coverage diagnostic. |
| `distortion_application_policy` | 전처리 또는 projection/reconstruction 중 correction 적용 여부. |
| `created_at` | calibration timestamp. |

## `Reconstruction3D`

목적: rack-domain analysis 이전의 재구성된 타깃 위치.

권장 dense shape:

```text
[frame_index, target_index, channel]
```

Channel 의미:

| Channel | 의미 | 단위 | 누락값 |
| --- | --- | --- | --- |
| `x` | 선언된 `space_id`의 3D 좌표 | calibration unit | `NaN` |
| `y` | 선언된 `space_id`의 3D 좌표 | calibration unit | `NaN` |
| `z` | 선언된 `space_id`의 3D 좌표 | calibration unit | `NaN` |
| `quality` | 정규화된 reconstruction 신뢰도 | 0.0 to 1.0 | `0.0` |

필수 메타데이터:

- `frame_ids[frame_index]`
- `target_ids[target_index]`
- `space_id`, 원시 reconstruction에서는 보통 `CaptureWorldSpace`
- `calibration_id`
- `reconstruction_mode`: multi_camera, single_camera_estimate, simulated, imported

권장 sidecar array:

- `reprojection_error[frame_index, target_index]`
- `per_camera_reprojection_error[camera_index, frame_index, target_index]`
- `used_camera_count[frame_index, target_index]`
- multi-camera reconstruction이 retained camera를 dense mask로 저장하는 경우 `used_camera_mask[camera_index, frame_index, target_index]`
- reconstruction engine이 지원하는 경우 `camera_contribution[camera_index, frame_index, target_index]`
- `observation_reconstruction_status[camera_index, frame_index, target_index]`: retained, below_confidence, outlier_reprojection_error, missing, invalid_projection 같은 enum
- `reconstruction_status[frame_index, target_index]`
- `failure_reason[frame_index, target_index]`: invalid target을 위한 stable enum. 예: insufficient_views, degenerate_solution, non_finite_solution, behind_camera, high_reprojection_error

## `EntityFrame3D`

목적: 타깃을 rack-tracker domain entity로 조립한다.

권장 record field:

| Field | 의미 |
| --- | --- |
| `frame_index` | logical frame id. |
| `timestamp` | 사용 가능한 경우 session timestamp. |
| `space_id` | analysis-ready entity에서는 `RackWorldSpace`를 기대한다. |
| `persons` | keypoint와 quality를 가진 한 명 이상의 tracked people. |
| `barbell` | left endpoint, right endpoint, derived center, axis, quality. |
| `rack` | static 또는 tracked rack anchor와 support feature. |
| `derived_segments` | bar axis 또는 torso line 같은 domain-specific segment. |
| `events` | unrack, rerack, support contact, safety-pin proximity에 대한 candidate event. |
| `quality` | frame-level quality summary. |

권장 nested shape:

- `persons[person_index].keypoints[keypoint_index, channel]`, channel은 `x`, `y`, `z`, `quality`.
- `barbell.points[point_index, channel]`, point는 left endpoint, right endpoint, derived center를 포함한다.
- `rack.anchors[anchor_index, channel]`, anchor는 session 설계에 따라 static 또는 frame-varying이다.

## Sparse Representation

rack-tracker는 live stream 또는 선택적 타깃이 많은 경우 dense array 대신 sparse record를 사용할 수 있다. 그래도 sparse record는 다음을 포함해야 한다.

- 2D인 경우 camera id
- frame id
- target id
- channel name
- coordinate space
- missing/status reason
- quality field

Offline batch processing에는 dense array를 권장한다. sync, reconstruction, temporal diagnostic을 더 쉽게 검증할 수 있기 때문이다.
