# [feat] 두 동영상 스켈레톤 추출 및 3D 합성 기반 실험
Parent: #25

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place this file under `docs/mvp-v2/issues/sub-issues/`.
- Update this document before each related commit.

## Matrix Sync Rule
- 부모 문서의 matrix는 하위 plan 문서들의 상태, 결정, 연동 위험을 요약한다.
- 하위 plan 문서의 상세 구현 항목이 외부 계약을 바꾸면 부모 matrix의 해당 row를 갱신한다.
- 부모 matrix에서 scope, priority, dependency, 상태가 바뀌면 관련 하위 plan 문서의 matrix도 갱신한다.
- 하위 plan 문서의 상태가 `결정 필요`, `구현 완료`, `검증 완료`, `보류`, `차단됨`으로 바뀌면 부모 row 상태와 `갱신 필요 사항`도 함께 재검토한다.
- 부모 matrix는 세부 구현의 source of truth가 아니라 통합 tracking index다. 세부 구현 source of truth는 하위 plan 문서다.

## Plan Integration Matrix

| ID | 구분 | 하위 문서 | 상태 | 결정된 방향 | 연동 대상 | 갱신 필요 사항 | 다음 액션 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PLAN-01 | 스트리밍 파이프라인 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/streaming-pipeline-plan.md` | 검증 완료 | chunk streaming, stage split, spool collector, timing summary 기반 2D skeleton artifact 생성 경로가 #29 실험 입력으로 동작한다. | 3D 합성기, API, benchmark | 2D artifact 저장 경로나 stageDetails 필드가 바뀌면 합성기와 API plan 갱신 | #29에서는 종료. streaming synthesis는 후속 이슈에서 재정의 |
| PLAN-02 | 3D 합성기 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/3d-skeleton-synthesizer-plan.md` | 검증 완료 | job artifact 기반 batch synthesis, source binding, debug report, `synthesisInfo.viewHint`를 포함한 실험용 `skeleton3d.v1` 생성 경로를 구현했다. | triangulation, API, GT 평가, rendering | output schema나 quality/debug field가 바뀌면 렌더링/API/GT 문서 갱신 | #29에서는 종료. product/session world 합성은 후속 이슈로 분리 |
| PLAN-03 | triangulation | `29-feat-dual-video-skeleton-3d-synthesis-experiment/triangulation-implementation-plan.md` | 검증 완료 | DLT, cheirality, reprojection error, Sampson 진단, 실패 관절의 `diagnosticPosition`/non-renderable 분리를 구현했다. | 3D 합성기, GT 평가, rendering | CameraModel 계약 변경 시 합성기와 GT 문서 갱신 | #29에서는 종료. camera rig/session world 검증은 후속 이슈로 분리 |
| PLAN-04 | 3D 렌더링 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/3d-skeleton-rendering-plan.md` | 구현 완료 | Three.js viewer가 paged `skeleton3d.v1`를 로드하고 실패 관절을 제외하며 `viewHint` 기반 수직 축/지면 힌트를 사용한다. | API, output schema, PLAN-08 | viewer 품질 표현 규칙이나 page contract가 바뀌면 API/output schema 문서 갱신 | #29에서는 종료. 브라우저 시각 품질 검증과 UX polish는 후속 이슈로 분리 |
| PLAN-05 | API/분석 연결 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/3d-synthesis-api-analysis-pipeline-plan.md` | 구현 완료 | pair manifest 기반 synthesis job/status/result/skeleton3d/evaluation/debug 조회 경로를 구현했다. 3D 분석 adapter는 후속 범위로 남긴다. | 3D 합성기, 렌더링, GT 평가 | synthesis status/result/debug schema가 바뀌면 렌더링/GT 문서 갱신 | #29에서는 종료. 3D analysis adapter는 후속 이슈에서 정의 |
| PLAN-06 | GT 평가 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/gt-evaluation-plan.md` | 구현 완료 | MediaPipe33-COCO19 subset raw MPJPE와 reprojection summary를 분리 계산하는 evaluator를 구현했다. | triangulation, output schema | joint mapping이나 evaluation artifact schema가 바뀌면 synth/API 문서 갱신 | #29에서는 종료. 공식 품질 threshold와 product acceptance는 후속 이슈에서 정의 |
| PLAN-07 | 3D 합성 재설계 검토 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/3d-synthesis-redesign-review-plan.md` | 보류 | 2D 출력 계약, camera binding, session world, two-view diagnostics, viewer transform 분리 방향을 기록했다. #29에서는 구현 범위를 더 확장하지 않는다. | 3D 합성기, triangulation, 렌더링, GT 평가, future rack session world | 재검토 결과가 output schema, camera model, 실패 관절 계약, viewer transform을 바꾸면 PLAN-02/03/04/06 갱신 | 후속 rack/session-world pipeline 이슈에서 필요한 항목만 재개 |
| PLAN-08 | ThreeJS viewer 수직 축 구조 수정 | `29-feat-dual-video-skeleton-3d-synthesis-experiment/viewer-floor-fix-plan.md` | 구현 완료 | `synthesisInfo.viewHint`를 backend output에 추가하고 adapter/viewer에서 수직 축·지면 힌트와 관절 bounds 역할을 분리했다. | 3D 렌더링(PLAN-04), 재설계 검토(PLAN-07) | `viewHint` schema가 바뀌면 PLAN-02/PLAN-05 갱신 | #29에서는 종료. 실제 브라우저 visual regression은 후속 검증 이슈로 분리 |

## Final Conclusion
- #29의 원래 done criteria인 두 동영상 2D skeleton 추출, 두 시점 기반 3D 좌표 합성 실험, 합성 방식 및 초기 품질/진단 결과 문서화는 현재 범위에서 충족된 것으로 정리한다.
- 이번 실험의 산출물은 production-ready rack motion pipeline이 아니라, `skeleton3d.v1` artifact, batch synthesis API, triangulation/debug/evaluation contract, Three.js 검증 viewer까지 이어지는 MVP 실험 baseline이다.
- 사용자 관찰상 3D viewer의 시각 품질과 초반 관절 안정성은 제품 기준으로 충분하지 않다. #29에서는 이를 미해결 리스크로 남기고, camera rig/session world, fixture 재검증, temporal smoothing, visual regression은 후속 이슈에서 다룬다.
- MVP2-03/rack motion pipeline 요구사항 및 별도 issue branch 작업은 #29 종료 커밋 범위에 포함하지 않는다.

## Summary
두 카메라 각도의 동영상에서 각각 2D 스켈레톤(랜드마크)을 추출하고, 이를 합성하여 정밀도 높은 3D 스켈레톤을 생성하는 기반 작업과 실험을 진행한다.
단일 카메라 2D 랜드마크의 깊이 정보 부재 한계를 극복하고, 다시점 정보를 활용한 3D 재구성 파이프라인의 타당성을 검증한다.

## Goal
- 두 동영상 입력을 받아 각각 2D 랜드마크를 추출하는 파이프라인을 구성한다
- 두 시점의 2D 랜드마크로 3D 좌표를 합성하는 실험 파이프라인을 구현한다
- 초기 정밀도 평가 기준을 정의하고 결과를 문서화한다

## Scope
- 두 동영상 입력을 받아 각각 MediaPipe 2D 랜드마크 추출
- 두 카메라 시점 간 대응 관계 설계 (epipolar geometry, triangulation 등 후보 방식 검토)
- 3D 스켈레톤 합성 알고리즘 실험 및 구현
- 초기 정밀도 평가 기준 정의 및 결과 문서화

## Out Of Scope
- 실시간 스트리밍 입력 처리
- 카메라 캘리브레이션 자동화 (수동 파라미터 입력으로 우선 실험)
- 3개 이상 카메라 시점 합성
- 프로덕션 배포 수준의 최적화

## Done Criteria
- 두 동영상을 입력받아 각각 2D 랜드마크를 추출할 수 있다
- 추출한 2D 랜드마크로 3D 좌표를 합성하는 실험 파이프라인이 동작한다
- 사용한 합성 방식과 초기 정밀도 측정 결과가 문서화되어 있다

---

## Work Log

## feat: close dual video 3D synthesis experiment (#29)

> Closes the #29 experiment at the current baseline and separates remaining production-grade 3D motion work into follow-up issue scope.

#### Scope
- #29 parent management matrix finalization.
- #29 supporting plan read order and viewer floor fix plan status cleanup.
- MVP v2 umbrella row for MVP2-02 closure.
- Explicit exclusion of MVP2-03/#32 from this branch and PR.

#### Changes
- Marked the original #29 experiment done criteria as satisfied for the MVP experiment baseline.
- Updated PLAN-01 through PLAN-08 to show which parts are verified, implemented, or intentionally deferred.
- Recorded the current conclusion that #29 produced an experimental `skeleton3d.v1` synthesis/API/debug/evaluation/viewer baseline, not a production rack motion pipeline.
- Left camera rig/session world, temporal smoothing, visual regression, and product acceptance criteria as follow-up scope.

