# [DOCS] 팀 온보딩 문서 추가 및 포트·환경변수 통일 (#4)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/docs/`.
- Update this document before each related commit.

## Summary
레포를 포크한 팀원이 로컬 환경을 빠르게 세팅할 수 있도록 온보딩 문서를 작성하고,
포트 불일치 및 환경변수 예시 파일 누락 문제를 함께 정리한 작업이다.

## Goal
- 포크 후 온보딩 문서만 따라가면 프론트·백엔드 모두 실행 가능한 상태
- 프론트엔드 VITE_API_BASE_URL과 백엔드 PORT를 8000으로 통일

## Scope
- docs/onboarding.md 신규 작성
- 포트 통일: backend/config/config.py, frontend/.env.local
- frontend/.env.local.example 신규 추가
- backend/.env.example에 RELOAD=0 추가
- .gitignore에 .env.local.example 예외 추가

## Out Of Scope
- CI/CD 파이프라인 구성
- Node.js 버전 고정(.nvmrc 등)

## Done Criteria
- [x] docs/onboarding.md 작성 완료
- [x] 포트 8000으로 통일
- [x] frontend/.env.local.example 추가 및 git 추적

---

## Work Log

### docs: 팀 온보딩 문서 추가 및 포트·환경변수 통일 (049532c)

> 포크 후 세팅 절차를 문서화하고, 포트 불일치와 환경변수 예시 파일 누락을 함께 수정

#### Changes
- `docs/onboarding.md` 신규 작성 — 사전 설치, 프론트/백엔드 세팅, 데이터 다운로드, 에이전트 워크플로우, 체크리스트 포함
- `backend/config/config.py` — 기본 PORT 8080 → 8000
- `backend/.env.example` — RELOAD=0 추가
- `frontend/.env.local.example` 신규 추가 (VITE_API_BASE_URL=http://127.0.0.1:8000)
- `.gitignore` — .env.local.example 예외 추가

#### Notes
- `frontend/.env.local`(git-ignored)은 기존에 PORT=9000으로 설정되어 있었음 — 로컬에서 직접 수정 필요
- `backend/.env`(git-ignored)도 동일하게 PORT=9000이었음 — 로컬에서 직접 수정

---

## Management Notes

### Follow-up Candidates
- .nvmrc로 Node.js 버전 고정
- CI/CD 파이프라인 구성

### References
- GitHub Issue: #4
