# [docs] update backend/README.md after root README overhaul
Parent: —

## Document Relations
- This document tracks one issue-sized work item (#23).
- Keep this file name aligned with the issue branch name `23-docs-update-backend-readme`.
- Update this document before each related commit.
- Direct follow-up to #20/#21 (루트 README 전면 재작성). 루트 README 갱신 이후 `backend/README.md`가 옛 `poseLandmarker_Python` 시점에 그대로 머물러 있는 문제를 정리한다.
- Mirror of `rack-labs/rack-tracker#69`. 자매 저장소가 동일 후속 작업을 #69로 진행했고, 본 이슈는 그 결과를 본 저장소(상업 버전) 컨벤션에 맞춰 적용한다.

## Summary

본 저장소(`Rack-Venture/rack-tracker`)의 루트 `README.md`는 #20/#21로 자매 저장소 #65 양식이 적용되어 갱신 완료된 상태다. 그러나 `backend/README.md`는 옛 mvp-v1 시기 문서(`poseLandmarker_Python`) 그대로다. 본 이슈는 `backend/README.md`를 현재 코드 기준으로 전면 재작성해 루트 README와 정합되게 만든다.

자매 저장소(`rack-labs/rack-tracker`)는 동일 작업을 #69 PR로 진행했다. 본 작업은 그 결과를 본 저장소(상업 버전) 컨벤션에 맞춰 적용한다. 코드 구조(6-Layer, 라우터, 서비스 모듈)는 두 저장소가 동일하므로 본문 내용도 대부분 동일하다.

## Goal

- 신규 팀원·외부 기여자가 `backend/README.md`만 보고도 백엔드 정체성·구조·실행 절차·라우터·모듈 분포를 정확히 파악할 수 있게 한다.
- 루트 README의 톤(상업 버전 정체성 / 6-Layer / `/synthesis/jobs` 권장 경로)과 정렬되게 한다.

## Scope

- `backend/README.md` 전면 재작성
  - 제목·정체성: `poseLandmarker_Python` → **RackTracker Backend**
  - 옛 fork 절대경로(`C:\...\rack-tracker-forked\poseLandmarker_Python`) 전량 제거
  - 6-Layer(Entry / App / Controller / Service / Adapter / Schema) 구조 설명
  - 라우터: `/`, `/jobs`(deprecated), `/synthesis`, `/analysis`, `/rack-motion` 6개 모두 반영
  - `/synthesis/jobs` 권장 경로로 명시
  - 죽은 안내 섹션 제거: "현재 목업 비디오 동작", Node 워커 실험(검증 미완)
  - 비개발자 친화 톤은 일부 보존하되 분량 압축
  - 본 저장소가 상업 버전임을 상단에 한 줄 명시
- 관리 문서 `docs/issues/docs/23-docs-update-backend-readme.md` 신규 작성

## Out Of Scope

- `docs/archive/` 하위 README — 자매 저장소에서 마이그레이션된 문서로 archive 정책상 수정 금지.
- `frontend/` 자체 README 신설 — 별도 이슈에서 다룬다.
- `backend/read_docs.py` 제거 — #14에서 별도 트래킹.
- 자매 저장소(`rack-labs/rack-tracker#69`)의 sub-issues README 표 보완 — 본 저장소에는 해당 파일이 archive 안에만 존재(수정 금지)하므로 적용 불가.

## Done Criteria

- `backend/README.md`에서 옛 경로(`poseLandmarker_Python`, `rack-tracker-forked`)가 사라진다.
- `/synthesis/jobs`, `/analysis/preview`, `/rack-motion`이 `backend/README.md`에 명시된다.
- `backend/README.md`가 6-Layer 구조를 따라 정리된다.
- 옛 fork 절대경로 예시가 사라진다.
- 본 저장소가 상업 버전이라는 점이 backend/README 상단에서 한 번 언급된다.

---

## Work Log

### docs: update backend/README.md after root overhaul (#23)

> 루트 README(#20/#21) 후속. `backend/README.md`를 현재 코드 기준으로 전면 재작성. 자매 저장소(`rack-labs/rack-tracker#69`)와 동일 골격에 본 저장소(상업 버전) 정체성과 자매 특유 자산을 반영.

#### Scope
- `backend/README.md` 전면 재작성 (−406 / +173)
- `docs/issues/docs/23-docs-update-backend-readme.md` 관리 문서 신규

#### Changes
- **`backend/README.md`** — mvp-v1 시기에 작성된 옛 `poseLandmarker_Python` 문서를 현재 코드 기준으로 전면 재작성.
  - 제목·정체성: `poseLandmarker_Python` → **RackTracker Backend**.
  - 상업 버전 callout 1줄 추가: 본 저장소가 `Rack-Venture/rack-tracker`이며 자매 `rack-labs/rack-tracker`(졸업 프로젝트 전용)와 백엔드 구조는 동일함을 명시.
  - 옛 fork 절대경로(`C:\...\rack-tracker-forked\poseLandmarker_Python`) 전량 제거.
  - 6-Layer(Entry / App / Controller / Service / Adapter / Schema) 표 추가.
  - 라우터 6개 모두 반영(`/`, `/jobs`*deprecated*, `/synthesis`, `/analysis`, `/rack-motion`), `/synthesis/jobs`를 권장 경로로 명시.
  - 비동기 Job 두 매니저(`job_manager`, `synthesis_job_manager`)와 State 흐름 정리.
  - Service 모듈을 영역별(Job orchestration / Frame&pose / 3D synthesis / Analysis / LLM / Repositories / Observability)로 묶어 표시.
  - 데이터 계약(`skeleton` / `analysis` / `llmFeedback` 3분할) 강조.
  - 죽은 섹션 제거: "현재 목업 비디오 동작(`src/video/backSquat.mp4`)", Node 워커 실험.
  - 비개발자 친화 톤은 "폴더 읽는 순서" / "데이터 분석 담당자 안내" 두 섹션에 압축 보존.
  - **자매 특유 자산** — "부속 디렉터리" 섹션 신설: `config/`, `fixtures/rack_motion/`, `scripts/run_3d_synthesis.py`, `src/preset_estimations/`, `tests/` (pytest), `docs/`.
  - 관련 문서 링크에 자매 `backend/docs/architecture/`, `docs/reference/`, `docs/testing.md` 반영.

#### Verification
- 백엔드 라우터 6개(`backend/controller/*.py`) 실재 확인 — README의 라우터 표와 일치.
- 백엔드 서비스 모듈 30개(`backend/service/*.py`) 실재 확인 — 영역별 모듈 분류와 일치.
- 백엔드 어댑터 2개(`backend/adapter/{mediapipe,opencv}_adapter.py`) 실재 확인.
- 백엔드 스키마 7개(`backend/schema/*.py`) 실재 확인.
- 부속 디렉터리(`config/`, `fixtures/rack_motion/`, `scripts/run_3d_synthesis.py`, `src/preset_estimations/`, `tests/`, `docs/architecture/`, `docs/reference/`, `docs/testing.md`) 실재 확인.

#### Notes
- 자매 저장소(`rack-labs/rack-tracker#69`)의 동일 작업과 골격은 동일하되, 본 저장소만의 자산(테스트, fixtures, scripts, config, docs/architecture 등)을 추가로 반영해 분량이 약간 더 큼(rack-labs +159 vs 본 +173).
- 본 저장소 `docs/archive/`는 자매 저장소에서 마이그레이션된 보존 문서이며 수정 금지. 따라서 자매 #69의 sub-issues README 표 보완 작업은 본 저장소에서는 대응 작업이 없음.

---

## Management Notes

### Follow-up Candidates
- `frontend/` 자체 README 신설.
- `backend/docs/optimization/` 문서의 외부 공개 노출 정책 검토.

### References
- `README.md` (루트, #20/#21로 갱신됨)
- `docs/issues/docs/20-docs-overhaul-readme.md`
- 자매 저장소: `rack-labs/rack-tracker#69`
- `AGENTS.md`, `CLAUDE.md`