#### Verification
- `backend/.venv/Scripts/python.exe -m compileall app.py controller schema service tests`
- `uv run --with pytest python -m pytest tests/test_skeleton_mapper.py tests/test_skeleton_3d_synthesizer.py tests/test_triangulation.py`
- `npm run build` from `frontend/`
- `git diff --check`

#### Notes
- MVP2-03/rack motion pipeline requirements are intentionally not part of this #29 closure commit.

## follow-up needed: 3D synthesis viewer still appears lying / early arm jitter remains (#29)

> Attempted to tighten 3D synthesis rendering and failed-joint handling, but the user confirmed the desired visual result is still not achieved. This entry is a handoff note for the next implementation attempt.

#### Scope
- Backend triangulation output contract for failed high-reprojection joints.
- Frontend `skeleton3d.v1` adapter renderability contract.
- Three.js 3D skeleton viewer metric-coordinate orientation, floor placement, and failed-joint rendering.
- Local diagnosis of latest generated 3D synthesis artifact.

#### Changes Made In Working Tree
- `backend/service/triangulation.py`
  - If a triangulated joint exceeds `thresholds.maxReprojectionErrorPx`, it now returns `position=None` while preserving reprojection error and `failure_reason="high_reprojection_error"`.
  - Purpose: prevent known-bad 3D coordinates from being persisted as renderable positions in newly generated synthesis artifacts.
- `frontend/src/features/analysis-session/adapters.js`
  - `adaptSkeleton3DPage()` now sets `renderable: hasPosition && joint?.success !== false`.
  - Purpose: hide failed 3D joints even when older artifacts still contain numeric positions for failed joints.
- `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx`
  - Metric 3D landmarks with `success=false` are excluded from renderable landmarks, bounds, floor candidates, and bone endpoints.
  - Panoptic metric coordinates are mapped with world Y as the vertical body-height axis:
    - view X = centered world X
    - view Y = `groundY - worldY`
    - view Z = centered world Z
  - Floor/grid/glow plane are moved to the detected foot-based floor per frame.

#### Local Diagnosis
- Latest inspected artifact: `backend/tmp/synthesis/skeleton3d/synth_dff7912f.json`.
- Quality summary:
  - paired frames: `3599`
  - usable joint ratio: `0.5583`
  - successful joints: `66305 / 118767`
  - mean reprojection error: `6.6927px`
  - failure counts include `high_reprojection_error: 23947`, `low_visibility: 27986`, `pose_not_detected: 528`
- Early-frame arm jitter source:
  - Frame 0 shoulders/elbows/wrists are frequently `success=false` with high reprojection errors.
  - Example frame 0:
    - `left_shoulder`: `success=false`, reprojection error `11.6153px`
    - `left_elbow`: `success=false`, reprojection error `27.2473px`
    - `left_wrist`: `success=false`, reprojection error `61.8906px`
  - Older artifacts still contain numeric positions for some of those failed joints, so the previous frontend could render bad arms.
- "Lying skeleton" coordinate check:
  - Frame 0 successful joints indicate world Y is the height axis, not a lying body:
    - `nose.y = -168.396926`
    - `left_heel.y = -3.708562`
    - `right_heel.y = 1.931276`
    - successful-joint Y range is about `175cm`, while X/Z ranges are about `29cm` / `19cm`
  - This suggests the backend output coordinate orientation is probably not the main cause of the lying appearance. The remaining issue is likely viewer camera/rendering state, fallback preview mode, stale bundle, or an unverified Three.js canvas orientation bug.

#### Verification Run
- `backend/.venv/Scripts/python.exe -m compileall service/triangulation.py`
- `npm run build` from `frontend/`
- `git diff --check -- backend/service/triangulation.py frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx frontend/src/features/analysis-session/adapters.js`
- `backend/.venv/Scripts/python.exe -m pytest tests/test_triangulation.py` could not run because `pytest` is not installed in the backend venv.

#### Remaining Problem
- User restarted frontend/backend and reran jobs, but still observed:
  - early frames: arms jump even though the real arm is still
  - 3D synthesized skeleton still visually appears lying
- The latest change should hide failed arm joints rather than stabilize or reconstruct them. It does not solve missing/unstable 2D landmark correspondence.
- Browser-level Three.js screenshot/pixel verification was not completed, so the visual lying issue remains unresolved.

#### Suggested Next Attempt
- First verify the actual browser canvas in `FRONT` + `3D SYNTH` mode, not `A+B PREVIEW`, and confirm whether nose renders above feet.
- If it still appears lying, inspect camera preset orientation, OrbitControls target/state, and the final `toLandmarkVec3()` output inside the browser runtime.
- Consider adding a temporary debug overlay or axis labels for rendered metric X/Y/Z to make orientation failures obvious.
- Consider temporal filtering/interpolation only after failed-joint masking is confirmed; masking removes bad coordinates but does not create stable missing arms.

## fix: infer 3D synthesis camera pair from source videos (#29)

> Fixes the Visual Sync Studio 3D synthesis request so the camera pair matches the completed source videos instead of always using `00_00` and `00_01`.

#### Scope
- Frontend `Skeleton3DSynthesisSection` synthesis job creation only.
- Runtime diagnosis of latest local 2D job artifacts and generated `skeleton3d.v1` artifacts.

#### Changes
- `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx` now infers camera IDs such as `00_01` and `00_02` from `skeleton.videoInfo.displayName`, `videoSrc`, or related source metadata.
- The inferred camera IDs are passed into `createSynthesisJob()` and included in the synthesis state key so a changed camera pair creates a new synthesis job.
- This keeps the existing `00_00`/`00_01` fallback for sources that do not expose camera IDs.

#### Verification
- `npm run build` from `frontend/`
- `backend/.venv/Scripts/python.exe -` comparison for latest local `job_ad691fa7` + `job_a219317a` artifacts:
  - old hardcoded `00_00`/`00_01`: mean reprojection error `17034.1074`, first-frame successful joints `0`
  - inferred `00_01`/`00_02`: mean reprojection error `6.6927`, first-frame successful joints `16`
- `git diff --check -- frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`

#### Notes
- The failure was synthesis-input camera mapping, not a Three.js rendering failure. Existing local `skeleton3d.v1` artifacts were being written, but the wrong camera pair caused high reprojection errors and very sparse early frames.
- Existing unrelated local changes in `archive/poseLandmarker_Python-mvp-v1/config/config.py`, `backend/app.py`, and `docs/etc/businiss plan/base.md` were left untouched.

## fix: reduce post-completion browser stalls and clean uploaded source files (#29)

> Reduces browser main-thread pressure after two parallel analysis jobs complete, and prevents uploaded source videos from accumulating under `backend/tmp/uploads/`.

#### Scope
- Frontend completion hydration and skeleton playback rendering for dual analysis sessions.
- Backend transient upload cleanup for `/jobs` and `/analysis/preview`.
- Existing `backend/tmp/uploads/` local files cleanup.

#### Changes
- `frontend/src/features/analysis-session/useAnalysisSession.js` now hydrates completed sessions with the first skeleton page first, then loads remaining skeleton pages incrementally after yielding to the browser between page requests.
- `frontend/src/components/SkeletonViewer/hooks/useVideoSync.js` now runs continuous canvas redraw only while video playback is active, and renders once for pause, seek, timeupdate, loadeddata, and ended events.
- `backend/service/job_manager.py` deletes uploaded source files from `backend/tmp/uploads/` after a background job completes or fails, while leaving non-upload source paths untouched.
- `backend/controller/analysis.py` deletes preview-analysis uploaded source files after the preview request completes.
- Existing files under `backend/tmp/uploads/` were removed locally.

#### Verification
- `npm run build` from `frontend/`
- `backend/.venv/Scripts/python.exe -m compileall backend/controller/analysis.py backend/service/job_manager.py`
- `git diff --check -- frontend/src/features/analysis-session/useAnalysisSession.js frontend/src/components/SkeletonViewer/hooks/useVideoSync.js backend/controller/analysis.py backend/service/job_manager.py`
- Confirmed `backend/tmp/uploads/` has zero regular files after cleanup.

## docs: sync #29 plan docs with current implementation (#29)

> Brings the parent matrix and child plan documents back in sync with the current streaming, synthesis, API, rendering, and evaluation code paths.

#### Scope
- #29 부모 관리 문서의 `Plan Integration Matrix` 상태 최신화
- #29 하위 plan 문서들의 상태값과 본문 설명을 현재 코드 기준으로 정렬
- stale 경로와 구현 설명 정리

