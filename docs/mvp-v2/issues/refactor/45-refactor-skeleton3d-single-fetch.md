# [refactor] skeleton3d 단일 요청 로딩으로 전환
Parent: #45

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under `docs/mvp-v2/issues/refactor/`.
- Update this document before each related commit.

---

## Summary

synthesis 완료 후 skeleton3d 데이터를 300프레임씩 페이지네이션으로 가져오던 방식을
단일 HTTP 요청으로 전체 데이터를 가져오는 방식으로 교체한다.

**기존 문제:**
- 백엔드는 skeleton3d.json 전체를 synthesis 완료 시 한 번에 기록한다
- 페이지 요청마다 파일 전체를 디스크에서 읽고 슬라이싱하여 반환한다
- 프론트엔드는 첫 페이지 + 나머지 prefetch 루프 + on-demand 추가 요청을 관리한다
- 유튜브처럼 점진적 로딩되는 UX가 발생하나 실질적 이점이 없다

**변경:**
- 백엔드: `GET /synthesis/jobs/{job_id}/skeleton3d/all` 엔드포인트 추가
- 프론트엔드: 단일 `getSynthesisSkeleton3D()` 호출로 교체, 페이지네이션 인프라 제거

---

## Work Log

## refactor: load skeleton3d in single request, remove pagination infrastructure (#45)

**변경 파일:**
- `backend/service/skeleton_artifact_repository.py`: `get_skeleton3d_all()` 메서드 추가
- `backend/service/synthesis_job_manager.py`: `get_skeleton3d_all()` 위임 메서드 추가
- `backend/controller/synthesis.py`: `GET /synthesis/jobs/{job_id}/skeleton3d/all` 엔드포인트 추가
- `frontend/src/api/analysisClient.js`: `getSynthesisSkeleton3D()` 함수 추가
- `frontend/src/features/synthesis-session/useSynthesisSession.js`: `getSynthesisSkeleton3DPage` → `getSynthesisSkeleton3D` 교체
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`: 페이지네이션 인프라(`mergeSkeleton3DPage`, `pageRequestsRef`, prefetch 루프, on-demand fetch useEffect) 제거, 단일 요청으로 교체

**버그 수정 포함:**
`useSynthesisSession.js`가 첫 300프레임만 로드해 `getFrame`이 항상 프레임 299를 반환하던 문제 수정.

## feat: add playback controls to rack motion viewer (#45)

**변경 파일:**
- `frontend/src/components/sections/RackMotionStage1Section/RackMotionStage1Section.jsx`: `isPlaying` state, RAF 기반 재생 루프, stopPlayback, play/pause 버튼 추가
- `frontend/src/components/sections/RackMotionStage1Section/RackMotionStage1Section.module.css`: `.frameHeader`, `.playBtn`, `.playBtnActive` 스타일 추가
