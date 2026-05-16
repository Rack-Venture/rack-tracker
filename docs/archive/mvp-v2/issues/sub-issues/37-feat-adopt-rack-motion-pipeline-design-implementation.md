# [feat] Adopt Rack Motion Pipeline Design And Implementation
Parent: #25
GitHub: #37

## Document Relations
- This document tracks the follow-up implementation work after #32.
- Requirements input: `docs/mvp-v2/issues/sub-issues/32-feat-rack-motion-pipeline-requirements/`
- Keep this file name aligned with the issue branch name.
- Place detailed design and implementation notes under `37-feat-adopt-rack-motion-pipeline-design-implementation/`.
- Update this document before each related commit.

## Summary
Adopt the #32 clean-room requirements into rack-tracker-specific design and implementation. The work must turn the requirements baseline into project-owned architecture, schemas, fixtures, and first pipeline components without importing external source-project code, structure, naming, generated artifacts, tests, or sample data.

## Goal
- Define the rack-tracker adoption plan for rack motion artifacts and pipeline ownership.
- Harden project-specific design documents before implementation expands.
- Implement the first safe, rack-tracker-owned pipeline slice with validation coverage.
- Keep clean-room constraints visible for future contributors.

## Scope
- Project-specific architecture and design documentation.
- First implementation slice for pipeline contracts, schemas, validation fixtures, or service boundaries.
- Synthetic or rack-tracker-owned validation inputs only.
- Tests that verify the first adopted contracts or components.

## Out Of Scope
- Importing or adapting externally licensed implementation material.
- Copying external source-project module layout, class names, function names, schema names, tests, sample data, generated artifacts, comments, log messages, or default thresholds.
- Completing the full production rack motion pipeline in one work unit.
- Final product license selection.

## Done Criteria
- A rack-tracker-specific adoption/design document exists and references #32 only as requirements input.
- The first implementation slice is scoped to rack-tracker-owned modules and schemas.
- Clean-room constraints remain explicit in docs and PR text.
- Tests or validation fixtures use rack-tracker-owned synthetic data or separately cleared inputs.

## Work Log

## fix: rack motion viewer not loading — only fetch when synthesis is completed (#37)

- `frontend/src/App.jsx`: `RackMotionStage1Section`에 전달되는 `synthesisJobId`를 `synthesisSession.status === 'completed'`일 때만 `synthesisSession.jobId`로 설정.
  - 수정 전: `synthesisSession.jobId ?? synthesisJobId` — job 생성 즉시 (synthesis 진행 중) non-null이 됨.
  - 수정 후: synthesis 완료 전에는 `synthesisJobId`(이전 완료 job_id 또는 null)를 유지.
  - 근거: `synthesisSession.jobId`는 job 생성 시 즉시 세팅되므로, synthesis 아직 완료 전에 rack motion fetch가 먼저 실행되어 skeleton3d artifact 없음(404) → `setError` → 이후 synthesis 완료되어도 useEffect 재실행 없음(jobId prop 값 불변) → 에러 상태에 고착됨.

## fix: correct panoptic_world_cm → rack_world axis mapping in skeleton3d_to_rack_mapper (#37)

- `backend/service/skeleton3d_to_rack_mapper.py`: X-Z 축 교체 및 부호 수정.
  - 수정 전: `rack_x = panoptic_x`, `rack_z = panoptic_z` (identity_assumed — 실제론 90° 틀어짐)
  - 수정 후: `rack_x = -panoptic_z`, `rack_y = -panoptic_y` (변경 없음), `rack_z = -panoptic_x`
  - 근거: Panoptic cameras(00_11, 00_21)는 panoptic -X 방향(X≈-143~-242 cm)에 위치하므로 rack front(카메라 방향) = -panoptic_x = +rack_z. 측면(lateral)은 panoptic Z축이며 lifter's right = panoptic -Z = +rack_x.
  - 증상: front view에서 스켈레톤이 90° 왼쪽으로 돌아서 보임 (lateral이 depth로 렌더링됨).
- `backend/tests/test_rack_motion_repository.py`: `test_from_skeleton3d_converts_cm_to_meters` assertion 갱신.
  - 픽스처 `x=-14.3, y=-145.0, z=5.0 cm` 기준 기대값 재계산 후 z 검증 추가.

## fix: prefetch remaining skeleton3D pages after synthesis completes (#37)

- Added sequential background prefetch loop in `Skeleton3DSynthesisSection.jsx` inside `run()`, after the first page is loaded and `completed` state is set.
- Calculates total page count from `adaptedPage.totalFrames`, then fetches pages 1..N in order, merging each into state via `mergeSkeleton3DPage` as they arrive.
- Uses `pageRequestsRef` to prevent duplicate requests with the existing on-demand loader.
- Per-page error handling removes the entry from `pageRequestsRef` without changing synthesis status, so on-demand fallback can retry if needed.
- Abort signal checked at loop entry and on `AbortError` catch to stop cleanly on unmount.

## fix: invert y-axis and add full-range pagination to rack motion viewer (#37)

