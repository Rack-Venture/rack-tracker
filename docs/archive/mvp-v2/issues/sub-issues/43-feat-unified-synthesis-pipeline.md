# [feat] 단일 Synthesis 파이프라인으로 통합 — 중복 추론 제거
Parent: #43

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under `docs/mvp-v2/issues/sub-issues/`.
- Update this document before each related commit.

---

## Summary

현재 아키텍처는 동일한 비디오에 대해 MediaPipe 포즈 추론을 **두 번** 실행한다.

```
[현재]
createJob(A) → OpenCV 읽기 → MediaPipe 추론 → 2D 스켈레톤A   ← job_manager
createJob(B) → OpenCV 읽기 → MediaPipe 추론 → 2D 스켈레톤B   ← job_manager
createStreamingSynthesisJob(videoA, videoB)
  → OpenCV 읽기A → MediaPipe 추론A ─┬─► 삼각측량 → 3D 스켈레톤  ← synthesis_job_manager
  → OpenCV 읽기B → MediaPipe 추론B ─┘

[목표]
createSynthesisJob(videoA, videoB)
  → OpenCV 읽기A → MediaPipe 추론A ─┬─► 2D 스켈레톤A (부산물 저장)
                                      ├─► 삼각측량 → 3D 스켈레톤
  → OpenCV 읽기B → MediaPipe 추론B ─┴─► 2D 스켈레톤B (부산물 저장)
```

Streaming synthesis 파이프라인 하나가 추론 결과를 **2D 저장 + 3D 삼각측량 동시 처리**하며,
프론트엔드는 synthesis 잡 하나만 추적한다.

---

## Goal

- 비디오당 포즈 추론을 한 번만 실행한다
- 2D 스켈레톤(카메라별)을 synthesis 파이프라인의 부산물로 저장한다
- Preset 모드를 synthesis 파이프라인 내부에서 처리한다 (JSON 로드 → 삼각측량만 실행)
- 2D 생체역학 분석(AnalysisPipelineService)을 synthesis 파이프라인 내부로 이전하여 **3D 생체역학으로의 발전 경로를 보존**한다
- 프론트엔드를 단일 synthesis 잡 추적 구조로 단순화한다

---

## 아키텍처 설계

### 파이프라인 스레드 토폴로지

```
produce_frames(A) → frame_queue_a → infer_poses(A) → pose_queue_a ─┐
produce_frames(B) → frame_queue_b → infer_poses(B) → pose_queue_b ─┤
                                                                     └→ coordinate()
                                                                            │
                                                            ┌───────────────┤
                                                            │               ▼
                                                     assembler_a    aligned_pair_queue
                                                     assembler_b           │
                                                            │        triangulate()
                                                            │               │
                                                            └──── result_queue ──► [main collector]
```

`coordinate()` 함수는 `pose_queue_a`와 `pose_queue_b`를 모두 읽는 자연스러운 fan-out 지점이다.
여기서 각 pose chunk를 `SkeletonAssembler`에도 전달하면 추가 스레드 없이 2D 스켈레톤을 수집할 수 있다.

### Preset 모드 통합

```
[preset 소스]
load_preset_poses(jsonPath_A) → pose_queue_a ─┐
load_preset_poses(jsonPath_B) → pose_queue_b ─┤
                                               └→ coordinate() → triangulate() → [기존과 동일]
```

`StreamingPairManifest` 소스에 `presetJsonPath` 필드를 추가한다.
소스마다 독립적으로 video/preset을 선택할 수 있다.

```python
class StreamingSource(BaseModel):
    videoPath: str | None = None
    presetJsonPath: str | None = None  # 추가
    cameraId: str
```

### 2D 생체역학 분석 보존 방식

현재 `AnalysisPipelineService`는 2D 스켈레톤 기반으로 동작한다.
이 호출을 synthesis 잡 내부에서 카메라별로 유지한다.

```
synthesis 완료 후:
  skeleton_a → AnalysisPipelineService.analyze() → analysis_a (저장)
  skeleton_b → AnalysisPipelineService.analyze() → analysis_b (저장)
```

향후 3D 생체역학으로 발전 시:
- skeleton3d → `AnalysisPipeline3DService.analyze()` 호출로 교체 또는 병행
- 2D 분석은 비교 기준 또는 fallback으로 유지 가능

