# 좌표 공간

## 문서 쌍 동기화 강제

이 문서는 아래 문서와 쌍으로 관리한다.

- 원본 요구사항: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/02_coordinate_spaces_ko.md`
- 채택 검토: `docs/mvp-v2/issues/sub-issues/37-feat-adopt-rack-motion-pipeline-design-implementation/requirements-adoption-review/02-coordinate-spaces.md`

둘 중 하나를 수정하면 같은 작업 단위에서 다른 문서도 검토하고 필요한 변경을 반영해야 한다. 커밋 전에는 다음 검사가 한쪽만 변경된 문서쌍을 실패 처리한다.

```powershell
powershell.exe -ExecutionPolicy Bypass -File scripts/check-requirements-doc-pairs.ps1
```
rack-tracker는 좌표 공간을 명시적 계약으로 다루어야 한다. 좌표 값은 `space_id`, 단위, 축 convention, transform 방향이 알려져 있지 않으면 유효하지 않다.

용어 출처: 이 문서의 좌표 공간 식별자는 조사 대상 프로젝트의 API 이름을 복사한 것이 아니라 rack-tracker 계약 라벨이다. 일반적인 좌표 개념을 도메인 특화 명명 체계로 설명한다.

라이선스 경계: 이 문서는 외부 프로젝트의 소스 코드, 내부 파일 포맷, 함수명, 클래스명, 폴더 구조, 주석, 샘플 데이터를 재사용하지 않는다. 아래 계약은 OpenCV, multi-view geometry, photogrammetry에서 쓰이는 공개 기하 원리를 rack-tracker 요구에 맞게 독립적으로 재정의한 것이다.

## `ImageSpace`

- 목적: decoding 이후, detector별 resize 또는 crop 이전의 원본 카메라 이미지 픽셀 좌표.
- 원점: decoded image의 왼쪽 위 픽셀.
- 축: `x`는 오른쪽으로 증가하고 `y`는 아래쪽으로 증가한다.
- 단위: pixel.
- 차원: 2D.
- 계약: detector가 resize 또는 crop된 이미지에서 실행되었더라도 저장되는 모든 `Observation2D` 좌표는 이 공간으로 정규화되어야 한다.
- 필수 메타데이터: image width, image height, camera id, frame index, pixel coordinate convention.

## `PreprocessedImageSpace`

- 목적: resize, crop, padding, rotation, masking, color conversion, distortion correction 같은 작업 이후의 model-input 이미지 좌표.
- 원점: detector adapter가 다르게 선언하지 않는 한 전처리된 model input의 왼쪽 위.
- 축: 전처리 이후 `x`는 오른쪽으로 증가하고 `y`는 아래쪽으로 증가한다.
- 단위: model input image의 pixel.
- 차원: 2D.
- 계약: 이 공간은 내부 detector-adapter 공간이다. `PreprocessTransform`으로 `ImageSpace`에 연결되어야 하며, 영구 저장되는 2D 관측의 기본 좌표 공간이 되어서는 안 된다.
- 필수 메타데이터: input size, output size, crop rectangle, scale, padding, rotation, distortion policy, forward transform, inverse transform.

## `CameraSpace`

- 목적: 하나의 물리적 또는 논리적 카메라에 묶인 3D 좌표계.
- 원점: camera optical center 또는 캘리브레이션 모델이 선언한 camera origin.
- 축: rack-tracker는 정규화된 camera convention을 선언해야 한다. 권장 기본값은 `x` camera-right, `y` camera-down, `z` 카메라에서 장면 안쪽으로 forward이다. 외부 캘리브레이션 소스가 다른 convention을 사용하면 bundle에 이를 명시해야 한다.
- 단위: 캘리브레이션 단위. 정규화 이후에는 meter를 권장한다.
- 차원: 3D.
- 계약: camera-space ray, depth estimate, camera extrinsics는 camera id와 calibration id로 추적 가능해야 한다.
- 고정 센서 계약: 카메라가 파워랙 구조물 또는 개발용 mock rig에 거치되어 있다면 각 카메라 pose는 먼저 `CaptureWorldSpace`에 대한 extrinsics 관계로 고정해야 한다. 이 값은 skeleton motion에서 추정되는 속성이 아니다.
- rack-tracker 설정 계약: rack-tracker는 재현 가능한 카메라 배치를 목표로 하지만, rack마다 폭, 깊이, 높이, anchor가 다를 수 있다. 따라서 camera calibration file은 camera id별 intrinsics, image size, distortion policy, `camera_to_capture` 또는 `capture_to_camera` transform, calibration id를 저장하고, rack geometry와 `capture_to_rack` alignment는 별도 입력 rack config 또는 alignment 산출물에서 관리해야 한다.
- 고정 환경에서도 카메라 마운트, 렌즈, 해상도, mock rig, rack geometry, rack anchor가 바뀌면 상황에 맞게 새 calibration id 또는 rack alignment id를 발급해야 한다.
- rack-mounted calibration mode: 카메라가 파워랙 또는 고정 mock rig에 장착되어 `CaptureWorldSpace`와 `RackWorldSpace`가 같은 원점, 축, 단위를 쓰도록 설계될 수 있다. 이 경우에도 두 공간이 같다고 암시하지 말고 `capture_to_rack = identity` 또는 calibrated rigid transform을 명시하며, camera calibration id와 rack alignment id를 별도로 추적해야 한다.
- 필수 pose 메타데이터: `position_in_capture_world`, `rotation_camera_to_capture_world` 또는 `rotation_capture_world_to_camera`, 선택적 rack-relative pose, optical axis 또는 forward vector, camera up vector, camera right vector.

## `CaptureWorldSpace`

- 목적: 카메라 캘리브레이션이 생성하거나 수용하는 공통 3D 공간.
- 원점: 캘리브레이션이 정의한 world origin. 이 원점이 자동으로 rack-centered인 것은 아니다.
- 축: 캘리브레이션이 정의한 축. rack-tracker는 축이 rack analysis 요구와 일치한다고 가정하지 말고 convention을 기록해야 한다.
- 단위: 캘리브레이션 단위. bundle은 값이 meter, millimeter, target-square unit 중 무엇인지 명시해야 한다.
- 차원: 3D.
- 계약: 다중 뷰 재구성은 rack alignment 이전에 이 공간의 원시 3D 좌표를 방출한다.
- rack-tracker 계약: 개발용 mock rig와 실제 rack을 같은 재구성 파이프라인으로 다루기 위해, camera extrinsics와 triangulation은 기본 공유 공간으로 `CaptureWorldSpace`를 사용해야 한다. 실제 rack의 물리 치수와 anchor는 별도 rack config에서 읽어 `RackWorldSpace`로 mapping한다.
- 필수 메타데이터: `capture_world_space_id`, unit, axis definition, camera extrinsics, calibration quality, 선택적 ground-plane definition.

## `RackWorldSpace`

- 목적: bar path, rack proximity, endpoint asymmetry, support-contact event 같은 분석 output에 사용하는 rack-centered world space.
- 물리적 정의: 이 공간은 rack의 바닥, 기둥, 높이, 폭, 깊이, 원점, 축을 정의한다. 움직이는 skeleton이 아니라 고정된 rack 환경을 모델링한다.
- 권장 원점: rack centerline reference와 floor plane의 교차점, 또는 사용자 지정 rack anchor.
- 권장 축: `x`는 lifter-left에서 lifter-right, `y`는 rack-to-lifter depth, `z`는 중력 반대 방향 위쪽.
- 단위: 프로젝트가 명시적으로 다른 단위를 선택하지 않는 한 meter.
- 차원: 3D.
- 계약: 모든 rack analysis output과 재구성된 dynamic entity는 이 공간을 사용하거나 사용하지 않는 이유를 명시해야 한다.
- 독립성 규칙: skeleton data는 `RackWorldSpace`를 정의하거나, fit하거나, 기울기 보정하거나, 수정해서는 안 된다. Skeleton은 이 world 안에서 재구성되는 동적 객체이다.
- 필수 메타데이터: rack anchor point, ground plane 또는 vertical reference, rack dimensions, 별도의 capture space가 있을 때 `capture_to_rack` transform, `rack_to_capture` transform, alignment quality.

## `Skeleton`

- 목적: `RackWorldSpace` 안에서 움직이는 동적 재구성 entity.
- 좌표 의존성: skeleton keypoint는 `CaptureWorldSpace`로 재구성된 뒤 `RackWorldSpace`로 mapping될 수 있으며, calibration이 명시적으로 rack-relative일 때만 `RackWorldSpace`로 직접 재구성될 수 있다.
- 계약: skeleton observation은 world origin, floor plane, vertical axis, rack dimensions, camera pose를 정의하지 않는다.
- 피해야 할 failure mode: front camera에서는 skeleton이 맞아 보이지만 side view에서 기울어 보인다면 보통 camera extrinsics, rack alignment, renderer world-up이 선언된 world space에 묶이지 않은 상태를 의심해야 한다.

## Camera Geometry 용어

- Optical axis / forward vector: camera optical center에서 image center를 통과하는 대표 ray.
- Line-of-sight ray: camera optical center에서 특정 image pixel, 예를 들어 감지된 무릎 keypoint를 통과하는 ray.
- View direction: 보통 forward vector와 같은 의미로 다룰 수 있지만, 구현에서는 canonical term 하나를 선택해 일관되게 사용해야 한다.
- Intrinsics: focal length 또는 camera matrix, distortion coefficients, image width, image height.
- Extrinsics: `CaptureWorldSpace` 또는 명시적으로 rack-relative인 경우 `RackWorldSpace`에 대한 camera position과 orientation.

핵심 계약:

```text
calibration defines CaptureWorldSpace
rack config or rack alignment defines RackWorldSpace
cameras are fixed sensors in CaptureWorldSpace
skeleton is reconstructed from camera rays and mapped into RackWorldSpace for analysis
skeleton never defines RackWorldSpace
```

## Pixel-To-Ray 재구성 계약

3D 합성은 영상에서 보이는 2D 사람 모양을 그대로 world에 올리는 과정이 아니다. 각 2D keypoint를 world-space ray로 역투영하고 여러 ray에서 triangulation해야 한다.

기본 필수 흐름:

```text
2D pixel keypoint
  -> undistort
  -> normalized camera ray
  -> camera extrinsics로 CaptureWorldSpace ray로 변환
  -> CaptureWorldSpace에서 여러 camera ray의 closest point / triangulation
  -> 선택적 capture_to_rack transform
  -> 분석용 RackWorldSpace 3D keypoint
