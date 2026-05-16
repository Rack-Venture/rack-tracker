# [DOCS] 이슈 관리 문서 경로 정책 명문화 (아카이브 vs 신규) (#2)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/docs/`.
- Update this document before each related commit.

## Summary
rack-tracker-forked에서 마이그레이션한 docs/mvp-v1/, docs/mvp-v2/ 하위 이슈 관리 문서들은 구 레포 이슈 번호 기준의 과거 이력 아카이브다. rack-venture 신규 체계(docs/issues/)와 혼재하므로 documentation-rules.md에 구분 정책을 명문화한다.

## Goal
- documentation-rules.md에 아카이브 체계와 신규 체계 구분 규칙 추가

## Scope
- docs/agent-workflow/documentation-rules.md

## Out Of Scope
- docs/mvp-v1/, docs/mvp-v2/ 파일 내용 수정 — 아카이브이므로 그대로 유지

## Done Criteria
- 아카이브/신규 체계 구분이 documentation-rules.md에 명시됨

---

## Work Log

### docs: 이슈 관리 문서 경로 정책 명문화 — 아카이브 vs 신규 (#2)

> documentation-rules.md에 구 레포 아카이브(docs/mvp-v1/, docs/mvp-v2/)와 rack-venture 신규 관리 문서(docs/issues/) 체계 구분 규칙 추가

#### Scope
- docs/agent-workflow/documentation-rules.md: Archive Policy 섹션 추가

#### Changes
- `## Archive Policy` 섹션 신설
  - docs/mvp-v1/, docs/mvp-v2/ = 구 레포 이슈 번호 기준 과거 이력 아카이브, 수정 금지
  - docs/issues/ = rack-venture GitHub 이슈 기준 신규 관리 문서 위치
  - 새 작업 시 rack-venture 이슈 먼저 생성 → docs/issues/{type}/{N}-{slug}.md 생성 순서 명시

#### Verification
- documentation-rules.md 내용 검토

#### Notes
- 이슈 번호 불일치 문제는 mvp-v1/v2가 모두 완료된 과거 이력이므로 소급 수정 불필요
