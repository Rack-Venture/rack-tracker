# [CHORE] pre-push·commit-msg 훅 추가 (#11)

## Document Relations
- This document tracks one issue-sized work item.
- Placed under `docs/issues/chore/`.
- Update this document before each related commit.

## Summary
에이전트(Claude)가 git workflow 규칙을 어기는 push·commit을 로컬에서 차단한다.

## Goal
- upstream 직접 push 금지
- main/develop 직접 push 금지
- force push 금지
- 브랜치 이름 형식 경고
- 커밋 메시지 형식(`type: 설명 (#N)`) 강제

## Scope
- `.githooks/pre-push` 추가
- `.githooks/commit-msg` 추가
- `scripts/check-push-rules.ps1` 추가
- `scripts/check-commit-msg.ps1` 추가

## Out Of Scope
- PR base 브랜치 검증 (GitHub 서버 측 — 로컬 훅 범위 밖)

## Done Criteria
- upstream push 시 차단 및 오류 메시지 출력
- main/develop 직접 push 시 차단
- force push 시 차단
- 브랜치 이름 형식 위반 시 경고
- 커밋 메시지 형식 위반 시 차단

---

## Work Log

### chore: pre-push·commit-msg 훅 추가 (#11)

> push 규칙 및 커밋 메시지 형식을 로컬에서 강제하는 훅 추가

#### Scope
- `.githooks/pre-push`, `.githooks/commit-msg` 신규
- `scripts/check-push-rules.ps1`, `scripts/check-commit-msg.ps1` 신규

#### Changes
- `pre-push`: upstream push, main/develop 직접 push, force push 차단 / 브랜치 이름 형식 경고
- `commit-msg`: `type: 설명 (#N)` 형식 강제 (merge/revert 커밋 제외)

#### Verification
- `git push upstream ...` → 차단 확인
- `git push origin main` → 차단 확인
- force push 상황 시뮬레이션 → 차단 확인
- 잘못된 커밋 메시지 → 차단 확인

#### Notes
- PR base 검증은 로컬 훅으로 불가 — git-rules.md에 PR 생성 전 default branch 확인 절차 명시로 대응

---

## Management Notes

### References
- #11 이슈
- `docs/agent-workflow/git-rules.md`
