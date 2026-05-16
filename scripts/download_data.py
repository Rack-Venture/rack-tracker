"""
Large data file downloader — Google Drive 기반.

사용법:
    python scripts/download_data.py            # 누락된 파일만 다운로드
    python scripts/download_data.py --force    # 이미 있어도 덮어쓰기

등록 방법 (팀 관리자):
    1. 파일을 Google Drive에 업로드
    2. 우클릭 → '링크 보기' → '링크가 있는 모든 사용자'로 설정
    3. 공유 URL에서 파일 ID 복사
       예: https://drive.google.com/file/d/XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX/view
                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    4. 아래 MANIFEST의 "id" 항목에 붙여넣기
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─── 파일 목록 ──────────────────────────────────────────────────────────────
# id: Google Drive 파일 ID  (공유 URL에서 추출)
# dest: 레포 루트 기준 상대경로  (이 경로에 파일이 저장됨)
# desc: 설명 (표시용)
MANIFEST: list[dict] = [
    {
        "id": "REPLACE_WITH_GOOGLE_DRIVE_FILE_ID",
        "dest": "171204_pose1/171204_pose1/calibration_171204_pose1.json",
        "desc": "Panoptic CMU 171204_pose1 카메라 캘리브레이션 파일 (합성 기능 필수)",
    },
    # 추가 파일은 같은 형식으로 여기에 등록
    # {
    #     "id": "REPLACE_WITH_ID",
    #     "dest": "171204_pose1/171204_pose1/hdVideos_2min/hd_00_21_2min.mp4",
    #     "desc": "카메라 A 2분 클립",
    # },
]
# ────────────────────────────────────────────────────────────────────────────

GDRIVE_BASE = "https://drive.google.com/uc?export=download&id="


def _gdrive_url(file_id: str) -> str:
    return GDRIVE_BASE + file_id


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  다운로드 중: {url}")
    try:
        urllib.request.urlretrieve(url, dest)
    except Exception as e:
        print(f"  [오류] 다운로드 실패: {e}", file=sys.stderr)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="대용량 데이터 파일 다운로드")
    parser.add_argument("--force", action="store_true", help="이미 존재하는 파일도 덮어쓰기")
    args = parser.parse_args()

    placeholder = "REPLACE_WITH_GOOGLE_DRIVE_FILE_ID"
    errors: list[str] = []

    for entry in MANIFEST:
        file_id: str = entry["id"]
        dest = REPO_ROOT / entry["dest"]
        desc: str = entry["desc"]

        print(f"\n[{desc}]")
        print(f"  대상: {entry['dest']}")

        if file_id == placeholder:
            print("  [건너뜀] Google Drive 파일 ID가 아직 등록되지 않았습니다.")
            print("  → scripts/download_data.py의 MANIFEST에 파일 ID를 입력하세요.")
            continue

        if dest.exists() and not args.force:
            print(f"  [건너뜀] 이미 존재합니다 (--force로 덮어쓰기 가능)")
            continue

        try:
            _download(_gdrive_url(file_id), dest)
            print(f"  완료: {dest.relative_to(REPO_ROOT)}")
        except Exception:
            errors.append(entry["dest"])

    if errors:
        print(f"\n[실패] 다음 파일을 다운로드하지 못했습니다:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print("\n모든 파일 처리 완료.")


if __name__ == "__main__":
    main()