#### Changes
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`의 parent matrix를 현재 구현 상태에 맞춰 `구현 완료`/`검증 필요` 중심으로 갱신했다.
- `streaming-pipeline-plan.md`를 실제 4-stage bounded queue, spool artifact, post-finalize analysis 구조 기준으로 재작성했다.
- `3d-skeleton-synthesizer-plan.md`, `triangulation-implementation-plan.md`, `3d-synthesis-api-analysis-pipeline-plan.md`, `gt-evaluation-plan.md`의 상태값을 현재 코드 존재 여부에 맞춰 상향 조정했다.
- `3d-skeleton-rendering-plan.md`에 paged `skeleton3d.v1` 우선 로딩, Three.js 품질 표현, A/B fallback 경로의 현재 프론트 동작을 반영했다.
- 부모 문서 하단 관리 메모의 `backend/src/` 예정 문구를 실제 구현 경로로 교체했다.

#### Verification
- `git diff --check -- docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment`
- 관련 backend/frontend 코드 경로와 문서 상태표를 교차 확인

#### Notes
- synthesis API는 구현 완료 상태지만 3D analysis adapter와 synthesis SSE는 여전히 후속 범위로 남겨 두었다.
- 현재 활성 브랜치는 `31-docs-add-business-plan-working-materials`로 #29 브랜치와 정렬되어 있지 않다.

## feat: add 3D synthesis job API and viewer integration (#29)

> Adds a post-analysis 3D skeleton synthesis path that builds a paged `skeleton3d.v1` artifact from two completed 2D skeleton jobs and hydrates it in the Three.js viewer.

#### Scope
- Backend synthesis API, schema, artifact repository, frame alignment, triangulation, evaluator, and job manager for completed 2D skeleton artifacts.
- Frontend synthesis client calls, polling, paged `skeleton3d` loading, adapter mapping, and Three.js render integration.
- #29 synthesis, API, and rendering plan updates for the implemented MVP path.

#### Changes
- `backend/controller/synthesis.py` registers `/synthesis/jobs`, status, result, paged skeleton3d, and evaluation endpoints.
- `backend/schema/synthesis.py` defines the pair manifest, synthesis input, thresholds, job create request, and paged response models.
- `backend/service/synthesis_job_manager.py`, `backend/service/skeleton_3d_synthesizer.py`, `backend/service/triangulation.py`, `backend/service/frame_alignment.py`, `backend/service/camera_calibration.py`, `backend/service/landmark_observation.py`, `backend/service/skeleton_artifact_repository.py`, and `backend/service/skeleton_3d_evaluator.py` implement the batch synthesis pipeline and artifact persistence.
- `backend/service/job_manager.py` exposes completed skeleton artifact loading for synthesis source jobs.
- `frontend/src/api/analysisClient.js`, `frontend/src/features/analysis-session/adapters.js`, and `frontend/src/components/sections/Skeleton3DSynthesisSection/` create synthesis jobs after both sessions complete and render paged 3D skeleton output when available.
- `backend/scripts/run_3d_synthesis.py` adds a local smoke-test entry point for request JSON to skeleton3d/evaluation artifact generation.

#### Verification
- `backend/.venv/Scripts/python.exe -m compileall app.py config controller schema service scripts tests` from `backend/`
- `npm run build` from `frontend/`
- `git diff --check`
- `backend/.venv/Scripts/python.exe -m pytest tests/test_synthesis_schema.py tests/test_frame_alignment.py tests/test_triangulation.py tests/test_skeleton_3d_synthesizer.py` could not run because `pytest` is not installed in the backend venv.

#### Notes
- The synthesis pipeline currently loads completed 2D skeleton artifacts and runs batch alignment/triangulation before writing a paged result. It is not yet streaming or chunk-orchestrated end to end.

## docs: mark GT skeleton as EVAL-05 answer key (#29)

> EVAL-05 now treats the GT skeleton fixture as the correctness source and keeps reprojection as a diagnostic summary.

#### Scope
- GT evaluation planning note for EVAL-05.
- #29 management log for the commit-sized documentation update.

#### Changes
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/gt-evaluation-plan.md` now names `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json` as the EVAL-05 answer key.
- Reprojection summary is documented as triangulation quality diagnostics, separate from GT-based 3D correctness.
- The open authoritative-source decision is closed for EVAL-05.

#### Verification
- `git diff --check -- docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/gt-evaluation-plan.md`
- `git diff --check -- docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`

## docs: restore #29 work log ordering (#29)

> 관리 메모 아래로 잘못 붙은 work log 항목을 원래 로그 영역으로 되돌리고 깨진 한글을 복원했다.

#### Scope
- #29 관리 문서 로그 구조 정리
- 인코딩이 깨진 live conveyor 로그 문장 복원

#### Changes
- `fix: make live conveyor rows visually distinct even when queue depth is zero (#29)` 로그를 `Management Notes` 아래에서 `Work Log` 영역으로 이동했다.
- 같은 로그의 깨진 한글 설명과 verification 문장을 정상 문장으로 복원했다.
- `fix: constrain video upload filename overflow (#29)` 로그도 `Work Log` 영역으로 이동해 `Management Notes`가 파일 최하단의 관리 메모만 담도록 정리했다.

#### Verification
- `git diff --check`
- replacement character `U+FFFD`가 남아 있지 않음을 확인

## docs: add matrix-based plan tracking workflow (#29)

> 부모/자식 계획 문서에 matrix 기반 상태·결정·연동 추적 구조를 추가했다.

#### Scope
- #29 하위 plan 문서들의 상태/결정 matrix 표준화
- #25 umbrella, #29 부모 문서, #29 하위 plan 문서 간 상호 갱신 규칙 추가
- 재사용 가능한 workflow template 보강

#### Changes
- `docs/agent-workflow/templates.md`에 `Matrix Sync Rule`, `Plan Integration Matrix`, `Implementation Status & Decision Matrix` 템플릿을 추가했다.
- `docs/mvp-v2/issues/umbrella/mvp-v2-umbrella.md`에 하위 issue 단위 `Plan Integration Matrix`를 추가했다.
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment.md`에 하위 plan 단위 `Plan Integration Matrix`를 추가했다.
- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/README.md`를 matrix 운영 방식과 읽기 순서 기준으로 갱신했다.
- #29 하위 plan 문서들에 `Matrix Sync Rule`과 `Implementation Status & Decision Matrix`를 추가했다.

#### Verification
- `git diff --check`
- `rg`로 #29 부모/자식 문서와 workflow template의 matrix 섹션 존재 확인

#### Notes
- 부모 matrix는 통합 tracking index로 두고, 세부 구현 source of truth는 하위 plan 문서에 둔다.

## feat: dual Live View sync studio + Three.js 3D skeleton synthesis section (#29)

#### Scope
- Visual Sync Studio 리디자인 (두 세션 병렬 뷰, 공유 재생 바)
- Three.js 기반 3D 스켈레톤 합성 섹션 신규 추가
- VisualizationSettings 토글 다열 그리드 레이아웃

