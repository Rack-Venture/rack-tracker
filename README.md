# rack-tracker

---

> **[임시 메모 - 추후 정리 필요]**
>
> ### 프로젝트 운영 구조
>
> 이 레포(`rackventure-racktracker`)는 **창업경진대회 출전용 상업 버전**이다.
>
> | 레포 | 목적 | 기여 가능 인원 |
> |------|------|--------------|
> | racklabs-racktracker | 졸업프로젝트(졸프) 전용 | 졸프 팀원만 |
> | **rackventure-racktracker** (이 레포) | 창업경진대회 출전용 | lacklabs 졸프 팀원 + 외부 인원 |
>
> **분기 이유:** 외부 팀원이 racklabs-racktracker를 건드리면 졸프 부정행위 이슈 발생 → 동일 코드베이스에서 출발하되 완전히 별도 운영 / rack-labs는 연구용 및 학술용이나 rack-venture는 상업용 오가니제이션. 만드는 제품의 목표와 지향점은 같으나, 라이선스와 같은 부분이 다름.
>
> MVP v2 뼈대는 이미 구성됨. 이후 팀 전원 투입 예정.
>
> ---
>
> ### [TODO] calibration JSON Google Drive 등록
>
> 합성(synthesis) 기능에 필요한 `171204_pose1/171204_pose1/calibration_171204_pose1.json` 파일은 용량 문제로 git에서 제외됨.
> 아래 절차로 Google Drive에 등록하면 팀원이 스크립트로 자동 다운로드할 수 있음.
>
> 1. 파일을 Google Drive에 업로드 → 공유 설정: '링크가 있는 모든 사용자'로 변경
> 2. 공유 URL에서 파일 ID 복사 — URL 형식: `https://drive.google.com/file/d/XXXXXXXX/view`
> 3. `scripts/download_data.py` 열기 → `MANIFEST`의 `"id": "REPLACE_WITH_GOOGLE_DRIVE_FILE_ID"` 부분에 파일 ID 붙여넣기 후 커밋
> 4. 팀원 로컬 세팅 시: `python scripts/download_data.py` 한 번 실행
>
> 추가 대용량 파일(영상 등)도 같은 방식으로 `MANIFEST`에 항목 추가.
> **등록 완료 후 이 메모 삭제.**

---
