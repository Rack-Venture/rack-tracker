# Agent Workflow Templates

## Document Relations

- Parent index: `docs/agent-workflow/README.md`
- Related rule summaries:
  - `docs/agent-workflow/git-rules.md`
  - `docs/agent-workflow/documentation-rules.md`

## Issue Placeholder

- Use `#<issue-number>` until GitHub assigns the real number.

## Branch Placeholder

- Use `type/<issue-number>-short-description` until GitHub assigns the real issue number.

## Branch Examples

- `feature/12-rack-registration-api`
- `fix/34-login-token-expiry`
- `refactor/21-auth-middleware`
- `docs/8-readme-update`
- `chore/5-project-setup`

## Commit Message Template

```text
type: 변경 내용 요약 (#이슈번호)

- 세부 변경 사항 1
- 세부 변경 사항 2
```

## Issue Template

```text
[TYPE] 작업 내용 요약

## 작업 목적
이 작업이 왜 필요한지 설명한다.

## 작업 내용
- 구현하거나 수정할 항목
- 변경 사항

## 완료 조건
- 이 기준을 충족하면 작업 완료로 간주한다

## 참고 자료
관련 링크, 문서, 관련 Issue 번호
```

## PR Title Template

```text
[TYPE] 작업 내용 요약 (#이슈번호)
```

## PR Description Template

```text
## 관련 Issue
Closes #이슈번호

## 작업 내용
- 구현하거나 수정한 내용
- 주요 변경 사항

## 변경 사항 상세
- 코드 구조 변경 내용
- 신규 모듈 또는 API

## 테스트 방법
1. 실행 방법
2. 확인해야 할 시나리오

## 스크린샷 (선택)
```

## Management Document Path Examples

- `docs/issues/feature/12-rack-registration-api.md`
- `docs/issues/fix/34-login-token-expiry.md`
- `docs/issues/refactor/21-auth-middleware.md`
- `docs/issues/docs/8-readme-update.md`
- `docs/issues/chore/5-project-setup.md`

## Path Rule

- Use repository-relative paths in workflow docs, templates, and management documents.
- Do not write absolute local filesystem paths such as `C:/...` into reusable workflow rules.

## Issue Management Document Template

```text
# [TYPE] 작업 내용 요약 (#이슈번호)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/type/`.
- Update this document before each related commit.

## Summary
Short context for the issue.

## Goal
- What this issue needs to achieve

## Scope
- Planned implementation scope

## Out Of Scope
- Explicit non-goals

## Done Criteria
- Conditions that mark the issue complete

---

## Work Log

### type: 변경 내용 요약 (#이슈번호)

> One-line description of what changed and why

#### Scope
#### Changes
#### Verification
#### Notes

---

## Management Notes

### Follow-up Candidates
- Items deferred for later issues

### Notes
- Decisions, constraints, or risks worth preserving

### References
- Related issues, docs, or links
```