```

개념 수식:

```text
ray_camera = inverse(K) * [u, v, 1]
ray_camera = normalize(ray_camera)

ray_capture_origin = camera_position_in_capture_world
ray_capture_direction = R_camera_to_capture * ray_camera

point_rack = T_capture_to_rack * point_capture
```

계약:

- Intrinsics와 distortion correction은 각 image pixel에 대한 camera-local ray를 결정한다.
- Camera extrinsics는 그 ray가 `CaptureWorldSpace` 안에서 어디서 시작하고 어느 방향을 향하는지 결정한다.
- Rack alignment는 재구성된 point를 `RackWorldSpace`로 변환하는 방식을 결정한다.
- output이 single-camera estimate로 명시되지 않는 한 3D point 추정에는 두 개 이상의 camera ray를 사용해야 한다.
- Reconstruction output은 `space_id`, calibration id, used camera ids, reprojection error, quality status를 포함해야 한다. Analysis-ready output은 `capture_to_rack` transform을 사용한 경우 rack alignment id도 포함해야 한다.

## Camera Pose Diagnostics

rack-tracker는 재구성된 skeleton motion을 신뢰하기 전에 camera geometry를 시각적으로 진단할 수 있어야 한다.

권장 renderer/debug overlay:

- Capture-world axes and unit convention.
- Rack frame: width, depth, height, uprights, known anchor points.
- Floor plane: `z = 0` 또는 프로젝트가 선언한 vertical convention.
- `CaptureWorldSpace` 안의 camera positions 및 mapping된 경우 `RackWorldSpace` 안의 camera positions.
- Camera forward vectors / optical axes.
- Camera frustums.
- 선택한 2D keypoint의 line-of-sight rays.
- 두 공간이 모두 있을 때 rack alignment 전후의 triangulated 3D skeleton.

Skeleton이 rack 또는 floor에 대해 기울어 보이면, 우선 진단할 대상은 skeleton 정의 자체가 아니라 camera extrinsics, rack alignment transform, renderer world-up convention이다.

## Calibration Bundle 계약

- 목적: 촬영 환경의 카메라 배치와 렌즈 모델을 rack-tracker 독자 schema로 고정한다.
- 저장 형식: TOML, JSON, YAML 중 하나를 선택할 수 있으나 schema는 rack-tracker가 소유해야 한다. 외부 프로젝트의 calibration 파일 구조를 그대로 복제하지 않는다.
- 필수 camera 필드: `camera_id`, image width, image height, intrinsic matrix, distortion model, distortion coefficients, calibration unit, transform direction.
- 필수 pose 필드: rack-tracker 기본 calibration에서는 `camera_to_capture` 또는 `capture_to_camera` 중 하나를 canonical transform으로 저장한다. rack-relative transform이 필요하면 camera calibration에 직접 섞지 말고 rack config 또는 alignment 산출물의 `capture_to_rack` / `rack_to_capture`로 연결한다. 어느 경우든 역변환을 계산 가능하게 저장한다.
- 필수 bundle 필드: `calibration_id`, `capture_world_space_id`, creation time, calibration target description, calibration quality metrics, coordinate convention. `rack_world_space_id`는 rack config 또는 rack alignment 산출물에서 연결한다.
- rack-tracker 권장 저장 분리: camera calibration은 카메라와 `CaptureWorldSpace`의 관계를 소유하고, rack config는 rack dimensions, rack anchor, floor plane, vertical reference, `capture_to_rack` 또는 `rack_to_capture` alignment를 소유한다. 실제 rack과 개발용 mock rack은 유효한 경우 같은 camera calibration을 재사용하면서 rack config 교체로 다룰 수 있어야 한다.
- 개발용 외부 calibration fixture를 사용할 때도 먼저 source camera id, image size, intrinsics, distortion, extrinsics, unit, source capture-world convention을 rack-tracker-owned calibration bundle로 가져온다. 그 다음 별도의 dev rig mapping에서 각 source camera에 파워랙 logical mount role을 부여한다.
- 개발용 logical mount role은 실제 rack anchor 또는 `RackWorldSpace` 정의가 아니다. rack anchor가 없으면 `capture_to_rack`은 `not_computed`로 남기고, 임시 identity transform을 쓰는 경우에도 dev-only assumption과 alignment provenance를 기록해야 한다.
- 계약: bundle은 2D 관측을 3D로 재구성하기 위한 기하 계약이지 detector 출력 포맷이나 분석 결과 포맷이 아니다.

## `CaptureWorldSpace` 경유 재구성

- 목적: calibration이 rack에 직접 묶이지 않고 별도의 capture world를 먼저 만드는 경우의 중간 경로를 정의한다.
- 입력: `ImageSpace`의 2D 관측, camera id, frame index, target id, calibration bundle, rack alignment.
- 1단계: 2D pixel point를 해당 카메라의 distortion model로 undistort한다.
- 2단계: intrinsic matrix의 역변환을 사용해 undistorted point를 normalized camera ray로 변환한다.
- 3단계: camera pose transform을 사용해 camera-local ray를 `CaptureWorldSpace`로 배치한다.
- 4단계: 같은 frame과 target에 대한 여러 camera ray를 이용해 `CaptureWorldSpace`의 최적 3D point를 추정한다.
- 5단계: `capture_to_rack` transform으로 결과를 `RackWorldSpace`에 매핑한다.
- 출력: `RackWorldSpace`의 `Point3D`, 선택적 `CaptureWorldSpace` raw point, 사용된 camera id 목록, per-camera reprojection error, aggregate quality, reconstruction mode.
- 계약: 최종 분석과 렌더링 기준은 `RackWorldSpace`이며, optical axis, camera forward vector, view direction, line of sight는 calibration bundle과 image point에서 계산 가능한 파생 기하이다.

## Rack 기준 가상공간 고정

- 목적: 촬영 환경을 rack-centered 가상공간으로 해석하되, 재구성 좌표계와 분석 좌표계를 분리한다.
- 권장 절차: 먼저 calibration bundle로 `CaptureWorldSpace`를 고정하고, 별도의 rack config로 rack dimensions, rack anchor, floor plane, vertical reference를 입력해 `RackWorldSpace`를 정의한다. rack-relative calibration이 가능하더라도 개발용 mock rack과 실제 rack 사이의 교체 가능성을 위해 `CaptureWorldSpace`와 `RackWorldSpace`의 분리를 유지한다.
- rack anchor 예시: 좌우 upright의 하단 기준점, rack centerline, bar support 위치, floor contact plane, 사용자가 지정한 known-size fixture.
- transform 산출물: `capture_to_rack`과 `rack_to_capture`는 rigid transform으로 저장한다. scale 보정이 필요하면 similarity transform 사용 여부와 scale factor를 명시한다.
- 입력 artifact: `RackWorldSpace`는 코드 상수나 renderer-only transform이 아니라 별도 TOML, JSON, YAML 같은 rack config 또는 rack alignment 입력 artifact로 정의해야 한다.
- 권장 파일 분리: camera calibration artifact는 camera intrinsics, distortion, image size, camera pose, capture-world convention을 저장하고, rack alignment artifact는 rack dimensions, rack anchors, floor/vertical reference, `capture_to_rack`/`rack_to_capture`, alignment quality와 provenance를 저장한다.
- 개발 fixture 계약: 외부 calibration source로 개발용 mock rig를 구성할 때는 source capture world를 먼저 calibration bundle로 가져오고, 별도 dev rack alignment artifact에서 logical camera role, rack definition status, `capture_to_rack` 상태를 기록한다.
- production 계약: 실제 파워랙에서는 같은 rack alignment schema에 측정된 rack 폭/깊이/높이, 원점 정의, 축 정의, anchor observations, calibrated rigid 또는 similarity transform을 채운다.
- 계약: camera calibration을 자동으로 rack space와 동일하다고 취급해서는 안 된다. 같은 camera calibration이라도 rack size, rack position, mock rig, rack anchor가 바뀌면 새 `RackWorldSpace` alignment가 필요하다.
- 금지: floor plane, vertical axis, rack origin은 skeleton pose 또는 skeleton trajectory에서 추정하지 않는다.
- 품질 메타데이터: anchor reprojection error, rack-axis orthogonality error, floor-plane residual, scale confidence, alignment frame range.

## Transform 방향

| Transform | 방향 | 필수 용도 |
| --- | --- | --- |
| `image_to_preprocessed` | `ImageSpace`에서 `PreprocessedImageSpace` | 원본 픽셀에서 detector input 좌표를 재현한다. |
| `preprocessed_to_image` | `PreprocessedImageSpace`에서 `ImageSpace` | detector 출력을 원본 이미지 픽셀에 영구 저장한다. |
| `camera_to_capture` | `CameraSpace`에서 `CaptureWorldSpace` | camera-local ray 또는 point를 공유 재구성 공간에 배치한다. |
| `capture_to_camera` | `CaptureWorldSpace`에서 `CameraSpace` | 진단을 위해 3D point를 카메라로 다시 project한다. |
| `capture_to_rack` | `CaptureWorldSpace`에서 `RackWorldSpace` | 재구성된 point를 분석 좌표로 변환한다. |
| `rack_to_capture` | `RackWorldSpace`에서 `CaptureWorldSpace` | rack-space 정의를 디버깅하거나 capture space로 다시 reproject한다. |
| `pixel_to_camera_ray` | `ImageSpace`에서 `CameraSpace` ray | undistortion과 intrinsics 역변환으로 LOS ray를 계산한다. |
| `camera_ray_to_capture_ray` | `CameraSpace` ray에서 `CaptureWorldSpace` ray | camera-local LOS ray를 공통 재구성 공간으로 변환한다. |
| `camera_to_rack` | `CameraSpace`에서 `RackWorldSpace` | calibration이 명시적으로 rack-relative일 때만 camera-local ray를 rack world에 직접 배치한다. |
| `rack_to_camera` | `RackWorldSpace`에서 `CameraSpace` | 진단을 위해 rack-space point를 특정 camera로 다시 project한다. |
| `camera_ray_to_rack_ray` | `CameraSpace` ray에서 `RackWorldSpace` ray | direct rack-relative calibration이 선언된 경우에만 camera-local LOS ray를 rack world로 변환한다. |

## 좌표 공간 규칙

- 2D point는 `camera_id`, `frame_index`, `target_id`, `space_id`를 포함해야 한다.
- 3D point는 `frame_index`, `target_id`, `space_id`, unit, reconstruction mode를 포함해야 한다.
- 처리된 좌표는 원시 좌표에 대한 provenance를 유지해야 한다.
- 축 뒤집기, 회전, 단위 변환, 원점 변경은 파일 위치나 stage name으로 암시하지 말고 transform으로 저장해야 한다.
- `CaptureWorldSpace`는 재구성 좌표계이고 `RackWorldSpace`는 domain analysis 좌표계이다. 특정 session에서 transform이 identity처럼 보이더라도 둘은 분리되어야 한다.
- rack-tracker는 rack-relative calibration이 가능하더라도 `CaptureWorldSpace`를 primary reconstruction world로 유지하고, rack-specific 분석은 `capture_to_rack` 이후의 `RackWorldSpace`에서 수행해야 한다.
- 파워랙 구조물 또는 개발용 mock rig에 거치된 카메라는 `CaptureWorldSpace` 안의 fixed pose로 표현하고, rack별 치수와 anchor는 별도 rack config로 연결한다.
- 고정 장착 제품 모드에서 `capture_to_rack`이 identity에 가까워도 artifact에는 transform direction, unit, axis convention, rack alignment provenance를 기록해야 한다.
- `RackWorldSpace`가 필요한 artifact consumer는 rack alignment id와 상태를 확인해야 하며, `not_computed` 또는 dev-only alignment를 production-grade rack analysis 입력으로 취급해서는 안 된다.
- calibration bundle은 외부 구현의 schema 호환성을 목표로 하지 않는다. 필요한 경우 import adapter가 외부 파일을 읽어 rack-tracker schema로 변환하되, 내부 저장 계약은 독립 schema를 유지한다.
- LOS ray, optical axis, camera forward vector는 저장된 2D 관측 자체가 아니라 calibration bundle과 `ImageSpace` point에서 계산되는 파생값으로 취급한다.
- 3D triangulation 결과는 항상 어떤 calibration id와 어떤 rack alignment id에서 생성되었는지 추적 가능해야 한다.
