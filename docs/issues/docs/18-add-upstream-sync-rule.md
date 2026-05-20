# 18-add-upstream-sync-rule

## Issue
https://github.com/Rack-Venture/rack-tracker/issues/18

## Goal
로컬 develop 업데이트 시 upstream/develop 기준으로 fetch/merge해야 한다는 규칙이 git-rules.md에 누락되어 있어 추가한다.

## Scope
- `docs/agent-workflow/git-rules.md`에 `## Local Develop Sync Rules` 섹션 추가

## Done Criteria
- [x] 로컬 develop 업데이트 시 `upstream/develop` 기준으로 fetch/merge해야 함이 명시됨
- [x] origin 싱크 방법도 함께 명시됨

## Work Log

## docs: add local develop sync rules to git-rules (#18)

- `## Local Develop Sync Rules` 섹션 추가
- 로컬 develop은 항상 `upstream/develop`에서 fetch/merge
- origin 싱크는 matching push로 유지
