# [feat] preset 추정 JSON 입력으로 포즈 추론 단계 건너뛰기
Parent: #25

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under `docs/mvp-v2/issues/sub-issues/`.
- Update this document before each related commit.

## Summary
2D 분석 파이프라인에서 PoseLandmarker Heavy 재추론 비용을 절감하기 위해,
미리 추출해 둔 포즈 추정 JSON(hd_00_21_2min, hd_00_11_2min)을 파이프라인 입력으로
직접 주입하는 어댑터 경로를 추가한다.

기존 파이프라인 흐름은 변경하지 않고, "입력 소스" 분기점만 추가한다:
```
[기존] 영상 업로드 → 포즈 추론 → chunk 입력 → (이후 동일)
[추가] preset JSON 선택 → JSON 로드 → chunk 입력 → (이후 동일)
```

## Goal
- 백엔드에 `preset_estimation.v1` 스키마의 JSON을 저장 및 로드하는 경로 추가
- `sourceType=preset_estimation` 분기: 포즈 추론 단계 건너뜀
- 프론트엔드 Analysis Settings에 preset 선택 UI 추가
- 기존 progress/streaming/skeleton 처리는 변경 없음

## Scope
- `backend/config/config.py`: `PRESET_ESTIMATION_DIR` 추가
- `backend/controller/jobs.py`: `presetEstimationId` Form 파라미터 추가
- `backend/service/job_manager.py`: `_run_preset_pipeline()` 추가, `_execute_pipeline()` 분기
- `frontend/src/api/analysisClient.js`: `presetEstimationId` 전송
- `frontend/src/features/analysis-session/useAnalysisSession.js`: 폼 + 검증 업데이트
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx`: preset 선택 UI

## Out Of Scope
- 새 파이프라인 경로 추가 없음 (chunk 이후 downstream 변경 없음)
- progress UI 변경 없음
- preset JSON 자동 생성 도구

## Preset JSON Format (`preset_estimation.v1`)
```json
{
  "schemaVersion": "preset_estimation.v1",
  "presetId": "hd_00_21_2min",
  "videoInfo": { "fps": 29.97, "width": 1920, "height": 1080, "frameCount": 3596 },
  "frames": [
    {
      "frameIndex": 0,
      "timestampMs": 0.0,
      "poseDetected": true,
      "landmarks": [
        {"name": "nose", "x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.99, "presence": 0.99}
      ]
    }
  ]
}
```

파일 저장 위치: `backend/src/preset_estimations/{preset_id}.json`

## Done Criteria
- preset JSON이 없을 경우 명확한 에러 메시지 반환
- preset 모드에서 `initializing_landmarker` → `analyzing` → `computing` → `completed` 흐름 정상 동작
- 기존 영상 업로드 경로 변경 없음
- 프론트엔드에서 preset 선택 시 영상 업로드 없이 분석 시작 가능

---

## Work Log

### feat: add preset estimation JSON input to skip pose inference (#42)

> 영상 업로드 없이 미리 추출한 포즈 JSON을 파이프라인에 직접 주입하는 어댑터 추가.
> 백엔드 preset 파이프라인 + 프론트엔드 선택 UI 포함.

#### Scope
- `backend/config/config.py`
- `backend/config/__init__.py`
- `backend/controller/jobs.py`
- `backend/service/job_manager.py`
- `backend/src/preset_estimations/README.md`
- `frontend/src/api/analysisClient.js`
- `frontend/src/features/analysis-session/useAnalysisSession.js`
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx`
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css`

#### Changes
**Backend:**
- `PRESET_ESTIMATION_DIR = BASE_DIR / "src" / "preset_estimations"` 추가 (config + __init__)
- `create_job` 엔드포인트에 `presetEstimationId` Form 파라미터 추가
  - 존재하지 않는 preset_id → 400 에러 즉시 반환
- `job_manager.create_job`에 `preset_estimation_id` 파라미터 추가 → metadata에 `sourceType`, `presetEstimationId` 저장
- `_execute_pipeline`에 `source_type` 분기 추가: preset → `_run_preset_pipeline()`, video → 기존 `_run_streaming_pipeline()`
- `_run_preset_pipeline()` 신규 메서드:
  - preset JSON 로드 → `PoseFrameResult` 파싱 → `PoseChunk` 그룹화
  - 기존 `SkeletonAssembler` + `PoseChunkBenchmarkCollector` 그대로 사용
  - `StreamingPipelineArtifacts` 반환 (기존 `_execute_pipeline` 후속 처리와 완전 호환)
- `backend/src/preset_estimations/README.md`: `preset_estimation.v1` 스키마 문서

**Frontend:**
- `useAnalysisSession.js`: `DEFAULT_FORM`에 `presetEstimationId: null` 추가, 검증 로직 업데이트
- `analysisClient.js`: `presetEstimationId` 전송, preset 모드에서 modelVariant/delegate 생략
- `CoreDemoSection.jsx`:
  - `PRESET_PAIRS` 상수 추가 (`hd_00_21_2min + hd_00_11_2min`)
  - 비디오 선택 시 preset 초기화, preset 선택 시 비디오 초기화
  - idle 상태 하단에 "또는 미리 추출된 JSON 사용" 섹션
  - preset 선택 후 활성화 상태 UI + 시작 버튼
  - `ProgressColumn`의 idle 조건을 preset 모드까지 포함
- `CoreDemoSection.module.css`: preset 섹션 스타일 추가

#### Verification
- `uv run python -m pytest tests/ -q` → 29/33 통과 (4개 pre-existing 실패 무관)
- `uv run python -c "from service.job_manager import job_manager"` → import OK

#### Notes
- preset JSON 파일이 없으면 controller에서 400을 즉시 반환 (job 생성 전 검증)
- `FrameExtractionOptions(video_path=preset_path)`를 benchmark 빌더용으로 합성 (실제 읽기 없음)
- `inference_seed` PoseInferenceResult를 직접 생성 (PoseInferenceService 세션 없이)
- chunk 이후 처리 (analysis, LLM feedback, benchmark, SSE streaming) 변경 없음


