# [design] 3D 스켈레톤 triangulation 구현 계획
Parent: #29

## 문서 관계
- 이 문서는 `3d-skeleton-synthesizer-plan.md`의 하위 구현 계획이다.
- 목적은 저장된 두 2D 스켈레톤 JSON과 Panoptic Studio 캘리브레이션 파일을 입력으로 받아 metric 3D 관절을 복원하는 최소 triangulation 경로를 정의하는 것이다.
- 이 문서는 코드 변경 없이 구현 순서와 계약만 정리한다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TRI-01 | 입력 계약 | synthesis contract | 구현 완료 | `SynthesisInput`에서 skeleton job id, camera id, calibration ref를 받아 triangulation 입력을 구성한다. | 없음 | 상위 synthesis schema 변경 시 service input 필드도 함께 갱신한다. | `3d-skeleton-synthesizer-plan.md` |
| TRI-02 | 프레임 정합 | alignment | 구현 완료 | timestamp-first pairing을 기본으로 하고 `frameIndex`는 sanity check로 사용한다. | max delta 기본값은 fps 기반으로 계산하고 실제 결과로 조정할 수 있다. | 실제 업로드 케이스가 생기면 sync tuning만 별도 검토한다. | 처리 순서 |
| TRI-03 | 캘리브레이션 로드 | camera geometry | 구현 완료 | Panoptic `00_00`, `00_01`의 `K`, `distCoef`, `R`, `t`를 `CameraModel`로 변환한다. | projection matrix 방향과 단위의 GT 기준 수치 검증은 추가 여지가 있다. | reprojection fixture 기준 검증 메모를 보강한다. | 입력 |
| TRI-04 | 2D 관측점 변환 | observation | 구현 완료 | MediaPipe normalized 좌표를 `videoInfo.width/height` 기반 pixel 좌표로 변환한다. | 기존 artifact에 width/height가 없으면 보강 또는 실패 처리 정책이 필요하다. | 누락 artifact 처리 규칙만 문서로 명확히 남긴다. | 처리 순서 |
| TRI-05 | 왜곡 보정 | camera geometry | 구현 완료 | 입력 관측점의 `distortionState`를 명시하고 필요한 경우 undistorted point를 만든다. | OpenCV 보정 적용 결과의 수치 검증은 추가 여지가 있다. | 관측점 contract와 보정 경계를 fixture 기준으로 재검토한다. | 처리 순서 |
| TRI-06 | DLT triangulation | geometry service | 구현 완료 | 두 카메라의 projection matrix와 양쪽 2D 관측점으로 관절별 3D point를 복원한다. | 없음 | threshold tuning과 failure reason 분포만 추가 관찰한다. | 구현 후보 파일 |
| TRI-07 | reprojection scoring | quality | 구현 완료 | 복원된 3D point를 양쪽 카메라로 다시 project하고 px 단위 error를 기록한다. | `maxReprojectionErrorPx` 초기값은 첫 실험 후 조정 가능하다. | 실데이터 분포를 보고 threshold 조정 여부를 판단한다. | 품질 기준 |
| TRI-08 | 보류 범위 | future scope | 보류 | 실제 카메라 입력, 3개 이상 카메라, MediaPipe world landmark 융합은 첫 구현에서 제외한다. | 없음 | MVP triangulation 검증 후 별도 issue로 분리한다. | 보류 |

## 전제
- 첫 구현은 stored videos 전용이다. 실제 카메라 실시간 입력은 다루지 않는다.
- 데이터셋은 `171204_pose1/` 아래의 Panoptic Studio `171204_pose1` 가공본을 사용한다.
- 첫 카메라 쌍은 `00_00 + 00_01` 로 고정한다.
- 입력 영상은 `171204_pose1/171204_pose1/hdVideos_gt_aligned/` 기준으로 시간축이 이미 맞춰졌다고 본다.
- MediaPipe `z` 값은 metric 3D가 아니므로 첫 triangulation 계산에는 사용하지 않는다.

## 입력
- `skeletonA`: Video A의 2D 스켈레톤 JSON
- `skeletonB`: Video B의 2D 스켈레톤 JSON
- `cameraIdA`: 첫 버전 기본값 `00_00`
- `cameraIdB`: 첫 버전 기본값 `00_01`
- `calibrationRef`: `171204_pose1/171204_pose1/calibration_171204_pose1.json`
- 선택 입력: pair manifest JSON

## 출력
- 별도 3D JSON 파일
- 관절별 `success`, `sourceVisibility`, `reprojectionErrorPx`
- 프레임별 합성 성공/실패 요약
- 전체 `qualitySummary`

## 처리 순서
1. pair manifest 를 읽어 두 2D JSON 경로와 카메라 ID를 확정한다.
2. 두 2D JSON을 로드하고 `frames` 배열을 읽는다.
3. `timestampMs` 기반으로 프레임을 정합하고 `frameIndex`는 sanity check와 디버깅 정보로만 사용한다.
4. 캘리브레이션 JSON에서 `cameraIdA`, `cameraIdB` 항목을 찾는다.
5. 각 카메라의 `K`, `distCoef`, `R`, `t`를 내부 행렬로 변환한다.
6. 2D normalized landmark 좌표를 픽셀 좌표로 변환한다.
7. 왜곡 보정 여부를 명시적으로 적용한다.
8. 관절 이름이 양쪽 프레임에 모두 있고 visibility/presence 조건을 통과하면 triangulation을 수행한다.
9. 복원된 3D 점을 각 카메라로 다시 projection 해서 reprojection error 를 계산한다.
10. 관절별 success flag 와 실패 이유를 기록한다.

## 품질 기준
- 양쪽 카메라 모두 `poseDetected=true`인 프레임만 합성 후보로 둔다.
- 관절별 visibility/presence 는 첫 버전에서 기본 임계값 `0.5`로 시작한다.
- reprojection error 임계값은 결과를 본 뒤 조정 가능하게 설정값으로 둔다.
- 프레임은 버리지 않고, 실패한 관절만 `success=false`로 표시한다.

## 보류
- 실제 카메라 입력용 동기화
- 3개 이상 카메라 일반화
- MediaPipe `world_landmarks`와 triangulated 좌표 융합
- triangulation 결과를 바로 분석 파이프라인에 투입

## 구현 후보 파일
- `backend/schema/synthesis.py`
- `backend/service/camera_calibration.py`
- `backend/service/frame_alignment.py`
- `backend/service/triangulation.py`
- `backend/service/skeleton_3d_synthesizer.py`
- `backend/scripts/run_3d_synthesis.py`
- `backend/tests/test_triangulation.py`
