# [feat] 3D 합성을 청크 기반 스트리밍 파이프라인으로 통합
Parent: #25

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under `docs/mvp-v2/issues/sub-issues/`.
- Update this document before each related commit.

## Summary
현재 3D skeleton 합성은 두 2D job이 완료된 뒤 artifact 전체를 로드하여 일괄 삼각측량하는 분리된 순차 처리 경로다.
이 작업은 3D 합성을 기존 청크 기반 컨베이어 파이프라인 안으로 통합하여,
각 포즈 청크가 생성되는 즉시 삼각측량이 실행되는 실시간 스트리밍 경로를 구현한다.

이 작업은 `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/streaming-pipeline-plan.md`의
STR-04/STR-06 항목에서 "별도 이슈로 분리"하기로 결정된 후속 구현이다.

## Goal
- `Skeleton3DSynthesizer`에 청크 단위 삼각측량 메서드 추가 (Phase 1)
- `SynthesisJobManager`를 스트리밍 파이프라인으로 재구성 (Phase 2)
- 입력 스키마에 `streaming_mode` (비디오 파일 직접 전달) 추가 (Phase 3)
- 실시간 `processedFrames` / 청크 단위 `stageDetails` 진행 추적 구현 (Phase 4)

## Scope
- `backend/service/skeleton_3d_synthesizer.py`: `synthesize_chunk()` 추가
- `backend/service/synthesis_job_manager.py`: `_run_streaming_pipeline()` 재구성
- `backend/schema/synthesis.py`: streaming_mode 입력 필드 추가
- 진행 상황 추적 업데이트 (processedFrames, stageDetails)

## Out Of Scope
- 기존 artifact_mode (완료된 job ID 기반) 합성 경로 변경
- 카메라 캘리브레이션 자동화
- 3개 이상 카메라 지원
- temporal smoothing / visual regression 검증

## Done Criteria
- synthesis job이 두 비디오 파일 경로를 받아 두 추론 파이프라인을 병렬 실행한다
- `DualVideoSynthesisCoordinator`가 청크를 매칭하고 즉시 삼각측량에 넘긴다
- 진행 상황이 실제 프레임/청크 처리량을 실시간으로 반영한다
- 기존 artifact 기반 합성 경로가 그대로 동작한다
- 두 비디오 파일 입력에서 유효한 `skeleton3d.v1` artifact가 생성된다

---

## Work Log

### feat: add SynthesisChunkResult and synthesize_chunk() to Skeleton3DSynthesizer (#41)

> `_synthesize_frame`에서 `SynthesisInput` 의존성을 제거하고, 청크 단위 삼각측량 진입점인 `synthesize_chunk()`를 추가한다.

#### Scope
- `backend/service/skeleton_3d_synthesizer.py`
- `backend/tests/test_skeleton_3d_synthesizer.py`

#### Changes
- `SynthesisChunkResult` 데이터클래스 추가 (`chunk_index`, `frames`, `success_joint_count`, `total_joint_count`, `reprojection_errors`, `failure_counts`, `alignment_summary`)
- `_synthesize_frame` 시그니처에서 `synthesis_input: SynthesisInput` 제거 → `camera_id_a`, `camera_id_b`, `thresholds` 명시 파라미터로 분리
- `_failed_joint_payload` 동일 방식으로 리팩터링
- `debug_report` 파라미터 타입을 `dict | None`으로 변경, `None`일 때 debug sample 축적 스킵
- `synthesize_chunk(aligned_pair, *, camera_a, camera_b, camera_id_a, camera_id_b, max_delta_ms, thresholds, pair_index_offset, video_info_a, video_info_b, debug_report)` 메서드 추가
- `synthesize()` 공개 API 변경 없음 (하위 호환 유지)
- 신규 테스트 4개 추가: `test_synthesize_chunk_returns_synthesis_chunk_result`, `test_synthesize_chunk_produces_correct_3d_output`, `test_synthesize_chunk_preserves_chunk_index`, `test_synthesize_chunk_handles_multiple_frames`

#### Verification
- `uv run python -m pytest tests/test_skeleton_3d_synthesizer.py -v` → 6/6 통과
- 전체 suite: 19/23 통과 (4개 pre-existing 실패는 GroundRef/LlmFeedbackService 무관 이슈)

#### Notes
- `video_info_a/b` 기본값 `{}` 허용: `LandmarkObservationBuilder`가 `camera_model.image_width/height`로 fallback
- `pair_index_offset` 파라미터: 청크 간 debug sample 전역 순서 유지용 (Phase 2에서 스트리밍 collector가 사용)

---

### feat: add streaming synthesis pipeline and StreamingPairManifest schema (#41)

> 3D 합성을 청크 기반 컨베이어 파이프라인으로 통합한다. Phase 3 (스키마) → Phase 2 (파이프라인) → Phase 4 (진행 추적) 을 하나의 커밋으로 완성한다.

#### Scope
- `backend/schema/synthesis.py`
- `backend/service/synthesis_job_manager.py`
- `backend/tests/test_synthesis_schema.py`

