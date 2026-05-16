# MVP v2 Tracking — #25

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 issue 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 issue 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 issue 문서의 matrix도 갱신한다.
- 하위 issue 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 issue 문서다.

## Plan Integration Matrix

| ID | 구분 | 하위 문서 | 상태 | 결정된 방향 | 연동 대상 | 갱신 필요 사항 | 다음 액션 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MVP2-01 | 저장소 정리 | `../sub-issues/26-chore-clean-up-repository-before-mvp-v2.md` | 검증 완료 | MVP v2 구현 전 legacy, archive, docs 진입점, workflow 규칙을 정리했다. | workflow docs, docs index, active implementation paths | workflow 규칙이나 문서 진입점이 다시 바뀌면 #26 문서와 관련 workflow docs 갱신 | 완료 상태 유지, 후속 정리는 별도 issue로 분리 |
| MVP2-02 | 듀얼 비디오 3D 합성 실험 | `../sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md` | 검증 완료 | 두 동영상 2D skeleton artifact를 기반으로 batch 3D synthesis, triangulation, synthesis API, debug/evaluation artifact, Three.js 검증 viewer baseline을 구현하고 실험 결론을 문서화했다. | streaming pipeline, 3D synthesis, triangulation, rendering, API, GT evaluation, viewer floor fix | #29 실험 baseline 이후 camera rig/session world, browser visual regression, 3D analysis adapter 요구사항이 바뀌면 후속 issue에서 갱신 | #29 종료. product-grade rack/session-world pipeline은 별도 issue로 분리 |

## 현재 요약
- #26 저장소 정리와 workflow/document entry-point 정리는 검증 완료 상태로 유지한다.
- #29는 MVP2-02 실험 범위에서 종료한다. 남은 production-grade 3D motion pipeline, camera rig/session world, visual regression, 3D analysis adapter는 별도 이슈로 분리한다.

## 배경
이 이슈는 `MVP v2` 전체 작업을 추적하기 위한 상위 이슈다.
v2의 목표는 기능을 추가하는 것에 그치지 않고, 이후 확장과 유지보수가 쉬운 구조를 만드는 데 있다.

## 목표
- `MVP v2`의 방향과 범위를 명확히 정리한다.
- 핵심 사용자 흐름, 기능, 내부 구조를 개선한다.
- 구현 작업을 독립적으로 진행 가능한 하위 이슈 단위로 분해한다.

## 포함 범위
- `MVP v2`와 직접 관련된 기능 작업
- 플레이어 동작 방식과 상태 흐름 개선
- 유지보수성과 확장성을 높이는 구조 개선
- 작업을 지원하기 위해 필요한 수준의 문서화

## 제외 범위
- `MVP v2`를 직접 지원하지 않는 탐색성 작업
- 우선순위가 낮은 UI polish
- 다음 버전에서 다루는 편이 적절한 아이디어
- 범위를 크게 늘리는 신규 기능 제안

## 성공 조건
- `MVP v2` 핵심 작업이 하위 이슈로 분해되어 명확히 추적된다.
- 주요 사용자 흐름에서 기대 동작이 일관되게 유지된다.
- 구조 변경과 그 배경을 쉽게 추적할 수 있다.
- 남은 리스크와 후속 과제가 분리되어 정리된다.

## 진행 원칙
- 이 문서는 `MVP v2`의 상위 umbrella 이슈로 사용한다.
- 구현, 검증, 리뷰는 하위 이슈 단위로 진행한다.
- 범위 변경, 결정사항, 공통 리스크는 이 문서에 기록한다.
- 각 PR은 관련 하위 이슈를 연결하고, 필요하면 이 상위 이슈도 함께 참조한다.

## 리스크
- 구현 중 범위가 계속 커질 수 있다.
- 구조 변경 과정에서 기존 동작이 회귀할 수 있다.
- 기반 작업과 사용자 가시 기능 사이에서 우선순위가 흔들릴 수 있다.

## 하위 이슈
- #26 [chore] Clean up repository before MVP v2
- #29 [feat] 두 동영상 스켈레톤 추출 및 3D 합성 기반 실험