---

## Scope

### Backend

| 항목 | 파일 | 내용 |
|------|------|------|
| `coordinate()` fan-out | `service/synthesis_job_manager.py` | pose chunk → assembler_a/b 추가 전달 |
| 2D artifact 저장 | `service/synthesis_job_manager.py` | `_write_artifacts_and_complete()` 확장 |
| Preset 소스 지원 | `service/synthesis_job_manager.py` | `load_preset_poses()` 함수, video/preset 분기 |
| `StreamingSource` 스키마 | `schema/synthesis.py` | `presetJsonPath: str | None = None` 추가 |
| Artifact Repository 확장 | `service/skeleton_artifact_repository.py` | `write_skeleton_a/b()`, `get_skeleton_a/b_page()` 추가 |
| 새 엔드포인트 | `controller/synthesis.py` | `GET /synthesis/jobs/{id}/skeleton_a`, `/skeleton_b` |
| 2D 생체역학 분석 이전 | `service/synthesis_job_manager.py` | synthesis 완료 후 camera별 `AnalysisPipelineService.analyze()` 호출 |
| `/jobs` 엔드포인트 | `controller/jobs.py` | 하위호환 유지, 신규 프론트엔드에서는 사용 안 함 |

### Frontend

| 항목 | 파일 | 내용 |
|------|------|------|
| `useSynthesisSession` 신규 훅 | `features/synthesis-session/useSynthesisSession.js` | synthesis 잡 단일 추적, skeletonA/B/3D 접근 |
| `CoreDemoSection` 단순화 | `components/sections/CoreDemoSection/CoreDemoSection.jsx` | sessionA+sessionB 제거, synthesis 단일 세션 사용 |
| API 클라이언트 확장 | `api/analysisClient.js` | `getSkeletonAPage()`, `getSkeletonBPage()` 추가 |
| Progress UI 재구성 | `CoreDemoSection.jsx` | A/B inference 진행은 synthesis stage_details에서 파생 |
| Preset 입력 연결 | `CoreDemoSection.jsx` | `presetJsonPath` 기반 synthesis 요청으로 전환 |

### 보존 / 폐기

| 항목 | 처분 | 이유 |
|------|------|------|
| `job_manager.py` | 하위호환 유지 (폐기 선언) | 직접 호출하는 외부 클라이언트 대비 |
| `useAnalysisSession.js` | 내부적으로 폐기 | `useSynthesisSession`으로 대체 |
| `createJob()` API 호출 | 프론트엔드에서 제거 | `createStreamingSynthesisJob`이 단일 진입점 |
| `AnalysisPipelineService` | synthesis 파이프라인 내부로 이전 | 3D 생체역학 발전 경로 보존 |

---

## Out Of Scope

- 3D 생체역학 분석 구현 (별도 이슈)
- LLM 피드백 3D 확장 (별도 이슈)
- `/jobs` 엔드포인트 완전 제거 (충분한 안정화 후 별도 chore)
- 단일 카메라 분석 전용 워크플로우 지원

---

## Done Criteria

- [x] 비디오 업로드 시 MediaPipe 추론이 각 카메라당 한 번만 실행된다
- [x] Preset 모드 시 추론 없이 삼각측량만 실행된다
- [x] `/synthesis/jobs/{id}/skeleton_a`, `/skeleton_b`로 카메라별 2D 스켈레톤 접근 가능
- [x] 프론트엔드가 synthesis 잡 하나로 전체 진행 상태를 추적한다
- [x] A/B 카메라별 2D 생체역학 분석 결과가 synthesis 잡 결과에 포함된다
- [x] 기존 3D 스켈레톤 결과(`/synthesis/jobs/{id}/skeleton3d`)는 동일하게 동작한다

---

## Implementation Status & Decision Matrix

