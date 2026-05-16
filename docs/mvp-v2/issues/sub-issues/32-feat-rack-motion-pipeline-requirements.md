# [feat] Define Rack Motion Pipeline Clean-Room Requirements
Parent: #25
GitHub: #32

## Document Relations
- This document tracks one issue-sized work item.
- Keep this file name aligned with the issue branch name.
- Place detailed design notes under `32-feat-rack-motion-pipeline-requirements/`.
- Update this document before each related commit.

## Summary
Define a rack-tracker-owned requirements baseline for rack-centered motion analysis. The immediate deliverable is a safe requirements document that converts user-authored clean-room research notes into rack-tracker terminology without importing external project code, implementation structure, sample data, generated artifacts, tests, or expressive documentation text.

## Goal
- Create a requirements document that future implementers can use without inspecting the investigated source project.
- Define the expected processing stages for camera input, synchronization, 2D observations, calibration, 3D reconstruction, rack alignment, temporal processing, and rack-domain analysis.
- Define entity expectations for rack anchors, barbell endpoints, lifter keypoints, and rack interaction events.
- Record clean-room constraints so implementation work stays independent and license risk remains visible.

## Scope
- Requirements and design constraints only.
- Coordinate-space and artifact expectations for rack-tracker-owned schemas.
- Quality, diagnostics, and acceptance criteria for future implementation tasks.
- Open decisions that require product or engineering judgment before implementation.

## Out Of Scope
- Pipeline implementation.
- Importing or adapting externally licensed source code.
- Copying source-project module layout, class names, function names, schema names, comments, log messages, tests, sample data, generated artifacts, or default thresholds.
- Choosing the final rack-tracker license.

## Source-Handling Rules
- User-authored clean-room output documents may be used as research input for this issue.
- Do not copy those notes verbatim into product documentation when they preserve external source-project expression, structure, naming, defaults, or implementation sequence.
- Convert any useful idea into rack-tracker-owned requirements, acceptance criteria, open decisions, or validation needs.
- If a note cannot be separated from external implementation detail, leave it out of the requirements baseline and track it as an open legal or engineering question instead.

## Deliverables
| ID | Document | Status | Purpose |
| --- | --- | --- | --- |
| REQ-01 | `32-feat-rack-motion-pipeline-requirements/README.md` | Drafted | Explain how to read the sub-issue folder. |
| REQ-02 | `32-feat-rack-motion-pipeline-requirements/rack-motion-pipeline-requirements.md` | Drafted | Define the clean-room rack motion pipeline requirements. |

## Done Criteria
- GitHub issue #32 exists in `rack-labs/rack-tracker`.
- The local issue document references #32 and parent #25.
- The detailed requirements document is written in rack-tracker terminology.
- The detailed requirements document contains clean-room boundaries, pipeline stages, coordinate-space rules, artifact contracts, quality requirements, and acceptance criteria.
- No external source-project code, file layout, naming scheme, test wording, generated artifact, or sample data is copied into rack-tracker.
- User-authored clean-room output is represented only as rack-tracker requirements or decisions, not as copied source-project expression.

## Work Log

### 2026-05-06 - Issue and requirements draft
- Created upstream GitHub issue #32.
- Added this local management document.
- Added a child folder with the rack motion pipeline requirements draft.

## docs: add clean-room Korean research notes (#32)

- Copied the user-authored Korean clean-room research notes into the #32 sub-issue folder.
- Removed translation-sync metadata and direct investigated-project license naming from the copied notes.
- Verified the #32 documents do not contain direct investigated-project names, direct copyleft-license names, or translation-source metadata references.