#### Changes
**Phase 3 — Schema:**
- `SynthesisThresholds`를 `SynthesisPairManifest` 앞으로 이동 (forward reference 방지)
- `StreamingVideoSource`, `StreamingPairSources`, `StreamingPairManifest` 추가
- `SynthesisJobCreateRequest.pairManifest`를 optional로 변경, `streamingManifest` 필드 추가
- model_validator로 양쪽 중 정확히 하나만 허용 (mutual exclusion)
- 기존 artifact_mode API 하위 호환 유지

**Phase 2 — Streaming Pipeline:**
- `SynthesisJobManager.__init__`에 `VideoReaderService` 주입
- `_execute_job()` → mode 분기: `_run_artifact_synthesis()` vs `_run_streaming_synthesis()`
- `_run_artifact_synthesis()`: 기존 배치 흐름 추출 (기능 변경 없음)
- `_run_streaming_synthesis()`: 6-워커 컨베이어 구현
  - `produce_frames` ×2 (A/B): `VideoReaderService.iter_frame_chunks()` → `frame_queue_a/b`
  - `infer_poses` ×2 (A/B): `PoseInferenceService.infer_chunk()` → `pose_queue_a/b`
  - `coordinate`: 두 pose_queue를 polling → `DualVideoSynthesisCoordinator.ingest()` → `aligned_pair_queue`
  - `triangulate`: `synthesizer.synthesize_chunk()` → `result_queue`
  - 메인 collector: `SynthesisChunkResult` 누적 → artifact 조립 → 저장
- `_set_progress()` 리팩터링: `synthesis_input` 의존성 제거, `stage_details` dict 직접 전달

**Phase 4 — Progress Tracking (Phase 2에 통합):**
- 스트리밍 중 `processedFrames` / `totalFrames` 실시간 업데이트
- `pairedChunks`, `triangulatedChunks`, `triangulatedFrames`, `avgTriangulateMs`, `p95TriangulateMs` stageDetails 노출
- ratio를 `processedFrames / estimatedTotalFrames` 기반으로 동적 계산

#### Verification
- `uv run python -m pytest tests/test_synthesis_schema.py tests/test_skeleton_3d_synthesizer.py -v` → 12/12 통과
- 전체 suite: 37/41 통과 (4개 pre-existing 실패 무관)

#### Notes
- streaming mode의 `debugReport`는 현재 미포함 (artifact mode와 동일하게 향후 추가 가능)
- `_front_view_hint`, `_calibration_service`, `_alignment_service`, `_fps_from_video_info`는 synthesizer 내부 메서드 직접 호출 (단일 모듈 경계 내)
- `coordinate` 워커는 두 pose_queue를 0.05s timeout으로 번갈아 polling (단순하고 실용적)

---

### feat: connect frontend to streaming synthesis pipeline (#41)

> 프론트엔드가 완료된 job ID 대신 비디오 경로를 사용하는 streamingManifest로 합성 job을 생성하도록 전환한다.

#### Scope
- `frontend/src/api/analysisClient.js`
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`
- `backend/service/synthesis_job_manager.py`

#### Changes
- `analysisClient.js`: `createStreamingSynthesisJob({ videoPathA, videoPathB, cameraIdA, cameraIdB })` 추가
- `Skeleton3DSynthesisSection.jsx`:
  - import `createStreamingSynthesisJob` 으로 교체
  - 트리거 조건: `sessionA/B.status === 'completed'` → `skeletonA/B.videoInfo.videoSrc` 존재 여부
  - manifest: `pairManifest(sourceJobId)` → `streamingManifest(videoPath)`
  - key: `streaming:{videoPathA}:{videoPathB}:{cameraIdA}:{cameraIdB}`
  - statusLabel: `initializing`, `streaming` 스테이지 추가
  - description 텍스트 업데이트
  - deps 배열: `jobId` 제거, `videoSrc` 추가
- `synthesis_job_manager.py`:
  - `_write_artifacts_and_complete`에 `total_steps` 파라미터 추가
  - streaming mode는 5 steps, artifact mode는 6 steps로 분리

#### Verification
- `uv run python -m pytest tests/ -q` → 37/37 통과

#### Notes
- 현재 트리거는 여전히 2D skeleton 완료 후 (videoSrc 획득 시점)
  - 이는 실제 병렬 실행이 아니라 순차 실행과 같음
  - 완전한 병렬화(2D 완료 전 synthesis 시작)는 별도 follow-up으로 분리
  - 현재 구현으로도 streaming pipeline의 e2e 동작 검증 가능

---

### fix: expose videoPath at job creation and trigger synthesis in parallel with 2D inference (#41)

> `JobCreateResponse`에 `videoPath`를 추가하여 synthesis 트리거를 2D 완료 전으로 앞당긴다.
> `PendingChunkOverflowError` 원인 분석 및 `max_pending_chunks` 확대, `_fail_job` 로깅도 함께 포함.

#### Scope
- `backend/schema/job.py`
- `backend/service/job_manager.py`
- `backend/service/synthesis_job_manager.py`
- `frontend/src/features/analysis-session/useAnalysisSession.js`
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`

