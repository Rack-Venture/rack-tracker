# [CHORE] 구 레포 아카이브 docs/archive/로 이동 및 rack-venture mvp-v2 문서 공간 신설 (#6)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/chore/`.
- Update this document before each related commit.

## Summary
docs/mvp-v1, docs/mvp-v2는 rack-tracker-forked 마이그레이션 아카이브다.
rack-venture 신규 작업 문서와 섞여 있어 docs/archive/로 이동하고,
rack-venture 전용 docs/mvp-v2/를 새로 만든다.

## Goal
- 아카이브와 신규 작업 문서 공간을 명확히 분리
- rack-venture 전용 mvp-v2 문서 공간 확보

## Scope
- docs/mvp-v1/ → docs/archive/mvp-v1/
- docs/mvp-v2/ → docs/archive/mvp-v2/
- docs/mvp-v2/ 신규 생성 (rack-venture 전용 README)
- docs/agent-workflow/documentation-rules.md 아카이브 경로 업데이트

## Out Of Scope
- 아카이브 내부 문서 내용 수정
- 아카이브 내 구 이슈 번호 수정

## Done Criteria
- [x] docs/archive/mvp-v1/, docs/archive/mvp-v2/ 이동 완료
- [x] docs/mvp-v2/ rack-venture 전용 공간으로 신설
- [x] documentation-rules.md 경로 반영

---

## Work Log

### chore: 구 레포 아카이브 docs/archive/로 이동 및 rack-venture mvp-v2 신설 (#6)

> docs/mvp-v1, docs/mvp-v2를 docs/archive/로 이동하고 rack-venture 전용 mvp-v2 공간 생성

#### Changes
- `docs/mvp-v1/` → `docs/archive/mvp-v1/` (git mv)
- `docs/mvp-v2/` → `docs/archive/mvp-v2/` (git mv)
- `docs/mvp-v2/README.md` 신규 생성 (rack-venture 전용)
- `docs/agent-workflow/documentation-rules.md` 아카이브 경로 업데이트

---

## Management Notes

### References
- GitHub Issue: #6