#### Changes

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/package.json` | `three@^0.184.0` 의존성 추가 |
| `frontend/src/App.jsx` | `sessionA` / `sessionB` 이중 세션, `Skeleton3DSynthesisSection` 추가 |
| `frontend/src/components/Toggle/Toggle.module.css` | `.row`에 `padding: 0.9rem 1.4rem` + hover background 추가 |
| `frontend/src/components/VisualizationSettings/VisualizationSettings.module.css` | 단일 flex column → 3열 CSS grid 전환 |
| `frontend/src/components/sections/LiveSyncSection/LiveSyncSection.jsx` | 이중 `LiveViewPanel` 그리드, 공유 재생/스크러버 바, `VisualizationSettings` 하단 배치로 전면 재작성 |
| `frontend/src/components/sections/LiveSyncSection/LiveSyncSection.module.css` | `.dualGrid`, `.viewerCard`, `.syncBar`, `.scrubber` 신규 스타일 |
| `frontend/src/components/sections/LiveSyncSection/LiveViewPanel.jsx` | 신규: 스코프 뷰어 (영상 + 스켈레톤 캔버스, 컨트롤 없음, props로 재생 제어) |
| `frontend/src/components/sections/LiveSyncSection/LiveViewPanel.module.css` | 신규: viewport, frameOverlay, annotationOverlay 스타일 |
| `frontend/src/components/sections/Skeleton3DSynthesisSection/` | 신규: Three.js 3D 스켈레톤 렌더러 + 합성 정보 패널 섹션 |

#### Verification

- `npm run build` (`frontend/`) — Three.js chunk size 경고 외 에러 없음

---

## feat: expose startup timing breakdown for landmarker warmup (#29)

- `backend/schema/job.py`, `backend/service/job_manager.py` 에 `stageDetails` 와 startup timing summary 를 추가해 `initializing_landmarker` 와 첫 chunk 처리 전 구간의 세부 시간을 진행 중 상태 응답에 포함
- `backend/schema/benchmark.py`, `backend/service/benchmarking.py` 에 `BenchmarkStartupSummary` 를 추가해 완료 후 benchmark 에도 `startupWallMs`, `landmarkerInitMs`, `firstChunkReadMs`, `firstChunkInferenceMs`, 첫 chunk span 정보를 보존
- `frontend/src/features/analysis-session/adapters.js`, `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx`, `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css` 에 startup breakdown UI 를 추가해 live progress 와 benchmark 패널 모두에서 초기 지연 원인을 바로 확인 가능하게 정리

**Verification**

- `py_compile`
  - `backend/schema/job.py`
  - `backend/schema/benchmark.py`
  - `backend/service/benchmarking.py`
  - `backend/service/job_manager.py`
- `npm run build` (`frontend/`)
- startup smoke test
  - `JobManager._run_streaming_pipeline(...)` 로 `hd_00_00_2min.mp4`, `samplingFps=5`, `full`, `CPU` 조건 실행
  - `startup_summary` / `progress.stageDetails` 에 `landmarkerInitMs`, `firstChunkReadMs`, `firstChunkInferenceMs`, `startupWallMs` 가 채워지는 것 확인

## feat: redesign pipeline progress UI for 4-worker streaming conveyor (#29)

- `frontend/src/features/analysis-session/adapters.js` 에서 `analyzing` 스테이지 레이블을 `'Pose inference'` → `'Streaming pipeline'` 으로 변경: 현재 내부가 FrameProducer + PoseWorker + SkeletonCollector + BenchmarkCollector 4개 병렬 worker 구조이기 때문에 "Pose inference" 표현이 부정확했음
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx` 에서 `showConveyor` 조건의 `&& frameRatio != null` 제거: 새 스트리밍 구조에서 처리 중에는 `totalFrames` 가 항상 `null` 이어서 기존 조건이 항상 false 가 되어 컨베이어가 아예 렌더링되지 않던 버그 수정
- 같은 파일에서 2트랙 컨베이어(Extract + Infer) → 4트랙 컨베이어(Frame / Pose / Skel / Bench)로 교체: 각 트랙이 실제 pipeline stage 하나씩 대응되고, 모두 `ppConveyorFlow` 스크롤 애니메이션으로 병렬 실행을 표현. `done` 상태에서는 모두 `ppConveyorDone` solid 바로 전환
- 같은 파일에서 컨베이어 하단에 `processedFrames` 카운터 추가: `totalFrames` 없이도 처리된 프레임 수를 인라인으로 표시
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css` 에서 `.ppConveyorLabel` 너비를 `3.6rem` → `4rem` 으로 확장하고, `.ppConveyorFrameCount` 스타일 추가

**Verification**

- `adapters.js` `STAGE_LABELS.analyzing` 변경 확인
- `IDLE_STEP_LABELS[3]` `'Streaming pipeline'` 으로 일치 확인
- `showConveyor` 조건이 `frameRatio` 에 의존하지 않음을 확인 (analyzing 단계 진입 시 컨베이어 즉시 표시)
- ring segment `isAnalyzingActive` 는 여전히 `frameRatio != null` 를 요구하므로 fill 오버레이는 렌더링되지 않고 pulse 애니메이션만 표시됨 (totalFrames 없는 현재 구조에 적합)

## feat: split streaming stages and spool collector outputs (#29)

- `backend/service/job_manager.py` 에서 기존 `frame chunk -> infer -> skeleton accumulate` 직렬 루프를 `frame producer -> pose worker -> skeleton collector / benchmark collector` bounded queue 구조로 재편
- 같은 파일에서 chunk / frame / collector queue 크기를 환경변수(`STREAMING_FRAME_CHUNK_SIZE`, `STREAMING_FRAME_QUEUE_MAXSIZE`, `STREAMING_POSE_QUEUE_MAXSIZE`, `STREAMING_COLLECTOR_QUEUE_MAXSIZE`)로 조정 가능하게 바꿔 현재 streaming 경로를 기본 경로로 고정
- `backend/service/skeleton_mapper.py` 에 JSONL 스풀 기반 skeleton assembler 옵션을 추가해 처리 중 frame payload 전체를 메모리에 계속 유지하지 않고, 최종 skeleton 파일 생성 시에만 재로딩하도록 변경
- `backend/service/benchmarking.py` 에 `PoseChunkBenchmarkCollector` 와 file-backed frame metric load 경로를 추가해 benchmark frame metrics 누적도 JSONL 스풀 기반으로 전환
- `backend/service/job_manager.py` 의 skeleton page / benchmark frame metrics 조회를 persisted artifact 재로딩 방식으로 바꿔 completed job 메모리 상주량을 줄임

**Verification**

- `python -m compileall backend/service/job_manager.py backend/service/skeleton_mapper.py backend/service/benchmarking.py`
- backend import smoke test:
  - `from service.job_manager import JobManager`
  - `from service.benchmarking import BenchmarkService, PoseChunkBenchmarkCollector`
  - `from service.skeleton_mapper import SkeletonMapperService`

## docs: rewrite streaming pipeline plan as staged Korean design note (#29)

- `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/streaming-pipeline-plan.md` 를 영문 설계 메모에서 한글 단계 문서로 전면 재작성
- 문서 구조를 `현재 구현의 정확한 타임라인`, `진짜 스트리밍과 가짜 스트리밍 구분`, `완성형 컨베이어로 가기 위한 다음 구현 단계` 의 3개 축으로 재정리
- 현재 `backend/service/job_manager.py`, `backend/service/video_reader.py`, `backend/service/pose_inference.py`, `backend/service/skeleton_mapper.py`, `backend/service/dual_video_synthesis_coordinator.py` 기준으로 실제 구현 상태와 미연결 지점을 구분해 문서화
- 완성형 컨베이어가 아직 아니라는 점, 현재는 bounded chunk streaming + backpressure 단계라는 점, coordinator 가 아직 orchestration 에 연결되지 않았다는 점을 명시

**Verification**

- 현재 저장소 코드 흐름 검토를 기준으로 문서 내용을 작성
- `JobManager` 청크 루프, bounded queue, `infer_chunk`, `SkeletonAssembler.add_pose_chunk`, `DualVideoSynthesisCoordinator` 미연결 상태를 코드 기준으로 재확인


### feat: stabilize streaming runtime and add dual-video coordinator foundation (#29)

- `backend/adapter/mediapipe_adapter.py` 에 Windows 전용 `platform` query patch scope 를 추가해 MediaPipe import 및 `create_from_options()` 경로가 WMI query 에서 장시간 멈추지 않도록 보강
- `backend/service/job_manager.py` 에서 초기 상태를 `initializing_landmarker` 로 분리하고, `reader -> bounded chunk queue(maxsize=2) -> inference/collector` 구조로 전환해 chunk prefetch 와 inference 가 겹치도록 조정
- 같은 파일에서 `pose_frames` 전체 누적을 제거하고 benchmark frame metric 을 chunk 단위로 누적해 최종 benchmark 생성 시 full pose frame list 없이도 summary / frame metrics 가 유지되도록 변경
- `backend/schema/job.py`, `frontend/src/features/analysis-session/useAnalysisSession.js`, `frontend/src/features/analysis-session/adapters.js`, `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx` 에 processed-frame progress (`processedFrames`, `totalFrames`) 를 반영하고 프론트가 `initializing_landmarker` 단계를 인식하도록 정렬
- `backend/schema/pose.py`, `backend/service/dual_video_synthesis_coordinator.py`, `backend/tests/test_dual_video_synthesis_coordinator.py` 에 chunk index 기준 A/B `PoseChunk` pairing 을 위한 coordinator 골격 및 단위 검증 추가

**Verification**

- `py_compile` 검증:
  - `backend/adapter/mediapipe_adapter.py`
  - `backend/schema/job.py`
  - `backend/schema/pose.py`
  - `backend/service/benchmarking.py`
  - `backend/service/job_manager.py`
  - `backend/service/dual_video_synthesis_coordinator.py`
  - `backend/tests/test_dual_video_synthesis_coordinator.py`
- 직접 런타임 검증:
  - `PoseInferenceService.open_session()` 이 lite model / CPU 기준 약 1.5s 내 초기화됨을 확인
  - `POST /jobs` 로 GT-aligned mp4 2건을 동시에 업로드해 두 job 모두 `completed` 까지 정상 종료됨을 확인
  - analyzing 중 `processedFrames` 가 `32 -> 64 -> ...` 형태로 증가하고 완료 시 `581 / 581` 로 닫히는 상태 응답 확인
- coordinator 검증:
  - venv 에 `pytest` 가 없어 `python -m pytest` 는 불가했지만, `backend/tests/test_dual_video_synthesis_coordinator.py` 의 테스트 함수를 backend workdir 에서 직접 실행해 pairing / out-of-order / pending bound / flush 동작 확인

---

### refactor: stream pose pipeline in chunks (#29)

- `backend/schema/frame.py`에 `FrameChunk`를 추가하고 `backend/schema/pose.py`에 `PoseChunk`를 추가해 프레임 청크와 포즈 청크 경계를 정의
- `backend/service/video_reader.py`에 `iter_frame_chunks()`를 추가해 전체 프레임 리스트 물질화 없이 샘플링된 프레임을 고정 크기 청크로 순차 방출
- `backend/service/pose_inference.py`에 landmarker 세션 유지형 청크 추론 경로를 추가하고, 청크 처리 직후 `frame.image` 참조를 해제해 메모리 점유를 빠르게 낮춤
- `backend/service/skeleton_mapper.py`에 `SkeletonAssembler`를 추가해 청크별 포즈 결과를 누적하고 기존 skeleton 응답 shape를 유지한 채 최종 결과를 조립
- `backend/service/job_manager.py` 메인 실행 경로를 `extract_frames() -> full-list inference` 배치 방식에서 `frame chunk -> infer chunk -> accumulate skeleton` 스트리밍 방식으로 전환
- public result / skeleton / benchmark API contract는 유지하고, Phase 1 목표에 맞춰 한 job 내부에서만 동기식 청크 스트리밍을 우선 적용

**Verification**

- 변경 파일 대상 `py_compile` 통과
- `compileall backend` 전체 검사는 `backend/.venv` 내부 서드파티 테스트 파일 인코딩 문제로 신호가 오염되어, 이번 작업에서는 변경 파일 단위 정적 검증으로 제한

---

### feat: add frontend testbed (CoreDemo + Visual Sync Studio only)

- `racl-labs-frontend-forked/app` 에서 React/Vite 앱을 `frontend/` 로 복사 (`node_modules` 제외)
- `frontend/src/App.jsx` 에서 Header, Hero, AnalysisDashboard, TechnicalPipeline, Footer, ScrollToTopButton 제거
- `CoreDemoSection` + `LiveSyncSection` 두 섹션만 남겨 MVP v2 실험 전용 샌드박스로 구성
- `npm install && npm run dev` 로 `http://localhost:5173` 에서 즉시 실행 가능