#### Changes
- `JobCreateResponse`에 `videoPath: str | None` 필드 추가
- `job_manager.create_job`에서 `videoPath=source_path` 반환
- `useAnalysisSession`: state에 `videoPath` 추가, job 생성 응답에서 즉시 저장
- `Skeleton3DSynthesisSection`: 트리거를 `skeletonPage.videoInfo.videoSrc` (2D 완료 후) → `sessionA/B.videoPath` (job 생성 직후)로 변경
- `SYNTH_COORDINATOR_MAX_PENDING = 16` 추가, coordinator 생성 시 적용 (`PendingChunkOverflowError` 대비)
- `_fail_job`에 `logger.error(..., exc_info=True)` 추가

#### Verification
- `uv run python -m pytest tests/test_synthesis_schema.py tests/test_skeleton_3d_synthesizer.py -q` → 12/12 통과

#### Notes
- 2D job과 synthesis job이 동일 비디오 파일을 동시에 읽음. 2D 완료 후 `_cleanup_transient_upload`가 `unlink()` 시도:
  - Windows: 파일 락으로 삭제 실패 → `except OSError: pass` 처리됨 (synthesis 종료 후 파일 잔존)
  - Linux: unlink 성공, fd 유지로 synthesis는 계속 읽을 수 있음
- 잔존 파일 정리는 별도 cleanup 메커니즘으로 추후 처리 예정

---

### feat: restructure dualProgressContent to match synthesis conveyor topology (#41)

> Pipeline Progress 패널의 컨베이어 UI를 6-worker + collector 구조에 맞게 재구성한다.

#### Scope
- `frontend/src/App.jsx`
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx`
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css`
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`

#### Changes
- `App.jsx`: `synthesisProgress` state 추가, `Skeleton3DSynthesisSection`에 `onSynthesisProgressChange` 전달, `CoreDemoSection`에 `synthesisProgress` prop 전달
- `Skeleton3DSynthesisSection`: `onSynthesisProgressChange` prop 추가, synthesisState 변경 시마다 `{ status, progress }` 업콜
- `buildPipelineRows`: skeleton/benchmark 행 제거 → A/B branch용 `Prod`(producer) + `Infer`(inference) 2행으로 축소
- `buildSynthSharedRows` 추가: coordinator(`pairedChunks`), triangulator(`triangulatedChunks`, `avgTriangulateMs`, `p95TriangulateMs`), collector(`triangulatedFrames`) 3행
- `SynthSharedColumn` 컴포넌트 추가: synthesis stageDetails 기반 컨베이어 렌더링
- `dualProgressContent` JSX: `A | divider | B` → `A | divider | SynthSharedColumn | divider | B` 5열 레이아웃
- CSS: `dualProgressContent` grid `1fr auto 1fr` → `1fr auto 1fr auto 1fr`, coordinator(violet)/triangulator(cyan)/collector(slate) 트랙 색상 추가

#### Notes
- A/B branch 열: 2D inference stageDetails 기반 (Prod + Infer), synthesis pipeline의 per-branch 역할과 1:1 대응
- Synthesis 열: `progress.stageDetails.synthesis`의 집계 메트릭만 노출 (queue depth는 백엔드 미노출)
- `ppConveyorRow` 레이블 칼럼 4rem 제약 → 짧은 약어(Coord/Tri/Coll) 사용

---

## Management Notes

### Implementation Matrix

| Phase | 내용 | 상태 | 핵심 파일 |
|-------|------|------|----------|
| Phase 1 | `Skeleton3DSynthesizer.synthesize_chunk()` 추가 | 구현 완료 | `backend/service/skeleton_3d_synthesizer.py` |
| Phase 2 | `SynthesisJobManager` 스트리밍 파이프라인 재구성 | 구현 완료 | `backend/service/synthesis_job_manager.py` |
| Phase 3 | 입력 스키마 streaming_mode 추가 | 구현 완료 | `backend/schema/synthesis.py` |
| Phase 4 | 실시간 진행 추적 | 구현 완료 (Phase 2에 통합) | `backend/service/synthesis_job_manager.py` |
| 병렬화 | synthesis 트리거를 2D job 생성 직후로 앞당김 | 구현 완료 | `schema/job.py`, `useAnalysisSession.js`, `Skeleton3DSynthesisSection.jsx` |

### Notes
- #29 STR-04/STR-06의 "별도 이슈 분리" 결정을 따르는 후속 구현
- `DualVideoSynthesisCoordinator`는 이미 청크 페어링 로직이 구현되어 있음
- chunk_index 기준 매칭이므로 두 스트림의 청크 크기 일치가 전제 조건
- Phase 1이 완료되기 전까지 Phase 2 구현을 시작하지 않는다

### References
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/streaming-pipeline-plan.md` (STR-04, STR-06)
- `backend/service/dual_video_synthesis_coordinator.py`
- `backend/service/skeleton_3d_synthesizer.py`
- `backend/service/synthesis_job_manager.py`
- GitHub issue: #41
