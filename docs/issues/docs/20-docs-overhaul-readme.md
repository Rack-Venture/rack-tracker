# [docs] overhaul README to reflect current backend/frontend state
Parent: —

## Document Relations
- This document tracks one issue-sized work item (#20).
- Keep this file name aligned with the issue branch name `20-docs-overhaul-readme`.
- Update this document before each related commit.

## Summary
본 저장소(`Rack-Venture/rack-tracker`)의 `README.md`는 임시 메모(`[임시 메모 - 추후 정리 필요]`)와 calibration JSON 등록 TODO만 담긴 stub 상태였다. 자매 저장소 `rack-labs/rack-tracker`에서 #65 PR로 정리한 README 구조를 본 저장소(상업 버전)에 동일하게 적용하되, (1) commercial 버전 정체성, (2) 두 저장소 운영 구조 차이, (3) 관리 문서 경로 `docs/issues/`, (4) 본 저장소의 실제 이슈·remote 설정을 반영했다.

## Goal
- 외부 방문자(잠재적 외부 기여자 포함)가 README 한 문서만으로 제품 정체성·범위·기술 스택·구성 요소·두 저장소 운영 구조를 정확히 파악할 수 있게 한다.
- 신규 팀원에게는 setup 절차를 `docs/onboarding.md`로 명확히 안내한다.
- 사업계획서 narrative와 일관된 product positioning을 README에서도 노출한다.

## Scope
- `README.md` 전면 재작성 (자매 저장소 #65 PR 양식 기반)
- 본 저장소 정체성(상업 버전) 명시: 두 저장소 비교 표 포함
- `docs/issues/docs/20-docs-overhaul-readme.md` 관리 문서 신규
- 사업계획서(`rack-venture/별첨_3`) 기반 프로젝트 개요 7개 하위 섹션
- 프론트엔드 별도 섹션 신설(스크린샷 placeholder 4곳)
- 협업 컨벤션 하단 이동, mermaid 차트 8종 포함
- 임시 메모(`[임시 메모 - 추후 정리 필요]`) 및 calibration JSON TODO 제거(calibration TODO는 follow-up issue로 트래킹).

## Out Of Scope
- `docs/onboarding.md` 자체 갱신 (#4에서 별도 관리).
- `scripts/download_data.py` 구현 또는 `MANIFEST` 채우기 (#16에서 별도 관리, calibration JSON 등록 후 해결 예정).
- `backend/README.md` 자체 갱신.
- 자매 저장소(`rack-labs/rack-tracker`)와의 sync 정책 자체 정의.
- CI/CD 도입.

## Done Criteria
- README가 현재 `backend/`, `frontend/` 디렉터리 구조와 일치한다.
- 본 저장소 정체성(상업 버전, 외부 인원 합류 가능, `Rack-Venture` org)이 README 상단과 [제품 정체성] 표에 명시되어 있다.
- 관리 문서 경로(`docs/issues/<type>/`)가 README의 [이슈 기반 작업 관리]·[문서 안내]에서 일관되게 사용된다.
- `docs/onboarding.md` 링크가 Setup 섹션 첫머리에서 노출된다.
- 협업 컨벤션은 README 하단부에 위치한다.
- 프론트엔드 섹션이 별도로 존재하며 스크린샷 `<!-- TODO -->` placeholder 4곳이 있다.
- mermaid 차트 8종(협업 / Repo / Branch / Code Review / Project Scope / Job State / Analysis Pipeline / 6단계 로드맵)이 모두 포함된다.
- 기존 임시 메모(`[임시 메모 - 추후 정리 필요]` 블록)는 README에서 제거된다.

---

## Work Log

### docs: overhaul README to reflect current state (#20)

> 자매 저장소 #65 양식을 본 저장소(상업 버전)에 적용. 두 저장소 운영 구조 명시, 관리 문서 경로 차이 반영, 임시 메모 제거.

#### Scope
- `README.md` 전면 재작성
- `docs/issues/docs/20-docs-overhaul-readme.md` 관리 문서 신규

#### Changes
- **상단 callout 신설** — 본 저장소가 `Rack-Venture/rack-tracker` 상업 버전임을 명시하고, 자매 저장소(`rack-labs/rack-tracker`, 졸프 전용)와의 운영 구조 차이를 안내.
- **프로젝트 개요** — 사업계획서(`rack-venture/별첨_3`) narrative 기반 7개 하위 섹션:
  - 제품 정체성: RackTracker(산출물) / RackLabs(연구·학술 개발팀) / RackVenture(사업화팀) 3분리 + 두 저장소 비교 표.
  - 한 줄 요약, 왜 만드는가(헬스장 5년 폐업률 82% · 이탈률 71% · Agency Problem · 2026 체육시설법 개정), 누구를 위해(소비자·트레이너·헬스장 3-side), 무엇이 다른가(비접촉·비전 / 프리웨이트 3D / 환경 표준화 / 데이터 락인 / 규제 대응 5축).
  - 기술 목표(저장소 관점), 6단계 실현 로드맵 mermaid + 본 저장소 매핑 표.
- **저장소 구조** — 본 저장소 실제 layout 반영: `docs/issues/`(활성 이슈 관리), `docs/archive/`(자매 저장소 레거시 보존본), `docs/mvp-v2/`, `scripts/download_data.py`, `171204_pose1/`, `.githooks/`.
- **팀 구성** — 졸프 팀원 5인 + 외부 인원 행 추가, 합류자 본인 행 직접 작성 안내.
- **백엔드 아키텍처** — 자매 저장소와 동일한 6-Layer 표 / Controller 6개 라우터 / Job state machine mermaid / Service 영역별 모듈 표 / Adapter / Schema / 통신 규약. 현재 코드 기준 작성.
- **프론트엔드 아키텍처 신설** — Vite + React 19 + three.js 스택, 4개 페이지 섹션, 공통 컴포넌트, features 훅, 스크린샷 `<!-- TODO -->` placeholder 4곳.
- **데이터 분석 파이프라인** — mermaid + 3분할 데이터 계약 유지.
- **팀 역할 매트릭스** — Core / Data Analyst / Frontend / AI·3D 4개 역할.
- **로컬 설정 축약** — `docs/onboarding.md` 링크 강조 + 핵심 명령 4줄. clone 예제의 upstream URL을 `Rack-Venture/rack-tracker.git`로 본 저장소에 맞춤. calibration JSON 등 git 미포함 자산은 `scripts/download_data.py` 참조 안내로 갈음.
- **문서 안내** — `docs/issues/<type>/` 경로(`chore/`, `docs/` 실재 + 향후 type별 추가)와 `docs/archive/` 안내 반영.
- **협업 프로세스 하단 이동** — 협업 mermaid / Convention First / Fork 구조 mermaid / Branch 전략 mermaid + 타입 표 / 커밋 / 이슈 / 코드 리뷰 mermaid 모두 유지. 관리 문서 경로 참조를 `docs/issues/`로 갱신, 브랜치 타입 예시는 본 저장소 실제 이슈 번호(`9-chore-...`, `20-docs-...`)로 교체.
- **임시 메모 제거** — 기존 README의 `[임시 메모 - 추후 정리 필요]` 블록(두 저장소 구조 설명 + calibration JSON TODO)을 제거. 두 저장소 구조는 새 [제품 정체성] 섹션이 흡수, calibration JSON TODO는 #16 등 별도 이슈에서 관리.

#### Verification
- 백엔드 라우터(`backend/app.py`)·컨트롤러 6개 파일(`controller/{analysis,health,jobs,rack_motion,results,synthesis}.py`)과 README의 엔드포인트 표 일치 확인.
- 백엔드 서비스 모듈(`backend/service/*.py`) 실재 파일 30개와 README 모듈 표 일치 확인.
- 프론트엔드 디렉터리(`frontend/src/App.jsx`, `frontend/src/components/sections/`, `frontend/package.json`) 실제 구조와 README 일치 확인.
- 모든 mermaid 차트 8종 유지 확인.
- `docs/onboarding.md` 경로 정확성 확인.
- 사업계획서 narrative 인용 수치(82% 폐업률, 71% 이탈률, 2026 체육시설법)는 `rack-venture/별첨_3` 원문과 대조해 그대로 옮김.
- 자매 저장소 README(`rack-labs/rack-tracker#65`)와 대조해 차이 항목(저장소 정체성 callout, 두 저장소 비교 표, 관리 문서 경로, upstream URL, 외부 인원 행)이 모두 반영되었는지 확인.

#### Notes
- mermaid 차트는 8종 모두 유지. 자매 저장소 #65에서 확정된 양식을 본 저장소에 그대로 적용.
- 프론트엔드 스크린샷은 사용자가 직후 PR/커밋으로 보충 예정. README에는 placeholder만 둔다(`frontend/src/assets/readme-source/` 경로 안내 포함).
- 두 저장소의 sync 방식(코드 변경을 어느 쪽에서 먼저 반영할지)은 본 작업 범위 외. 별도 운영 정책 문서가 필요해지면 follow-up issue로 분리.

### docs: replace placeholder team table with venture-specific 5-member roster (#20)

> 사업계획서(`rack-venture/별첨_3`) "팀 구성원 소개 및 역량" 섹션을 기준으로 본 저장소 실제 멤버 5인(이현규·김미루·이지원·전효원·전태웅)으로 팀 테이블을 교체. 자문·외부 협력 표 신설.

#### Scope
- `README.md` 팀 구성 표 전면 교체
- 자문·외부 협력 표 신설

#### Changes
- 팀 테이블 컬럼 확장: `프로필 / 이름 / 소속·신분 / 담당 영역 / 핵심 책임 / 약력` 6열.
- **이현규** (상명대 학생, Founder/Team Lead) — Core/AI·사업화. 포즈 추정·3D synthesis 파이프라인 설계·구현, 어댑터 레이어 분리 모듈형 아키텍처, FastAPI 비동기 처리. 약력: 경제금융학 + 휴먼AI공학(복수전공), 다국적 웹 에이전시 PM, 모두의연구소 응용소프트엔지니어링 이수, 2026-05-16 NVIDIA AI 코어 엔지니어 교육과정(SeSAC 서대문) 선발.
- **김미루** (상명대 학생) — Backend/DevOps. 백엔드 아키텍처·네트워크 인프라·DevOps 파이프라인·AI 데이터 처리 시스템.
- **이지원** (상명대 학생) — Frontend. 화면 구성·시각화·서비스 인프라.
- **전효원** (상명대 학생) — Data Analyst. 데이터 수집·정제 파이프라인, 분석 지표 설계, 사용자 행동 인사이트.
- **전태웅** (현대모비스 연구원, 학생 외) — Biomechanics R&D. 관절 정렬·움직임 궤적·반복 패턴·좌우 비대칭 등 운동 수행 품질 해석 로직 설계. 약력: University of Warwick 기계공학 석사, (전)한화에어로스페이스, (현)현대모비스 연구원.
- 안내 문구: 졸프 팀원(이현규·이지원·전효원)과 외부 인원(김미루·전태웅) 분리 명시. 자매 저장소(`rack-labs/rack-tracker`)는 졸프 전용이며 장효인·신은수가 그쪽에만 합류함을 명기. 약력 칸은 본인 공개 가능 범위로 한정 안내.
- 자문/외부 협력 표 신설: 윤희남 교수(상명대 — AI·컴퓨터비전 자문), (주)위니브(창업·서비스 기획 컨설팅), NVIDIA·SeSAC 서대문(AI 코어 엔지니어 교육과정 연계), 다국적 웹 에이전시(클라우드 인프라 자문).

#### Verification
- 사업계획서(`rack-venture/별첨_3`) 페이지 10–12 "팀 구성원 소개 및 역량"·"창업자의 역량" 원문과 5인 책임·약력 대조 확인.
- 사용자 확인(2026-05-20): 두 저장소 멤버 구분이 (rack-labs: 이현규·이지원·장효인·전효원·신은수 / rack-venture: 이현규·김미루·이지원·전효원·전태웅 / 공통: 이현규·이지원·전효원)임을 회신.

#### Notes
- 약력에 외부 사기업·표창·소속 등 민감 정보가 포함될 수 있으므로 README는 공개 정보 범위로 한정. 사업계획서에 기재된 이현규의 군 표창 사항(1성 장군, 강릉경찰서장, 강릉시장 표창)은 README 공개 본문에서는 생략.
- 외부 인원의 약력 칸은 본인 작성 영역으로 유지. 본 PR에서는 PDF에 명시된 공개 정보만 채움.

### docs: format 약력 column with bullet lists (#20)

> 팀 표의 약력 칸이 한 줄 문단으로 압축되어 가독성이 떨어졌다. 이현규·전태웅 행을 `<ul><li>` HTML 리스트로 분리해 학력·경력·자격 항목을 행별로 보이게 정리.

#### Scope
- `README.md` 팀 표의 이현규·전태웅 약력 셀에 `<ul><li>` 적용
- 사용자가 직접 적용한 `WUAL` 변경(자문/외부 협력 표)은 그대로 유지

#### Changes
- 이현규 약력: 한 문단 → 4-항목 리스트(상명대 복수전공 / 다국적 웹 에이전시 PM / 모두의연구소 응용소프트엔지니어링 / NVIDIA SeSAC AI 코어 엔지니어 과정).
- 전태웅 약력: 한 문단 → 4-항목 리스트(Warwick 기계공학 석사 / 한화에어로스페이스 / 현대모비스 / R&D 경험).
- 김미루·이지원·전효원 약력: 본인 작성 영역 그대로 유지(빈 상태).

#### Verification
- `<ul><li>` 마크업은 GitHub-flavored markdown 표 셀에서 정상 렌더됨을 가정. PR 머지 전 GitHub UI에서 렌더 결과 직접 확인 권장.

#### Notes
- `핵심 책임` 칸도 길이가 비슷하지만 본 작업 범위는 `약력`에 한정. 추후 동일 양식 적용이 필요하면 follow-up issue로 분리.

---

## Management Notes

### Follow-up Candidates
- 두 저장소(`rack-labs/rack-tracker` ↔ `Rack-Venture/rack-tracker`) 간 코드/문서 sync 정책 명문화.
- 자매 저장소에서 작성된 슬라이드 캡처 자산(`docs/etc/architecture-slides/`)을 본 저장소로 이식할지 정책 결정.
- README의 외부 인원 합류 row 가이드 강화(누가 어떤 정보를 채워야 하는지).
- calibration JSON Google Drive 등록 완료 후 `scripts/download_data.py` MANIFEST 채움 (#16과 연계).

### Notes
- 자매 저장소 PR: https://github.com/rack-labs/rack-tracker/pull/67 (#65)
- 본 저장소는 commercial 운영 정책에 따라 license/contributor 정책이 자매 저장소와 다르다. 정책 본문은 별도 문서로 분리하는 것이 적절하나, 본 작업은 README 갱신만 다룬다.

### References
- 자매 저장소 README PR: `rack-labs/rack-tracker#67`
- `docs/onboarding.md`
- `AGENTS.md`
- `docs/agent-workflow/templates.md`
- 사업계획서: `C:\Users\25\Documents\rack-venture\(별첨_3)RackVenture_사업계획서_올해의_k-스타트업_20260506.pdf`