---

### chore: remove .venv from archive and add to .gitignore

- `.venv/` 를 루트 `.gitignore` 에 추가
- `archive/poseLandmarker_Python-mvp-v1/.venv/` git 추적 제거 (`git rm --cached`)
- 직전 커밋에서 `.venv` 가 통째로 커밋된 것을 수정

---

### chore: archive poseLandmarker_Python as mvp-v1 snapshot before dual-video refactor

- `poseLandmarker_Python/` → `archive/poseLandmarker_Python-mvp-v1/` 로 복사
- 원본 `poseLandmarker_Python/` 는 #29 작업(이중 영상 3D 합성 파이프라인)을 위해 별도 수정 예정
- 아카이브 목적: mvp-v1 단일 카메라 파이프라인 스냅샷 보존

---

### docs: document 171204_pose1 dataset structure and experiment usage

- 데이터셋 위치: `171204_pose1/`
- 데이터셋 출처: CMU Panoptic Studio (`171204_pose1` 시퀀스)
- `171204_pose1/README.md` 신규 작성

**데이터셋 구성 파악 결과**

| 구성 요소 | 내용 |
|-----------|------|
| 캘리브레이션 JSON | 카메라 520대 (HD 31, VGA 479, Kinect 10)의 K, distCoef, R, t |
| HD 영상 | 1920×1080 / 29.97fps / `hd_00_00` ~ `hd_00_05` (6개) |
| 3D 포즈 GT (perFrame) | COCO-19 관절 / 27,561 프레임 / x,y,z(cm)+score |
| 3D 포즈 GT (JSONL) | 위와 동일, `frame` 필드 포함 |

**실험 활용 방안**

- `hd_00_00.mp4`와 `hd_00_01.mp4` 두 영상에 MediaPipe 적용 → 2D 랜드마크 추출
- 캘리브 JSON의 `00_00`, `00_01` 카메라 파라미터(K, R, t)로 triangulation 수행
- `body3DScene_*.json` GT와 MPJPE 비교로 정량 평가 가능
- 캘리브레이션 자동화 없이 바로 실험 시작 가능한 조건 확보

**미결 사항**

- MediaPipe 33개 관절 ↔ COCO-19 19개 관절 매핑 테이블 미정의
- 영상 프레임 번호와 GT `univTime` 동기화 방식 미확정

---

### feat: prepare GT-aligned 2-minute clips and extract matching GT frames

**목적**: #29 MediaPipe 파이프라인 초기 실험을 위한 데이터 준비

**작업 내용**

- `pip install imageio imageio-ffmpeg` 로 ffmpeg 바이너리 확보
- `trim_hd_videos.py` 작성 및 실행 — `hdVideos/` 6개 원본(~17분 36초)을 앞 2분으로 무손실 트리밍 → `hdVideos_2min/`
- GT 확인 결과: `hdPose3d_stage1_coco19.tar` 내 GT가 프레임 **118번부터** 시작 (앞 3.94초 GT 없음)
- `prepare_gt_aligned_clips.py` 작성 및 실행:
  - `hdVideos_2min/` 6개 클립에서 앞 118 프레임(3.94초) 제거 → `hdVideos_gt_aligned/` (`hd_00_0X_gt.mp4`)
  - `hdPose3d_stage1_coco19.tar` 에서 프레임 118~3596 범위(3,479개) 선택 추출 → `hdPose3d_2min/`
- `.gitignore` 업데이트: 영상·GT JSON 제외, 스크립트·메타데이터 추적

**생성 파일 (추적 대상)**

| 파일 | 설명 |
|------|------|
| `171204_pose1/171204_pose1/trim_hd_videos.py` | 원본→2분 트리밍 스크립트 |
| `171204_pose1/171204_pose1/prepare_gt_aligned_clips.py` | GT 정렬 클립·GT 추출 스크립트 |
| `171204_pose1/171204_pose1/hdVideos_2min/metadata.json` | 2분 클립 메타데이터 |
| `171204_pose1/171204_pose1/hdVideos_2min/README.md` | 2분 클립 설명 문서 |
| `171204_pose1/171204_pose1/hdVideos_gt_aligned/metadata.json` | GT 정렬 클립 메타데이터 |

**생성 파일 (gitignore, 로컬 전용)**

| 경로 | 내용 |
|------|------|
| `hdVideos_2min/hd_00_0X_2min.mp4` × 6 | 2분 원본 클립 (각 274~340 MB) |
| `hdVideos_gt_aligned/hd_00_0X_gt.mp4` × 6 | GT 정렬 클립 (각 267~331 MB) |
| `hdPose3d_2min/body3DScene_XXXXXXXX.json` × 3,479 | GT JSON (프레임 118~3596) |

**클립 사양**

| 항목 | 값 |
|------|-----|
| 프레임 범위 | 118 ~ 3596 |
| 시간 범위 | 3.94초 ~ 120초 |
| 길이 | ~116.06초 |
| GT 대응 | 프레임 번호 직접 매핑 가능 |

---

### chore: merge GT skeleton frames 118~3596 into single JSON

**목적**: MediaPipe 파이프라인 평가 시 프레임별 GT 파일 개별 로드 없이 단일 파일로 접근 가능하게 함

**작업 내용**

- `hdPose3d_stage1_perFrame_coco19/body3DScene_00000118.json` ~ `body3DScene_00003596.json` (3,479개)를 하나의 JSON으로 병합
- 출력: `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json`
- missing 프레임: 0개 (3,479 프레임 전체 포함)

**생성 파일**

| 파일 | 크기 | 설명 |
|------|------|------|
| `171204_pose1/171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json` | 2.6 MB | 프레임 118~3596 GT 스켈레톤 병합 파일 |

**파일 구조**

```json
{
  "frame_range": [118, 3596],
  "frame_count": 3479,
  "missing_frames": [],
  "frames": [
    { "frame": 118, "version": 0.7, "univTime": ..., "fpsType": "hd_29_97", "bodies": [...] },
    ...
  ]
}
```

---

### feat: CoreDemoSection 이중 영상 입력 지원 및 Pipeline Progress 벤치마크 진단 패널 추가

**목적**: 두 영상을 동시에 분석할 수 있는 프론트엔드 기반 마련, 분석 실패 시 원인 파악을 위한 벤치마크 진단 정보 표시

