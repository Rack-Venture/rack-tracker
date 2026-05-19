# [CHORE] 171204_pose1 디렉토리 구조 정리 (#9)

## Document Relations
- This document tracks one issue-sized work item.
- File name matches the issue branch name without the type prefix.
- Placed under `docs/issues/chore/`.
- Update this document before each related commit.

## Summary
`171204_pose1/171204_pose1/` 이중 중첩 구조를 평탄화하고, 역할이 끝난 `trim_hd_videos.py`를 삭제한다.

## Goal
- `171204_pose1/` 바로 아래에 스크립트·메타데이터가 위치하도록 구조 정리
- 불필요한 파일 제거

## Scope
- `171204_pose1/171204_pose1/` 내용물을 `171204_pose1/`로 이동
- `trim_hd_videos.py` 삭제

## Out Of Scope
- `prepare_gt_aligned_clips.py`, `hdVideos_2min/`, `hdVideos_gt_aligned/` 내용 변경

## Done Criteria
- `171204_pose1/` 바로 아래에 `prepare_gt_aligned_clips.py`, `hdVideos_2min/`, `hdVideos_gt_aligned/` 존재
- `trim_hd_videos.py` 미존재
- `171204_pose1/171204_pose1/` 하위 폴더 미존재

---

## Work Log

### chore: 171204_pose1 디렉토리 중첩 제거 및 trim 스크립트 삭제 (#9)

> 이중 중첩된 폴더 구조를 평탄화하고 일회성 전처리 스크립트 제거

#### Scope
- `171204_pose1/171204_pose1/` → `171204_pose1/` 평탄화
- `trim_hd_videos.py` 삭제

#### Changes
- `171204_pose1/171204_pose1/prepare_gt_aligned_clips.py` → `171204_pose1/prepare_gt_aligned_clips.py`
- `171204_pose1/171204_pose1/hdVideos_2min/` → `171204_pose1/hdVideos_2min/`
- `171204_pose1/171204_pose1/hdVideos_gt_aligned/` → `171204_pose1/hdVideos_gt_aligned/`
- `171204_pose1/171204_pose1/trim_hd_videos.py` 삭제

#### Verification
- `171204_pose1/` 하위 구조 확인
- `trim_hd_videos.py` 미존재 확인

#### Notes
- `hdVideos_2min/`은 구글 드라이브에 업로드 완료 예정, 원본 재트리밍 계획 없음
- `prepare_gt_aligned_clips.py`는 드라이브에서 받은 후 `hdVideos_gt_aligned/` 재생성에 필요하므로 유지

---

## Management Notes

### References
- #9 이슈
