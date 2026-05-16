# [CHORE] pre-commit 훅 추가 — 관리 문서 누락 방지 (#5)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/chore/`.
- Update this document before each related commit.

## Summary
파일 변경 커밋 시 관리 문서가 함께 업데이트됐는지 검사하는 pre-commit 훅을 추가한다.
rack-tracker-forked의 동일 훅을 이 레포 경로 구조에 맞게 이식한다.

## Goal
- 관리 문서 없이 커밋 시 pre-commit에서 차단
- 온보딩 문서에 훅 활성화 방법 안내

## Scope
- `.githooks/pre-commit` 추가
- `scripts/check-management-doc-update.ps1` 추가
- `docs/onboarding.md`에 훅 활성화 단계 추가

## Out Of Scope
- check-requirements-doc-pairs.ps1 (구 레포 전용, 이식 불필요)
- CI 레벨 훅 강제

## Done Criteria
- [x] 관리 문서 없이 커밋 시 차단됨
- [x] 온보딩 문서에 `git config core.hooksPath .githooks` 안내 추가

---

## Work Log

### chore: pre-commit 훅 추가 — 관리 문서 누락 방지 (#5)

> rack-tracker-forked 훅을 이식하고 docs/issues/ 경로 패턴에 맞게 수정

#### Changes
- `.githooks/pre-commit` 신규 추가
- `scripts/check-management-doc-update.ps1` 신규 추가 (패턴: `docs/issues/[^/]+/.+\.md`)
- `docs/onboarding.md` — 훅 활성화 단계 추가

---

## Management Notes

### References
- GitHub Issue: #5
- rack-tracker-forked/.githooks/pre-commit (원본)
