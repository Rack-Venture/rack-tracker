# [design] 3D 합성 GT 평가 계획
Parent: #29

## 문서 관계
- 이 문서는 `3d-skeleton-synthesizer-plan.md`의 하위 평가 계획이다.
- 목적은 Panoptic Studio GT 를 기준으로 3D 합성 결과를 정량 평가하는 최소 절차를 정의하는 것이다.
- 이 문서는 코드 변경 없이 평가 입력, 매핑, 지표, 출력만 정리한다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| EVAL-01 | GT 데이터 | evaluation input | 결정 완료 | `gt_skeleton_118_3596.json`과 frame range `118 ~ 3596`을 첫 평가 기준으로 사용한다. | 없음 | evaluator fixture에서 GT file path와 frame range를 고정한다. | 평가 데이터 |
| EVAL-02 | 비교 대상 | input contract | 구현 완료 | 합성 결과 `skeleton3d.v1`의 `frames[].joints` shape를 평가 입력으로 사용한다. | 없음 | joint shape가 바뀌면 evaluator parser와 viewer adapter를 함께 갱신한다. | 비교 대상 |
| EVAL-03 | 관절 매핑 | mapping | 구현 완료 | MediaPipe33과 COCO19의 direct subset만 첫 raw metric에 사용한다. | `neck`, `mid_hip` 파생 관절은 첫 raw metric 후 포함 여부를 결정한다. | 파생 관절 필요성이 생기면 mapping version을 올린다. | 관절 매핑 |
| EVAL-04 | raw MPJPE | metric | 구현 완료 | Panoptic world coordinate cm 기준 raw MPJPE mean/median/p95를 계산한다. | 좌표계 방향이 맞지 않을 경우 aligned metric을 별도 추가할 수 있다. | raw metric 결과를 보고 aligned metric 필요 여부를 판단한다. | 지표 |
| EVAL-05 | reprojection summary | metric | 구현 완료 | `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json`을 정답지로 사용한다. reprojection error summary는 정답 판정 기준이 아니라 triangulation quality 진단값으로 평가 결과에 함께 기록한다. | 없음 | GT 기준 수치와 reprojection summary의 상관만 추가 해석한다. | 평가 데이터, 지표 |
| EVAL-06 | 평가 출력 | output schema | 구현 완료 | `skeleton3d_evaluation.v1` artifact를 별도로 저장한다. | API response에서 summary와 full frame metrics를 더 나눌 필요는 추후 검토할 수 있다. | 긴 결과에서 summary/full metrics 분리 필요성만 관찰한다. | 평가 출력 |
| EVAL-07 | 고급 평가 | future scope | 보류 | 다중 인물, 3개 이상 카메라, temporal smoothing 후 평가는 첫 버전에서 제외한다. | 없음 | 첫 raw/summary metric 검증 뒤 별도 issue로 분리한다. | 보류 |

## 평가 데이터
- GT 파일: `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json`
- 원본 per-frame GT: `171204_pose1/171204_pose1/hdPose3d_2min/body3DScene_*.json`
- GT frame range: `118 ~ 3596`
- GT frame count: `3479`
- GT skeleton: COCO-19, 단위 cm
- EVAL-05 source of truth: 위 GT 파일과 원본 per-frame GT를 정답지로 사용한다. 합성기 output의 reprojection quality field는 evaluator가 읽을 수 있지만, 정답 판정 기준은 GT와의 3D 비교 결과다.

## 비교 대상
- 합성 결과 JSON의 `frames[].joints[]`
- 첫 버전은 `frameIndex` 기준으로 GT frame 과 1:1 매칭한다.
- `timestampMs`는 sanity check 로 사용한다.

## 관절 매핑
MediaPipe 33과 COCO-19가 직접 일치하지 않으므로 평가용 subset 을 먼저 정의한다.

초기 후보:
- nose
- left_shoulder / right_shoulder
- left_elbow / right_elbow
- left_wrist / right_wrist
- left_hip / right_hip
- left_knee / right_knee
- left_ankle / right_ankle
- left_eye / right_eye
- left_ear / right_ear

COCO-19의 `neck`, `mid_hip`은 MediaPipe 원본에 직접 없으므로 첫 평가에서는 제외하거나, 양쪽 어깨/엉덩이 평균으로 파생한다. 파생 관절은 원본 관절과 지표를 분리해 기록한다.

## 지표
- MPJPE: 매칭 가능한 관절의 평균 3D 거리 오차
- median joint error
- p95 joint error
- frame-level valid joint ratio
- reprojection error summary: triangulation 입력 2D 관측값에 대한 재투영 진단값이며, GT 정답지와의 3D 정확도 지표를 대체하지 않는다.
- 실패 관절/프레임 수

## 좌표계 확인
- Panoptic GT 단위는 cm 이다.
- 캘리브레이션 `t`도 cm 로 문서화되어 있다.
- 합성 결과 좌표계가 GT와 같은 world coordinate 인지 먼저 검증한다.
- 축 방향 또는 원점 차이가 발견되면 alignment 변환을 별도 기록하고, raw metric 과 aligned metric 을 분리한다.

## 평가 출력
- `evaluationInfo`
  - GT ref
  - camera pair
  - frame range
  - mapping version
- `metrics`
  - MPJPE, median, p95
  - valid frame/joint ratios
  - reprojection summary
- `frames`
  - frameIndex
  - per-joint error
  - failure reasons

## 보류
- 다중 인물 평가
- 3개 이상 카메라 결과 비교
- learned correction 또는 temporal smoothing 후 평가
- 분석 파이프라인 결과 품질과의 직접 상관 분석
