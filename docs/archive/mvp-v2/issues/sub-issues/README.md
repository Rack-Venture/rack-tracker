# MVP v2 Sub-Issue Documents

## 역할
- 이 폴더의 루트에는 issue 또는 chore 단위의 관리 문서를 둔다.
- 특정 issue 안에서 파생되는 설계 문서, 실행 계획, 평가 계획은 같은 이름의 하위 폴더에 둔다.
- 커밋 단위 작업 로그는 루트의 관리 문서에만 기록하고, 하위 폴더 문서는 설계 판단과 구현 순서를 담는다.

## 현재 구조
| 경로 | 역할 | 관계 |
|------|------|------|
| `26-chore-clean-up-repository-before-mvp-v2.md` | 저장소 정리 관리 문서 | #25 하위 cleanup 작업 |
| `29-feat-dual-video-skeleton-3d-synthesis-experiment.md` | 3D 합성 실험 관리 문서 | #25 하위, GitHub #29 |
| `29-feat-dual-video-skeleton-3d-synthesis-experiment/` | #29 파생 설계 문서 묶음 | #29 관리 문서의 하위 참고 문서 |
| `41-feat-3d-synthesis-streaming-pipeline.md` | 3D 합성 청크 스트리밍 통합 관리 문서 | #25 하위, GitHub #41, #29 STR-04/STR-06 후속 |
| `42-feat-preset-estimation-json-input.md` | preset JSON 입력으로 추론 생략 관리 문서 | #25 하위, GitHub #42, #41 후속 |
| `43-feat-unified-synthesis-pipeline.md` | 단일 synthesis 파이프라인 통합 관리 문서 | #25 하위, GitHub #43, #41/#42 후속 |

## 정리 기준
- `Parent: #...`가 있고 work log를 갖는 문서는 루트에 둔다.
- 하나의 관리 문서에서 파생된 상세 설계 문서는 하위 폴더로 묶는다.
- 파일명은 하위 폴더 안에서는 짧게 유지하되, 폴더명이 부모 issue를 식별하게 한다.
- 설계 문서 사이에 선후관계가 있으면 하위 폴더의 `README.md`에 읽는 순서를 명시한다.

## #29 문서 읽는 순서
1. `29-feat-dual-video-skeleton-3d-synthesis-experiment.md`
2. `29-feat-dual-video-skeleton-3d-synthesis-experiment/README.md`
3. `29-feat-dual-video-skeleton-3d-synthesis-experiment/streaming-pipeline-plan.md`
4. `29-feat-dual-video-skeleton-3d-synthesis-experiment/3d-skeleton-synthesizer-plan.md`
5. 이후 구현 단계에 따라 triangulation, GT 평가, 렌더링, API/분석 연결 문서를 읽는다.
