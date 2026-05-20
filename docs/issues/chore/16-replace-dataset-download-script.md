# [CHORE] Replace dataset download script with gdown folder-based version
Parent: #16

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under the matching issue-type directory.
- Update this document before each related commit.

## Summary
기존 `scripts/download_data.py`는 파일별 Google Drive ID를 수동 등록하는 방식이었으나, 폴더 ID 하나로 전체 데이터셋을 일괄 다운로드하는 버전으로 교체한다.

## Goal
- `python scripts/download_data.py` 한 줄로 누락 파일만 다운로드되도록 한다.
- 팀원 어느 환경에서 실행해도 레포 루트 기준 올바른 경로에 파일이 배치된다.

## Scope
- `scripts/download_data.py` 교체

## Out Of Scope
- `.gitignore` 변경 없음
- README 업데이트 (별도 작업)

## Done Criteria
- `python scripts/download_data.py --list` 로 MANIFEST 출력 확인
- `python scripts/download_data.py` 로 누락 파일만 다운로드 확인
- `--force` 로 재다운로드 확인

---

## Work Log

### chore: replace dataset download script with gdown folder-based version (#16)

> 파일별 ID 등록 방식 → Drive 공유 폴더 기반 일괄 다운로드 방식으로 교체

#### Scope
- `scripts/download_data.py`

#### Changes
- `scripts/download_data.py`: `gdown.download_folder`로 Drive 공유 폴더에서 MANIFEST 기반 일괄 다운로드. `find_repo_root()`로 레포 루트 자동 설정. tar/zip 아카이브 자동 압축 해제. `--list` / `--force` 옵션 제공.

#### Notes
- `DRIVE_FOLDER_ID = "1NI81pbAQcow2z4LR6UDB-n54O00n528D"` 하드코딩 — 팀원 추가 설정 불필요
- `.gitignore`의 `171204_pose1/**` 규칙이 다운로드 대상 파일을 전부 제외함

---

## Management Notes

### References
- rack-tracker-forked #59 (동일 스크립트 포크 레포 적용)
