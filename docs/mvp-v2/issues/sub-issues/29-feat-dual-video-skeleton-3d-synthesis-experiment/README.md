# #29 Dual Video Skeleton 3D Synthesis Notes

## 문서 관계
- 부모 관리 문서: `../29-feat-dual-video-skeleton-3d-synthesis-experiment.md`
- 이 폴더는 #29의 파생 설계 문서만 담는다.
- 진행 로그, 커밋 단위 변경 기록, 승인 후 management log 는 부모 관리 문서에만 기록한다.
- 부모 관리 문서는 `Plan Integration Matrix`로 하위 plan 문서들의 통합 상태와 연동 위험을 추적한다.
- 각 하위 plan 문서는 `Implementation Status & Decision Matrix`로 자기 내부 구현 항목, 결정, 다음 액션을 추적한다.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## 상태 확인 순서
1. 부모 관리 문서의 `Plan Integration Matrix`에서 전체 plan 단위 상태를 확인한다.
2. 필요한 하위 plan 문서로 이동해 `Implementation Status & Decision Matrix`의 세부 항목을 확인한다.
3. 하위 plan에서 외부 계약, 상태, dependency가 바뀌면 부모 matrix의 해당 `PLAN-*` row를 함께 갱신한다.
4. 부모 matrix에서 우선순위나 연동 대상이 바뀌면 해당 하위 plan matrix의 관련 row를 함께 갱신한다.

## 문서 역할
| 부모 row | 문서 | 역할 |
| --- | --- | --- |
| PLAN-01 | `streaming-pipeline-plan.md` | 현재 2D 추출 파이프라인 상태, chunk streaming, artifact 생성 경계, synthesis handoff 전제를 정리한다. |
| PLAN-02 | `3d-skeleton-synthesizer-plan.md` | 3D 합성기의 중심 계약, output schema, orchestration, 분석 adapter 경계를 정리한다. |
| PLAN-03 | `triangulation-implementation-plan.md` | 두 2D 관측값과 camera model로 metric 3D 관절을 복원하는 최소 구현 계획을 정리한다. |
| PLAN-04 | `3d-skeleton-rendering-plan.md` | `skeleton3d.v1` 결과를 사람이 검증할 수 있는 Three.js viewer 요구사항을 정리한다. |
| PLAN-05 | `3d-synthesis-api-analysis-pipeline-plan.md` | synthesis API, job status, result 조회, 기존 분석 파이프라인 연결 방식을 정리한다. |
| PLAN-06 | `gt-evaluation-plan.md` | Panoptic Studio GT와 합성 결과를 비교하는 평가 입력, 매핑, 지표, 출력 artifact를 정리한다. |
| PLAN-07 | `3d-synthesis-redesign-review-plan.md` | 현재 3D 합성 결과를 다시 설계 검토하기 위해 2D 출력, 시점/위치 정렬, 두 시점 대조, triangulation, viewer 변환을 분리해 정리한다. |
| PLAN-08 | `viewer-floor-fix-plan.md` | Three.js Skeleton Viewer의 `computeMetricViewFrame` 버그를 수정한다. 발 관절 삼각측량 실패 시 얼굴 관절을 지면 기준으로 오용해 스켈레톤이 누워 보이는 현상의 원인, 수정 전략, 구현 범위를 정리한다. |

## 선후관계
1. 먼저 `streaming-pipeline-plan.md`로 현재 준비된 2D 추출 경로와 아직 미연결인 synthesis stage를 확인한다.
2. 그 다음 `3d-skeleton-synthesizer-plan.md`에서 첫 구현 범위, 입력 계약, output schema, artifact repository 경계를 확인한다.
3. `triangulation-implementation-plan.md`와 `gt-evaluation-plan.md`는 합성기 구현과 정확도 평가를 함께 설계하는 핵심 문서다.
4. 합성 결과가 기대와 다르게 나오면 `3d-synthesis-redesign-review-plan.md`에서 입력 산출물, 시점 정렬, 대조 검증, triangulation, viewer 변환을 먼저 분리 검토한다.
5. `3d-synthesis-api-analysis-pipeline-plan.md`는 합성기 output schema와 evaluation artifact가 안정될 때 API와 분석 연결 계약을 확정한다.
6. `3d-skeleton-rendering-plan.md`는 `skeleton3d.v1` 조회 API와 품질 필드가 안정된 뒤 검증 UI로 이어진다.

## 종료 판단
- #29는 두 동영상에서 2D skeleton을 추출하고, 두 시점 기반 3D synthesis artifact를 생성하며, API/debug/evaluation/viewer baseline을 연결하는 MVP 실험으로 종료한다.
- PLAN-07과 PLAN-08의 문서는 후속 productization 판단을 위한 진단 기록이다. 이 폴더에 보존하되, #29에서 camera rig/session world 전체 재설계까지 확장하지 않는다.
- MVP2-03/rack motion pipeline requirements 작업은 이 폴더와 #29 PR 범위에 포함하지 않는다.

## 현재 판단
- 첫 구현은 실시간 카메라 입력이 아니라 `171204_pose1/` stored videos 기반이다.
- 보존된 fixed fixture 기본 카메라 쌍은 `00_21 + 00_11`로 둔다.
- 첫 정합 기준은 timestamp-first 이고, `frameIndex`는 GT-aligned 실험 데이터의 sanity check와 디버깅 정보로만 쓴다.
- MediaPipe `z`는 첫 triangulation 계산에 사용하지 않는다.
- 3D 합성 결과는 기존 2D skeleton JSON과 분리된 별도 JSON으로 저장한다.