| ID | 구분 | 레이어/단계 | 상태 | 결정된 방향 | 결정 필요 사항 | 다음 액션 | 참조 |
|----|------|------------|------|------------|--------------|---------|------|
| ITEM-01 | coordinate() fan-out | Service | **완료** | coordinate()에서 pose chunk → assembler_a/b 추가 전달 | 없음 | — | `service/synthesis_job_manager.py` |
| ITEM-02 | Preset 소스 지원 | Contract / Service | **완료** | `StreamingSource.presetEstimationId` 추가, `load_preset_poses()` 함수로 video 분기 대체 | 없음 | — | `schema/synthesis.py` |
| ITEM-03 | Artifact Repository 확장 | Service | **완료** | `write_skeleton_a/b()`, `get_skeleton_a/b_page()` 신규 메서드 추가 | 없음 | — | `service/skeleton_artifact_repository.py` |
| ITEM-04 | 새 엔드포인트 | Contract | **완료** | `GET /synthesis/jobs/{id}/skeleton_a`, `/skeleton_b`, `POST /synthesis/upload` | 없음 | — | `controller/synthesis.py` |
| ITEM-05 | 2D 생체역학 이전 | Service | **완료** | synthesis 완료 후 카메라별 `AnalysisPipelineService.analyze()` 호출, 결과를 synthesis artifact에 포함 | 없음 | — | `service/synthesis_job_manager.py` |
| ITEM-06 | `useSynthesisSession` 훅 | UI | **완료** | synthesis 잡 단일 추적, skeletonA/B/3D 접근 제공 | 없음 | — | `features/synthesis-session/useSynthesisSession.js` |
| ITEM-07 | `CoreDemoSection` 재구성 | UI | **완료** | sessionA+sessionB 제거, 단일 synthesis 세션 사용, preset 입력 → presetEstimationId 전달 | 없음 | — | `components/sections/CoreDemoSection/CoreDemoSection.jsx` |
| ITEM-08 | Progress UI A/B 메트릭 | UI | **완료** | synthesis stage_details에 `inferredChunksA/B` 추가, SynthSharedColumn이 InfA/InfB 행 렌더링 | 없음 | — | `CoreDemoSection.jsx:buildSynthSharedRows` |
| ITEM-09 | `/jobs` 엔드포인트 폐기 선언 | Contract | **완료** | `Deprecation: true`, `X-Deprecated-By: /synthesis/jobs` 응답 헤더 추가 | 없음 | — | `controller/jobs.py` |

---

## Work Log

### 2026-05-13 — SynthSharedColumn 파이프라인 토폴로지 UI + 상세 벤치마크 재구성 (feat)

**변경 파일 (2개 수정):**
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx` — `buildSynthSharedRows` 제거, `TopoNode` 컴포넌트 신규, `SynthSharedColumn` 전면 재작성
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css` — 토폴로지 전용 CSS 클래스 추가, `dualProgressContent` 그리드 → flex 단순화

**결정 사항:**
- 파이프라인 스레드 토폴로지 그대로 시각화: 병렬 A/B 트랙 → `coordinate()` 수렴 → `triangulate()` → `[main collector]`
- Preset 모드: A/B 노드에 `isSkipped` 적용 (점선 + dim), "preset load" 라벨
- 완료 시 벤치마크 3개 서브섹션: 3D Quality (`qualitySummary`), Camera A/B Analysis (`analysisA/B.summary`), Pipeline 처리량
- 3D Quality: pairedFrameCount, validFrameRatio, usableJointRatio, meanReprojectionErrorPx, timestamp delta, failureReasonCounts
- 전체 진행률 바 (`progressRatio`) 추가

---

### 2026-05-13 — 3D 로딩 전 A+B fallback 제거 (cleanup)

**변경 파일 (1개 수정):**
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx` — `synthesizeFrames`에서 A+B 평균 fallback 제거, 모드 라벨·HUD 텍스트 정리

**결정 사항:**
- `synthesized` 모드에서 3D 프레임 미로드 구간은 빈 캔버스로 표시 (기존 A+B 평균 표시 제거)
- 모드 버튼 라벨 `'A+B Preview'` 제거 → `'3D Synthesis'` 고정
- HUD source 칩 `'fallback'` / `'A+B'` 케이스 제거

---

### 2026-05-13 — 섹션 간 데이터 전달 연결 수정 (bugfix)

**변경 파일 (2개 수정):**
- `frontend/src/App.jsx` — `Skeleton3DSynthesisSection`에 `synthesisSession` 전달, `RackMotionStage1Section`에 `synthesisSession.jobId` 우선 전달
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx` — `synthesisSession` prop 수락, external skeleton3d 시딩, 내부 synthesis 억제 가드, `activeJobId` 통합

