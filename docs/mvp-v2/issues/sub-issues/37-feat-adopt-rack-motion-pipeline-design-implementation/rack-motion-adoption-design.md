# Rack Motion Pipeline Adoption Design

## Purpose
Define the first rack-tracker-owned implementation slice for rack motion pipeline work. This document turns the #32 requirements baseline into concrete repository decisions without expanding into a full production pipeline.

## Current Repository Fit
- `backend/schema/` owns API and artifact contracts.
- `backend/service/` owns processing logic.
- `backend/tests/` already contains synthetic tests for triangulation and synthesis behavior.
- #29 produced an experimental `skeleton3d.v1` path, but rack motion work should use a separate rack-domain contract instead of extending that artifact implicitly.

## 하위 문서 관리 매트릭스
아래 문서들은 #32 요구사항 문서를 #37 구현 후보로 검토하기 위한 별도 단위이다. 각 문서는 사용자 검토와 방향 결정 전까지 구현 지시서가 아니라 채택 검토 문서로 취급한다.

| 순번 | 원본 참조 문서 | #37 검토 문서 | 검토 상태 | 구현 전 결정 |
| --- | --- | --- | --- | --- |
| 01 | `../32-feat-rack-motion-pipeline-requirements/01_pipeline_contract_ko.md` | `requirements-adoption-review/01-rack-tracker-pipeline-contract.md` | 작성됨, 검토 대기 | 파이프라인 단계별 채택, 보류, 제외 결정 |
| 02 | `../32-feat-rack-motion-pipeline-requirements/02_coordinate_spaces_ko.md` | `requirements-adoption-review/02-coordinate-spaces.md` | 작성됨, 검토 대기 | 공식 좌표계, 단위, transform 경계 결정 |
| 03 | `../32-feat-rack-motion-pipeline-requirements/03_data_shapes_ko.md` | `requirements-adoption-review/03-data-shapes.md` | 작성됨, 검토 대기 | artifact envelope, join key, schema shape 결정 |
| 04 | `../32-feat-rack-motion-pipeline-requirements/04_quality_metrics_ko.md` | `requirements-adoption-review/04-quality-metrics.md` | 작성됨, 검토 대기 | metric catalog, policy id, failure status 결정 |
| 05 | `../32-feat-rack-motion-pipeline-requirements/05_rack_tracker_requirements_ko.md` | `requirements-adoption-review/05-rack-tracker-requirements.md` | 작성됨, 검토 대기 | rack-domain entity, event, metric 우선순위 결정 |
| 06 | `../32-feat-rack-motion-pipeline-requirements/06_open_questions_ko.md` | `requirements-adoption-review/06-open-questions.md` | 작성됨, 검토 대기 | 열린 질문의 채택, 보류, 제외, risk 분류 |

### 동기화 장치
- #32 문서가 바뀌면 대응하는 #37 하위 검토 문서를 먼저 갱신한다.
- 사용자가 방향을 확정하면 하위 문서의 `결정 상태`와 이 매트릭스의 `구현 전 결정`을 함께 갱신한다.
- 구현 작업은 하위 검토 문서가 채택 항목과 보류 항목을 분리한 뒤 시작한다.
- #32 요구사항은 직접 구현으로 복사하지 않고, rack-tracker가 소유하는 명명, schema, service boundary, validation policy로 변환한 뒤 채택한다.

## First Implementation Slice
The first slice introduces a rack motion schema module with validation rules for:

- source-image 2D observations
- declared coordinate spaces
- 3D reconstruction targets
- rack anchors and support zones
- barbell endpoint entities
- per-artifact quality metrics

This slice deliberately stops before service orchestration, detector adapters, calibration import, persistence, or frontend rendering.

## Contract Decisions
- Use `rack_motion.*.v1` schema versions for rack-domain artifacts.
- Store persisted 2D observations in source-image pixel coordinates.
- Keep raw capture/reconstruction space separate from rack analysis space.
- Treat single-camera estimates as a different reconstruction mode from calibrated multi-camera results.
- Require multi-camera reconstruction records to identify at least two contributing cameras.
- Keep candidate rack events as data records with quality and policy ids rather than final judgments.

## Validation Strategy
Initial tests use synthetic in-memory records only. Tests should verify that invalid confidence values, invalid image sizes, invalid coordinate states, and under-specified multi-camera reconstruction records fail at schema validation time.

## Deferred Work
- Pipeline service orchestration from media inputs to rack analysis artifacts.
- Mapping existing `skeleton3d.v1` outputs into rack motion frames.
- Rack alignment service and rack-world transform estimation.
- Artifact repository persistence and API endpoints.
- Frontend rack motion visualization.
