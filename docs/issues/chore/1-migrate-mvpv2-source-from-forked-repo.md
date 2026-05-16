# [CHORE] 기존 개인 레포에서 mvpv2 소스 및 워크플로우 문서 마이그레이션 (#1)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/chore/`.
- Update this document before each related commit.

## Summary
rack-tracker-forked(개인 작업 레포)에서 팀 협업 레포(rack-venture-rack-tracker)로 mvpv2 소스 및 운영 문서를 이식한다.

## Goal
- frontend, backend, docs/mvp-v2, 171204_pose1(git 추적분) 복사
- .gitignore 작성
- 팀원 투입 가능한 상태로 초기화

## Scope
- frontend/ (node_modules, dist 제외)
- backend/ (.venv, __pycache__, tmp 제외)
- docs/mvp-v2/
- 171204_pose1/ git 추적 파일 5개만
- .gitignore

## Out Of Scope
- docs/agent-workflow/ 4개 겹치는 파일 — venture 버전 유지
- docs/agent-workflow/ 신규 2개 파일 — 스킵
- 171204_pose1/ 영상/대용량 데이터 — 별도 공유

## Done Criteria
- git status 기준 추적 대상 파일 이상 없음
- frontend npm install, backend uv sync 정상 동작

---

## Work Log

### chore: mvpv2 소스 및 워크플로우 문서 마이그레이션 (#1)

> rack-tracker-forked에서 frontend, backend, docs/mvp-v2, 171204_pose1(git 추적분), .gitignore를 이식

#### Scope
- frontend/, backend/, docs/mvp-v2/, 171204_pose1/ git 추적 5개 파일, .gitignore

#### Changes
- frontend/ 86개 파일 복사 (node_modules, dist 제외)
- backend/ 95개 파일 복사 (.venv, __pycache__, tmp 제외)
- docs/mvp-v2/ 42개 파일 복사
- 171204_pose1/ git 추적 파일 5개만 복사 (영상/대용량 제외)
- .gitignore 신규 작성 (소스 기준, poseLandmarker_Python 등 불필요 레거시 경로 제거)
- docs/agent-workflow/ 겹치는 4개 파일 → venture 버전 유지 (더 최신)
- docs/issues/chore/1-migrate-mvpv2-source-from-forked-repo.md 관리 문서 신규 생성

#### Verification
- git add --dry-run 기준 node_modules, .venv, __pycache__, dist, .task 미포함 확인

#### Notes
- docs/agent-workflow/ 신규 2개 파일(agent-commit-and-push-workflow.md, git-collaboration-convention.md)은 스킵 (git-rules.md가 커버)
- 171204_pose1 영상/대용량 데이터는 별도 공유 예정