**원인:** `CoreDemoSection`(preset/video synthesis)의 결과가 `Skeleton3DSynthesisSection`과 `RackMotionStage1Section`으로 전달되지 않음. `Skeleton3DSynthesisSection`은 `sessionA/B.videoPath`로만 synthesis를 트리거해 preset 모드에선 실행 안 됨. `RackMotionStage1Section`도 `onSynthesisJobIdChange` 콜백으로만 jobId를 받아 끊김.

**수정 결정 사항:**
- `externalSkeleton3D` useMemo → useEffect 시딩 패턴: 외부 세션의 skeleton3d를 `synthesisState.skeleton3D`에 초기화, 이후 추가 페이지 prefetch도 동일 state에 누적
- 내부 synthesis useEffect에 `synthesisSession?.jobId` 가드 추가 — 외부 세션이 있으면 중복 synthesis 방지

---

### 2026-05-13 — 전체 구현 완료 (commit `13b9822`)

**변경 파일 (8개 수정, 1개 신규):**
- `backend/schema/synthesis.py` — `StreamingSource` 클래스 추가 (`presetEstimationId` 필드)
- `backend/service/skeleton_artifact_repository.py` — `skeleton2d` 디렉터리, `write_skeleton_a/b()`, `get_skeleton_a/b_page()` 추가
- `backend/service/synthesis_job_manager.py` — `coordinate()` fan-out, `load_preset_poses()`, `AnalysisPipelineService` 통합, `inferredChunksA/B` 메트릭, `_source_display_path()` 헬퍼
- `backend/controller/synthesis.py` — `POST /synthesis/upload`, `GET /synthesis/jobs/{id}/skeleton_a/b` 엔드포인트 추가
- `backend/controller/jobs.py` — `Deprecation: true` 응답 헤더 추가
- `frontend/src/api/analysisClient.js` — `uploadSynthesisVideo()`, `getSkeletonAPage/B()`, `createStreamingSynthesisJob` 확장
- `frontend/src/features/synthesis-session/useSynthesisSession.js` — **신규** 훅
- `frontend/src/App.jsx` — `useSynthesisSession` 사용, `CoreDemoSection` prop 변경
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx` — synthesis 단일 세션으로 재구성, InfA/InfB 행 추가

**구현 결정 사항:**
- `presetJsonPath` 대신 `presetEstimationId`를 스키마에 사용 — 서버 파일 경로를 클라이언트가 알 필요 없도록
- `POST /synthesis/upload` 엔드포인트 신설 — 분석 잡 생성 없이 비디오 업로드만 처리
- `AnalysisPipelineService.analyze()` 실패 시 경고 로그만 기록, 전체 합성은 계속 진행

---

## Management Notes

### Follow-up Candidates
- 3D 생체역학 분석 구현 (skeleton3d 기반 `AnalysisPipeline3DService`)
- LLM 피드백 3D 기반 확장
- `/jobs` 엔드포인트 완전 제거 (안정화 후 chore)
- 단일 카메라 전용 분석 워크플로우 (synthesis 없이 2D만 필요한 케이스)

### Notes
- `coordinate()` fan-out 방식: 추가 스레드 불필요, 기존 queue 구조 유지
- Preset 소스와 video 소스는 같은 파이프라인을 공유 — `pose_queue`에 청크를 주입하는 방식만 다름
- `AnalysisPipelineService`는 2D 스켈레톤 dict를 입력받으므로 synthesis 완료 후 그대로 호출 가능
- 2D 생체역학 결과는 synthesis result_summary에 `analysisA`, `analysisB` 키로 포함

### References
- GitHub Issue: https://github.com/rack-labs/rack-tracker/issues/43
- 선행 작업: `docs/mvp-v2/issues/sub-issues/41-feat-3d-synthesis-streaming-pipeline.md`
- 선행 작업: `docs/mvp-v2/issues/sub-issues/42-feat-preset-estimation-json-input.md`
- 현재 synthesis 파이프라인: `backend/service/synthesis_job_manager.py:212`