**변경 파일**

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/App.jsx` | `useAnalysisSession` 두 인스턴스(`sessionA`, `sessionB`) 사용, `CoreDemoSection`에 두 세션 전달 |
| `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx` | 이중 영상 레이아웃 및 벤치마크 패널 구현 |
| `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css` | 이중 레이아웃·벤치마크 섹션 스타일 추가 |
| `frontend/src/features/analysis-session/useAnalysisSession.js` | job `failed` 시 `loadBenchmark` 자동 호출 추가 |

**이중 영상 입력 (CoreDemoSection)**

- `primaryGrid` 레이아웃: `minmax(32rem, 40rem) 2fr` — Analysis Settings 고정 너비, Pipeline Progress 2배 점유
- Analysis Settings 패널: Video A / Video B `VideoUpload` 나란히 배치, FPS·bodyweight·model 등 공유 설정은 두 세션 동시 업데이트(`updateSharedForm`)
- Start Analysis: 두 영상이 모두 업로드된 경우에만 활성화, `sessionA.startAnalysis()` + `sessionB.startAnalysis()` 동시 호출
- Pipeline Progress 패널: `ProgressColumn` 컴포넌트 추출 — Video A / Video B 두 열을 1px 구분선으로 나란히 배치
- `LiveSyncSection`은 `sessionA`만 유지 (기존 동작 보존)

**Pipeline Progress 벤치마크 진단 패널**

분석 완료 또는 실패 후 각 `ProgressColumn` 하단에 표시. `BenchmarkResult` 스키마 전체 필드 기반.

| 섹션 | 표시 항목 | 경고 조건 |
|------|-----------|-----------|
| **Quality** | `analysisSuccess`, pose detected 비율(분자/분모), avg/min visibility, low vis. frame 비율, max consecutive missed frames | `analysisSuccess=false`, detection < 50%, visibility < 0.5, low vis > 40%, missed > 30 frames |
| **Run** | delegate requested → actual, `delegateErrors` dict 원문, model variant · backend, frame count @ fps · interval, sampling fps mismatch | fallback 적용, delegateErrors 존재, fps mismatch |
| **Timing** | `stageStats` 각 단계: label + bar(shareRatio) + totalMs + % + avg/p95(per-frame 단계) | — |
| **LLM Call** | model, enabled/fallback 여부, input/output 토큰, latency, prompt reduction ratio | disabled, fallback |
| **Raw JSON** | `frameMetrics` 제외 전체 JSON, collapsible `<details>`, 스크롤 가능 pre | — |

- job `failed` 시 `loadBenchmark` 자동 호출 — 백엔드가 benchmark를 생성한 경우 자동 표시
- benchmark 미로드 상태에서 `status=completed|error`이고 `jobMeta.jobId` 존재하면 "Load Benchmark" 수동 버튼 표시
- Error Detail 섹션: `status=error`이고 `jobMeta.error` 존재 시 `error.code` + `error.message` 표시

---

### chore: add missing MediaPipe pose landmarker model files

- `poseLandmarker_Python/models/mediapipe/` 에 `pose_landmarker_lite.task`, `pose_landmarker_heavy.task` 추가
- 기존에는 `pose_landmarker_full.task` 만 존재했으며, `lite` / `heavy` 요청 시 파일 없음 오류 발생
- config에 세 variant 모두 정의되어 있으나 실제 파일이 없어 `lite` 모델 사용 불가 상태였음

---

### chore: rename poseLandmarker_Python to backend

- `poseLandmarker_Python/` → `backend/` 디렉토리 rename (git mv)
- `frontend/`와 `backend/`로 디렉토리 구조 통일

---

### refactor: switch to general motion experiment mode, defer squat pipeline

**목적**: 스쿼트 전용 파이프라인을 미뤄두고 임의 동작(general motion) 기반 스켈레톤 추출 실험 모드로 전환. 스쿼트 코드는 주석으로 보존하여 복구 가능하게 유지.

**변경 파일**

| 파일 | 변경 내용 |
|------|-----------|
| `poseLandmarker_Python/config/config.py` | `MOCK_VIDEO_EXERCISE_TYPE = None`, `BODYWEIGHT = None`, `EXTERNAL_LOAD = None` (스쿼트 값 주석 보존) |
| `poseLandmarker_Python/service/analysis_pipeline.py` | `_resolve_exercise_type`: None → `"general_motion"`. `analyze()`에 general_motion 분기 추가 — `preprocess` + 기본 통계만 수행, 스쿼트 단계 스킵. `_analyze_general_motion()` 메서드 추가. 스쿼트 파이프라인 코드 원본 보존. |
| `poseLandmarker_Python/service/job_manager.py` | `_execute_pipeline`: `exerciseType == "general_motion"` 시 LLM feedback 단계 스킵, 빈 `LlmFeedbackResult` 반환 |
| `frontend/src/api/analysisClient.js` | `exerciseType: 'squat'` hardcode 제거, `bodyweightKg`/`externalLoadKg`/`barPlacementMode` 전송 제거 (주석 보존) |
| `frontend/src/features/analysis-session/useAnalysisSession.js` | `DEFAULT_FORM`에서 스쿼트 전용 필드 제거(주석 보존). 스쿼트 검증 로직 제거. `buildUserError` 스쿼트 메시지 제거 |
| `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx` | Exercise Type / Bar Placement / Bodyweight / External Load 필드 제거, "General Motion (experiment)" 표시. 스쿼트 필드 JSX 주석 보존 |

**동작 변화**

- 영상 업로드 시: 프레임 추출 → Pose inference → 스켈레톤 매핑 → 기본 통계(frame count, detection ratio, fps) 반환
- 스쿼트 전용 단계(rep 감지, KPI, CoP, thresholds, issues, LLM feedback) 모두 스킵
- 복구 방법: 각 파일의 주석 처리된 스쿼트 코드 활성화, `_resolve_exercise_type`에서 squat 분기 복원

---

### fix: VideoReaderService 동시 실행 시 OpenCvAdapter 공유로 인한 레이스 컨디션 수정

**목적**: 두 job을 동시에 실행할 때 한 job이 항상 실패하는 버그 수정

**원인**

`JobManager`가 `VideoReaderService` 인스턴스를 하나만 보유하고, 이 서비스 내부에서 `OpenCvAdapter`(= `cv2.VideoCapture` 핸들)를 `self._adapter`로 캐싱해 모든 job이 공유하고 있었다.

두 job이 `asyncio.to_thread`로 동시에 실행될 때 두 스레드가 같은 어댑터 인스턴스를 경쟁하면서 다음 두 버그가 겹쳐 실패가 발생했다:

1. **`open_video`의 선행 `self.close()` 호출** (`opencv_adapter.py:50`): Job B가 `open_video` 진입 시 무조건 `self.close()`를 먼저 호출해 Job A가 진행 중인 `VideoCapture` 핸들을 파괴
2. **`self._adapter` 직접 참조** (`video_reader.py:54`): `iter_frames`의 while 루프가 로컬 변수 `adapter` 대신 `self._adapter`를 직접 참조해, 다른 스레드가 어댑터를 교체하면 잘못된 핸들을 읽음

결과적으로 Job A의 `finally: adapter.close()`가 Job B의 진행 중인 캡처를 닫거나, Job B의 `open_video`가 Job A의 캡처를 닫아 `"Video source not found"` 또는 `"Video is not opened"` 에러로 실패가 발생했다.

`_last_metadata` 인스턴스 변수도 두 스레드가 공유해 메타데이터 오염이 발생할 수 있었다.

**수정 내용**

| 파일 | 변경 내용 |
|------|-----------|
| `backend/service/video_reader.py` | `iter_frames` 호출마다 새 `OpenCvAdapter()` 생성 (공유 캐시 제거). while 루프를 `self._adapter` 대신 로컬 `adapter` 변수 참조로 통일. `_last_metadata` 공유 인스턴스 변수를 `_out_metadata` 로컬 dict 전달 방식으로 교체. `_get_adapter()` 메서드 제거 |

**수정 후 동작**

각 `iter_frames` 호출이 독립적인 `OpenCvAdapter` + `VideoCapture` 핸들을 가지므로 동시 실행 job들이 서로 영향을 주지 않음.

---

### fix: PoseInferenceService 동시 실행 시 공유 MediaPipeAdapter 레이스 컨디션 수정

**목적**: 두 job을 동시에 실행할 때 `ValueError: Input timestamp must be monotonically increasing` 및 `LandmarkerInitializationError` 로 두 job 모두 실패하는 버그 수정

**원인**

`JobManager`가 `PoseInferenceService` 인스턴스를 하나만 보유하고, 이 서비스 내부의 `MediaPipeAdapter`(`self._landmarker`)를 모든 job이 공유하고 있었다.

두 job이 `asyncio.to_thread`로 동시에 실행될 때 두 스레드가 같은 어댑터 인스턴스를 경쟁하면서:

1. Job A가 `iter_infer` → `create_landmarker` → landmarker A 생성
2. Job B가 `iter_infer` → `create_landmarker` → `close_landmarker()` (Job A의 landmarker 파괴!) → landmarker B 생성
3. Job A가 frame 0을 infer 시도 → landmarker B에 엉뚱한 타임스탬프 전송 → `Input timestamp must be monotonically increasing` 에러
4. Job A의 `finally: close_landmarker()` 실행 → landmarker가 None
5. Job B가 frame 1을 infer 시도 → `LandmarkerInitializationError: not initialized` 에러

**수정 내용**

| 파일 | 변경 내용 |
|------|-----------|
| `backend/service/job_manager.py` | `__init__`에서 공유 `self._pose_inference` 제거. `_execute_pipeline` 호출마다 새 `PoseInferenceService()` 인스턴스 생성 |

**수정 후 동작**

각 pipeline 실행이 독립적인 `PoseInferenceService` + `MediaPipeAdapter` + `PoseLandmarker` 인스턴스를 가지므로 동시 실행 job들이 서로 영향을 주지 않음.

---

### experiment: 두 영상 동시 병렬 처리 벤치마크 실험

**목적**: 레이스 컨디션 수정 후 두 job을 동시에 실행했을 때의 안정성 및 성능을 정량적으로 검증

**실험 조건**

| 항목 | 값 |
|------|-----|
| 영상 | `hd_00_01_gt.mp4`, `hd_00_02_gt.mp4` (CMU Panoptic GT-aligned 클립) |
| 실행 방식 | 단일 브라우저 세션에서 두 job 동시 제출 |
| 모델 | MediaPipe Pose Landmarker lite |
| Delegate | CPU (GPU fallback 없음) |
| 샘플링 FPS | 29.97 (원본 전체 프레임) |
| 프레임 수 | 3,481 프레임 × 2 job |

**성능 결과**

| 지표 | job_ff65b7d2 (video 01) | job_0080b2d8 (video 02) | 차이 |
|------|------------------------|------------------------|------|
| 총 소요 시간 | 267,004 ms (4m 27s) | 264,414 ms (4m 24s) | ~1% |
| Frame Extraction | 86,139 ms | 85,822 ms | ~0.4% |
| RGB Conversion | 114,361 ms | 111,638 ms | ~2.4% |
| Inference | 62,452 ms | 61,144 ms | ~2.1% |
| 추론 평균 (per frame) | 17.94 ms | 17.57 ms | ~2.1% |
| 추론 p95 (per frame) | 21.96 ms | 21.95 ms | ~0.1% |

**품질 결과**

| 지표 | job_ff65b7d2 (video 01) | job_0080b2d8 (video 02) |
|------|------------------------|------------------------|
| 포즈 감지율 | 99.71% (3,471 / 3,481) | 99.40% (3,460 / 3,481) |
| 평균 가시성 | 0.7994 | 0.8290 |
| 낮은 가시성 프레임 비율 | 44.67% | 39.39% |
| 연속 미감지 최대 | 9 프레임 | 6 프레임 |

**병목 분석 (두 job 평균)**

| 단계 | 비율 | 비고 |
|------|------|------|
| RGB Conversion | ~43% | 최대 병목. CPU에서 BGR→RGB 변환 |
| Frame Extraction | ~32% | 디코딩 |
| Inference | ~23% | MediaPipe 추론 자체 |
| Serialization + Analysis | ~1% | 무시 가능 |

**결론**

- 두 job 간 총 소요 시간 차이 **~1%** — 동시 실행 간섭 없이 안정적으로 병렬 처리됨
- `VideoReaderService` / `PoseInferenceService` 레이스 컨디션 수정(`ab262f0`, `6fa604e`) 이후 동시 실행 안정성 확인
- 두 영상 모두 **99% 이상 포즈 감지율** 달성 — 품질 기준 충족
- video 01이 낮은 가시성 비율이 더 높은 것(44.67% vs 39.39%)은 영상 자체의 조명·각도 차이로 판단
- **다음 최적화 후보**: RGB Conversion 단계(전체의 ~43%) — 배치 처리 또는 GPU delegate 전환 시 병목 이동 여부 확인 필요

---

### chore: gitignore에 archive/tmp 및 backend/tmp 추가, 추적 중인 임시 파일 제거

**목적**: `archive/poseLandmarker_Python-mvp-v1/tmp/` 하위 818개 파일이 git에 추적되어 push 용량을 대폭 증가시키는 문제 수정

**원인**

`.gitignore`가 구 경로인 `poseLandmarker_Python/tmp/`만 제외하고 아카이브로 복사된 `archive/poseLandmarker_Python-mvp-v1/tmp/`와 리네임된 `backend/tmp/`를 누락했다. 아카이브 복사 시 업로드 mp4, 프레임 JPEG, 벤치마크 JSON 등 818개 임시 파일이 함께 커밋됐다.

**수정 내용**

| 파일 | 변경 내용 |
|------|-----------|
| `.gitignore` | `archive/poseLandmarker_Python-mvp-v1/tmp/*` 추가 (`.gitkeep` 제외), `backend/tmp/` 추가, `backend/src/video/` 추가 |

- `git rm --cached`로 818개 파일을 인덱스에서 제거 (로컬 파일 유지)

---

### chore: git history에서 대용량 바이너리 제거 및 다운로드 안내 추가

**목적**: `.task` 모델 파일(~46MB)과 `.mp4` 영상 파일이 git history에 포함되어 push 용량이 80MB에 달하는 문제 해결

**작업 내용**

- `git filter-repo`로 history 재작성: `*.task`, `*.mp4` 전체 제거
- `.gitignore`에 `**/models/mediapipe/*.task`, `archive/**/src/video/` 추가
- `README.md`에 "로컬 설정" 섹션 추가 — MediaPipe 공식 다운로드 URL 3개, 테스트 영상은 이현규에게 요청

**수정 파일**

| 파일 | 변경 내용 |
|------|-----------|
| `.gitignore` | 모델·아카이브 영상 패턴 추가 |
| `README.md` | 로컬 설정 섹션(모델 다운로드 명령어, 테스트 영상 요청처) 추가 |

---

### perf: BGR→RGB 변환을 VideoReader로 이전 및 벤치마크 타이머 분리

**목적**: 전체 처리 시간의 ~43%를 차지하던 RGB Conversion 병목 해소

**원인 분석**

`pose_inference.py`의 `_ensure_rgb`가 `image[:, :, ::-1]`로 numpy view를 만든 뒤 `mp.Image(data=view)`를 호출했다. negative channel stride를 가진 non-contiguous 배열을 MediaPipe C extension이 느린 경로로 복사하면서 ~32 ms/frame의 병목이 발생.

**수정 내용**

| 파일 | 변경 내용 |
|------|-----------|
| `backend/service/job_manager.py` | `convert_bgr_to_rgb=False` → `True` — 프레임 추출 시 `cv2.cvtColor(BGR→RGB)` 적용 |
| `backend/service/pose_inference.py` | `_ensure_rgb` 호출 및 메서드 제거. `frame.image`(이미 contiguous RGB)를 바로 `to_mp_image`에 전달 |
| `backend/schema/pose.py` | `PoseFrameBenchmark.rgb_conversion_ms` → `mp_image_creation_ms` |
| `backend/schema/benchmark.py` | `BenchmarkFrameMetric`, `BenchmarkTimingSummary` 필드 동일 rename |
| `backend/service/benchmarking.py` | stage key `rgb_conversion` → `mp_image_creation`, label 및 집계 변수명 업데이트 |
| `backend/README.md` | 필드명 설명 업데이트 |

**기대 효과**

- `mp.Image` 생성 시 C-contiguous 배열 전달 → fast memcpy 경로 사용
- BGR→RGB 변환 단계는 `cv2.cvtColor`(C-level)로 이전되어 VideoReader Frame Extraction 시간 내에 흡수
- 벤치마크 필드명이 측정 대상(`mp.Image` 생성 시간)을 정확히 반영

---

### chore: PORT/HOST를 환경변수로 제어 가능하도록 변경

- `backend/config/config.py`: `PORT = 8000` 하드코딩 → `int(os.getenv("PORT", "8000"))` 로 변경. `HOST`도 동일하게 환경변수 우선
- `backend/.env.example`: `PORT`, `HOST` 항목 추가
- `backend/.env` (로컬 전용, gitignore): `PORT=8080` 설정

---

### feat: job 상태를 SSE로 푸시, polling 제거

**목적**: 클라이언트가 주기적으로 `GET /jobs/{jobId}`를 폴링하는 대신, 서버가 상태 변경 시 직접 클라이언트에 전달하도록 변경

**변경 내용**

| 파일 | 변경 내용 |
|------|-----------|
| `backend/service/job_manager.py` | `_sse_queues`, `_loop` 추가. `_notify_subscribers` — `_set_progress`/`_fail_job` 호출 시 asyncio Queue에 status push. `stream_status` async generator — SSE 청크 yield |
| `backend/controller/jobs.py` | `GET /jobs/{job_id}/stream` 엔드포인트 추가 (`StreamingResponse`, `text/event-stream`) |
| `frontend/src/api/analysisClient.js` | `getBaseUrl` export, `openJobStream(jobId)` 추가 |
| `frontend/src/features/analysis-session/useAnalysisSession.js` | `pollJob` + `getPollingDelay` 제거 → `streamJob` (EventSource 기반)으로 교체. `runRef`에서 `timeoutId`/`pollCount` 제거, `eventSource` 추가 |

**동작 흐름**

1. job 생성 → `streamJob(jobId)` 호출 → `EventSource(/jobs/{jobId}/stream)` 연결
2. 서버: 연결 즉시 현재 status 전송. 이후 `_set_progress` 호출마다 `_notify_subscribers` → queue push → SSE 청크 yield
3. 클라이언트: `onmessage`에서 status 처리. `completed` 수신 시 result/skeleton fetch. `failed` 수신 시 error 처리
4. 25초 무변화 시 `: keepalive` 청크로 연결 유지

**제거된 것**

- `getPollingDelay` (adaptive delay 계산 함수)
- `window.setTimeout` 기반 recursive polling
- `pollCount` 추적

---


## feat: add streaming pipeline timing summary (#29)

- `backend/service/job_manager.py` now collects per-worker chunk metrics and exposes frame/pose/skeleton/benchmark queue depth, average/p95 chunk timings, and estimated total frame count through progress `stageDetails` and final `pipeline_summary`.
- `backend/service/video_reader.py` adds `probe_metadata()` so the streaming path can read frame count up front, and `backend/schema/benchmark.py` plus `backend/service/benchmarking.py` now persist the same metrics through `BenchmarkPipelineSummary` and pipeline stage stats.
- `backend/main.py` switches reload control to the `RELOAD` environment variable, and `backend/config/config.py` updates the default `PORT` to `8080` to match the current local development flow.

**Verification**

- `python -m compileall backend/service/job_manager.py backend/service/video_reader.py backend/service/benchmarking.py backend/schema/benchmark.py backend/main.py backend/config/config.py`
- `git diff -- backend/config/config.py backend/main.py backend/schema/benchmark.py backend/service/benchmarking.py backend/service/job_manager.py backend/service/video_reader.py` to confirm the implementation scope stays limited to pipeline timing summary and local runtime configuration.

---
## docs: add 3D synthesizer planning note and decision guide (#29)

> 두 개의 2D 스켈레톤 JSON을 3D로 합성하기 전에 필요한 준비사항과 사용자 결정 포인트를 분리해 문서화했다.

#### Scope
- 3D 합성기 준비 상태를 코드 기준으로 정리하는 하위 설계 문서 추가
- 아직 결정되지 않은 항목을 사용자가 쉽게 판단할 수 있도록 설명 보강

#### Changes
- docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/3d-skeleton-synthesizer-plan.md 신규 작성
- 문서에 현재 준비된 것, 아직 없는 계층, 추천 구현 순서, 권장 파일 구조를 정리
- 같은 문서에 사용자 결정이 필요한 항목 섹션을 추가해 입력 범위, 프레임 정합, 카메라/캘리브레이션 전달 방식, MediaPipe z 처리, 3D 출력 포맷, 품질 처리, 평가 기준, 분석 연결 시점을 쉬운 설명과 추천안으로 정리

#### Verification
- 현재 저장소 코드와 실험 데이터 문서를 기준으로 설계 판단이 맞는지 재검토
- 문서 경로와 부모 관리 문서 관계가 #29 하위 문서 구조와 일치하는지 확인

#### Notes
- 이번 작업은 문서 추가/정리에 한정되며 코드 변경은 없다

---
## docs: organize #29 design notes under nested sub-issue folder (#29)

- Moved #29 supporting design notes into `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/` so the root `sub-issues/` folder keeps only issue/chore management documents.
- Added `docs/mvp-v2/issues/sub-issues/README.md` to document the root folder rule: management documents at root, supporting design notes under child folders.
- Added `docs/mvp-v2/issues/sub-issues/29-feat-dual-video-skeleton-3d-synthesis-experiment/README.md` to capture #29 document roles and read order.
- Updated moved #29 design-note links to use shorter local filenames after the folder split.
- Updated `docs/mvp-v2/issues/README.md` to point readers to the sub-issues index and nested design-note convention.

**Verification**

- `rg` check for old flat #29 design-note filenames returned no remaining matches.
- `git diff --check -- docs/mvp-v2/issues/README.md docs/mvp-v2/issues/sub-issues` passed.
- Confirmed every file listed in the #29 nested README exists at its new path.

---
## fix: make live conveyor rows visually distinct even when queue depth is zero (#29)

- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.jsx`에서 pipeline row metadata에 `activityCount`, `hasWork`, `activityRatio`를 추가하고, row와 track에 `data-kind` / `data-live`를 부여해 Pose worker의 queue backlog가 0이어도 실제 처리 중인 row가 비활성처럼 보이지 않도록 정리했다.
- 같은 파일에서 queue fill과 active fill을 분리해, `queueDepth`가 0이어도 이미 chunk를 처리한 row의 진행 상태가 드러나도록 했다.
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css`에서 Frame / Pose / Skel / Bench 트랙의 stripe / fill 색상을 분리하고, live row의 label/count contrast를 높여 Pose row가 진행 중임을 더 명확히 보이게 했다.

**Verification**

- `npm run build` (`frontend/`)
- `CoreDemoSection.jsx`에서 `queueRatio`와 별개로 `step.status === 'active' && row.hasWork` 기준 row-level active fill이 렌더링되는지 확인
- `CoreDemoSection.module.css`에서 `[data-kind="pose"]` 기반 stripe / fill 스타일이 markup과 연결되는지 확인

---
## fix: constrain video upload filename overflow (#29)

> Keep dual video upload cards inside their grid columns and truncate long selected file names.

#### Scope
- Frontend dual-video upload layout and selected filename display only.

#### Changes
- `frontend/src/components/sections/CoreDemoSection/CoreDemoSection.module.css` uses `repeat(2, minmax(0, 1fr))` for the dual upload grid and sets `min-width: 0` on upload columns so long file names cannot widen the grid.
- `frontend/src/components/VideoUpload/VideoUpload.module.css` constrains `uploadArea` to the parent width and applies ellipsis overflow handling to the selected filename label.
- `frontend/src/components/VideoUpload/VideoUpload.jsx` adds a `title` attribute for the selected filename so the full name remains available on hover.

#### Verification
- `npm run build` (`frontend/`)
- `git diff --check`

---
## perf: reduce post-completion frontend rendering pressure (#29)

> Further reduces browser main-thread pressure after two parallel analysis jobs complete by pausing offscreen 3D rendering and lowering skeleton page merge priority.

#### Scope
- Frontend completion hydration for paged 2D skeleton data.
- Three.js 3D skeleton viewer render loop behavior.

#### Changes
- `frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx` now gates the Three.js render loop with `IntersectionObserver`, so the 3D canvas does not keep an always-on `requestAnimationFrame` loop while it is offscreen.
- The 3D viewer now renders immediately on frame or camera changes only when visible, while stopping the render loop when outside the viewport margin.
- `frontend/src/features/analysis-session/useAnalysisSession.js` now wraps remaining skeleton page merges in `startTransition`, yields once more before appending fetched pages, and removes duplicate raw-frame filtering during page merge.

#### Verification
- `npm run build` from `frontend/`
- `git diff --check -- frontend/src/features/analysis-session/useAnalysisSession.js frontend/src/components/sections/Skeleton3DSynthesisSection/ThreeJSSkeleton.jsx`
- `npm run lint` from `frontend/` currently cannot run because ESLint v9 does not find `eslint.config.js` in `frontend/`.

#### Notes
- Existing unrelated local changes in `archive/poseLandmarker_Python-mvp-v1/config/config.py`, `backend/app.py`, and `docs/etc/businiss plan/` were left untouched.

---
## Management Notes

### Follow-up Candidates
- 카메라 캘리브레이션 자동화
- 3개 이상 시점으로 확장
- 실시간 처리 파이프라인

### Notes
- 현재 단일 카메라 파이프라인: `backend/`
- 3D 합성 실험 코드는 `backend/service/`, `backend/controller/synthesis.py`, `backend/schema/synthesis.py`, `backend/scripts/run_3d_synthesis.py`, `frontend/src/components/sections/Skeleton3DSynthesisSection/`에 분산 구현되어 있다
- 카메라 파라미터 (focal length, baseline 등) 는 초기 실험 단계에서 수동 입력으로 진행

### References
- #25 MVP v2 Tracking (상위 이슈)
- #29 GitHub 이슈: https://github.com/rack-labs/rack-tracker/issues/29
- MediaPipe Pose Landmarker 공식 문서