- Fixed y-axis sign inversion in `backend/service/skeleton3d_to_rack_mapper.py`: panoptic_world_cm uses negative-y = up, rack_world uses positive-y = up. Changed `y = round(float(raw_y) * _CM_TO_M, 6)` to `y = round(-float(raw_y) * _CM_TO_M, 6)`. Symptom was person skeleton rendered below rack floor instead of at J-cup height.
- Fixed test fixture in `backend/tests/test_rack_motion_repository.py` `_make_skeleton3d_joint`: changed `y: 145.0` to `y: -145.0` so the fixture reflects correct panoptic convention (negative y = 145 cm above ground). Expected rack_world y ≈ +1.45 m assertion unchanged.
- Added full pagination to `frontend/src/components/sections/RackMotionStage1Section/RackMotionStage1Section.jsx`: replaced single fetch with sequential page loop using `framePage.page.nextStartFrame`. Frames accumulate in new `allFrames` state and the slider range now covers all frames in the synthesis result instead of the first page only (was: 120 frames visible out of ~3599 total).

## fix: synthesis completion stuck in queued state (#37)

- Fixed `frontend/src/components/sections/Skeleton3DSynthesisSection/Skeleton3DSynthesisSection.jsx`: replaced `synthesisState.key` in the synthesis `useEffect` dependency array with `synthesisKeyRef = useRef(null)`. The stale-closure on `key` caused the deduplication guard to re-trigger after state updates, preventing the effect from running to completion and leaving status stuck at `queued`.

## feat: add rack motion artifact contracts (#37)

- Added rack-tracker-owned adoption notes for the first rack motion pipeline implementation slice.
- Added `backend/schema/rack_motion.py` with rack motion observation, reconstruction, rack anchor, support zone, barbell, frame, and quality metric contracts.
- Added synthetic schema validation coverage for source-image observations, multi-camera reconstruction requirements, single-camera estimate downgrading, rack support-zone anchors, and barbell endpoints.
- Verified the new #37 files do not contain direct investigated-project names, direct copyleft-license names, or translation-source metadata references.

## docs: sync rack motion adoption review decisions (#37)

- Synchronized the #37 requirements adoption review documents with the `06-open-questions.md` user decisions.
- Updated camera/sync, canonical unit, rack alignment, target namespace, barbell endpoint, frontend scope, diagnostic visibility, and schema migration decisions across the review set.
- Clarified that public rack motion 3D coordinates use meter as the canonical stored unit while frontend/report display units remain metric-specific.

## feat: connect skeleton3d to rack motion viewer and complete stage1 scope (#37)

- Added `backend/service/skeleton3d_to_rack_mapper.py`: converts `skeleton3d.v1` joints to `ReconstructionTarget3D` with curated `person.*` namespace, `panoptic_world_cm` → `meter` conversion, and `identity_assumed` capture-to-rack quality metrics.
- Extended `backend/service/rack_motion_repository.py` with `get_stage1_fixture_from_skeleton3d()`: builds `RackMotionViewerFixture` from real synthesis data using the dev alignment fixture.
- Added `GET /rack-motion/from-synthesis/{synthesis_job_id}/stage1` endpoint to `backend/controller/rack_motion.py`.
- Extended `backend/tests/test_rack_motion_repository.py` with 4 new tests covering the skeleton3d path, cm-to-meter conversion, invalid joint inclusion, and pagination.
- Updated `Skeleton3DSynthesisSection` to emit `onSynthesisJobIdChange` callback when synthesis completes.
- Updated `App.jsx` to lift synthesis job ID state and pass it to `RackMotionStage1Section`.
- Rewrote `RackMotionStage1Section.jsx`:
  - Uses synthesis data when `synthesisJobId` is available; falls back to synthetic fixture.
  - Added CSS2DRenderer dimension annotations in 3D viewport (width/height/depth/J-cup labels).
  - Added `not_computed` degraded placeholder with dashed rack outline and label.
  - Added view toggles (Rack Mesh / Skeleton checkboxes).
  - Added per-keypoint inspector list with x/y/z coordinates, unit, and space badge.
  - Improved space badge colors: rack_world (teal #00aaaa), capture_world (blue #2266dd), identity_assumed (orange), not_computed (gray-blue).
  - Added `dev_assumption` and `not_computed` banner distinction.
  - Added "from synthesis" source badge in status bar.
- Added `getRackMotionFromSynthesis` to `frontend/src/api/analysisClient.js`.

## feat: add rack motion session schema, repository, and stage1 viewer (#37)

- Extended `backend/schema/rack_motion.py` with session-level contracts: `RackMotionSessionManifest`, `RackMotionViewerFixture`, `RackMotionFramePage`, `RackMotionCoordinateSpaces`, `RackMotionSpaceSummary`, `RackMotionSourceRefs`, `RackDimensions`, `RackAlignmentSummary`.
- Added `backend/service/rack_motion_repository.py` with `RackMotionArtifactRepository` reading stage1 fixture JSON from `backend/fixtures/rack_motion/`.
- Added `backend/controller/rack_motion.py` with `GET /rack-motion/fixtures/stage1` endpoint.
- Added `backend/fixtures/rack_motion/virtual_power_rack_dev_alignment.json` as dev alignment fixture.
- Added `backend/tests/test_rack_motion_repository.py` covering fixture load and page slicing.
- Extended `backend/tests/test_rack_motion_schema.py` with `personKeypoints` namespace and validation tests.
- Wired rack motion router into `backend/app.py`; added localhost:5174 CORS origin.
- Added `frontend/src/components/sections/RackMotionStage1Section/` with `RackMotionStage1Section.jsx` and module CSS.
- Added `getRackMotionStage1Fixture` to `frontend/src/api/analysisClient.js`.
- Added `RackMotionStage1Section` to `frontend/src/App.jsx`.
- Added `scripts/check-requirements-doc-pairs.ps1` and wired into `.githooks/pre-commit` to enforce #32-#37 doc pair updates.
- Updated `rack-motion-adoption-design.md` with the sub-document management matrix.
