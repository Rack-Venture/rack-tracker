# Rack Motion Pipeline Clean-Room Requirements

## Purpose
Define the rack-tracker motion pipeline as an independent set of requirements for rack-centered barbell and lifter analysis. This document is implementation input, not an implementation plan. It should let contributors build rack-tracker-owned code without consulting the investigated source project.

## Clean-Room Rules
- Write new rack-tracker code from these requirements and public domain knowledge of camera geometry, calibration, triangulation, and time-series processing.
- Use rack-tracker naming, folder structure, public APIs, schemas, fixtures, tests, error messages, and logs.
- Do not copy external project source code, module boundaries, function signatures, class structure, comments, log text, tests, sample data, generated artifacts, calibration file shape, or threshold values.
- Do not treat this document as permission to import externally licensed implementation material.
- Keep PR descriptions explicit: the implementation is based on rack-tracker requirements and standard computer vision techniques, with no copied external source.

## Research Input Handling
User-authored clean-room output documents may inform this requirements baseline. They are acceptable input when they summarize observations, tradeoffs, and product implications in the user's own words. Before content reaches implementation, convert those notes into rack-tracker-owned requirements and avoid carrying over external source-project expression, naming, configuration shape, thresholds, or implementation order.

If a research note depends on a specific external implementation detail, record the need as an open decision or validation requirement instead of copying the detail.

## Product Boundary
The first useful version should answer rack-domain questions:

- Where is the barbell in rack-centered 3D coordinates?
- How do the left and right bar endpoints move over time?
- Is the bar near the J-cups, safety pins, or uprights?
- Is the lifter position good enough to contextualize bar motion?
- Which frames are reliable, degraded, or unusable?

The vision core should not own marketing UI, notebook generation, external 3D application export, or dataset publication.

## Pipeline Requirements
| Stage | Required Responsibility | Required Output |
| --- | --- | --- |
| Session setup | Bind input videos, cameras, processing options, target definitions, and output locations to stable ids. | Session manifest with schema version, camera ids, target ids, selected policies, and artifact paths. |
| Media probing | Inspect each source without changing the source files. | Camera/media inventory with image size, frame count, FPS estimate, timestamp availability, and warnings. |
| Frame alignment | Map camera-local frames into shared analysis time. | Frame groups, offset metadata, dropped-frame notes, and sync warnings. |
| Image preparation | Produce detector input images while preserving a reversible mapping to source pixels. | Transform metadata for resize, crop, padding, rotation, and distortion policy. |
| 2D observation | Convert detector output into rack-tracker target observations. | Per-camera, per-frame 2D points in original image pixels with confidence and status. |
| Calibration | Describe camera intrinsics, distortion, extrinsics, units, and capture-world convention. | Calibration bundle with quality metrics and declared transform direction. |
| 3D reconstruction | Estimate 3D targets from synchronized multi-camera 2D observations. | Raw 3D points, used camera ids, reprojection error, reconstruction status, and failure reasons. |
| Rack alignment | Map raw capture coordinates into rack-centered analysis coordinates. | Rack-world transform, rack anchors, rack dimensions, floor/vertical convention, and alignment quality. |
| Entity assembly | Build domain entities from reconstructed targets. | Lifter, barbell, and rack entities with ids, target points, quality, and provenance. |
| Temporal processing | Smooth, interpolate, or segment only under declared policy. | Processed trajectories with links to raw frames and explicit interpolation spans. |
| Rack analysis | Compute rack-specific metrics and candidate events. | Bar path, endpoint asymmetry, rack proximity, support-contact candidates, and analysis quality report. |

## Coordinate Spaces
Every persisted coordinate must declare its space, unit, axes, and provenance.

| Space | Requirement |
| --- | --- |
| Source image pixels | Store 2D observations in decoded source-image pixel coordinates after reversing detector preprocessing. |
| Detector input pixels | Treat model input coordinates as adapter-private unless explicitly needed for diagnostics. |
| Camera space | Use only with a declared camera id, intrinsics, distortion model, and transform to the shared reconstruction space. |
| Capture world | Use as the raw calibrated 3D reconstruction space when calibration is not directly rack-relative. |
| Rack world | Use as the analysis space for bar path, rack proximity, height, depth, support zones, and rendered metric output. |

Rack world must be defined from rack measurements, rack anchors, floor/vertical references, or approved manual alignment. Lifter skeleton motion must not define the rack origin, floor plane, vertical axis, or camera pose.

## Core Data Contracts
### 2D Observations
2D observations should support dense batch processing and sparse streaming records. Required fields are:

- session id
- camera id
- frame index and timestamp when available
- target id
- coordinate space and image size
- x/y pixel coordinates or missing value
- confidence normalized by the adapter
- observation status and status reason
- preprocessing transform id when preprocessing was applied

### Calibration Bundle
The calibration bundle should be a rack-tracker schema. Required fields are:

- calibration id
- camera ids covered by the bundle
- camera intrinsics and image size
- distortion model and coefficients
- camera pose transform with direction declared
- length unit
- capture-world origin and axis convention
- calibration target summary
- quality report

Rack dimensions and rack anchors should live in rack config or rack-alignment artifacts, not be hidden inside camera calibration.

### 3D Reconstruction
3D reconstruction outputs must include:

- frame index
- target id
- x/y/z in the declared 3D space
- quality
- reconstruction mode
- calibration id
- used camera ids or mask
- per-camera and aggregate reprojection error
- observation reconstruction status
- failure reason for invalid targets

Single-camera estimates must use a different reconstruction mode from calibrated multi-camera 3D and must not be presented as equivalent quality.

### Rack Entities
Rack-tracker should keep rack, barbell, and lifter data separate even if one detector produces multiple categories.

Required entity groups:

- rack anchors and support zones
- barbell left endpoint, right endpoint, derived center, and derived bar axis
- lifter keypoints needed for selected lift analysis
- derived events and metric summaries

Endpoint side labels must be defined in rack-world terms, not image left/right.

## Reconstruction Requirements
The first multi-camera implementation may use standard weighted homogeneous least-squares triangulation or an equivalent well-understood method.

Minimum requirements:

- Use only finite 2D observations that pass the active confidence policy.
- Require the configured minimum number of retained cameras.
- Build projection geometry from the active calibration bundle.
- Compute 3D points in the declared reconstruction space.
- Reproject each accepted 3D point back to each retained camera.
- Record per-camera reprojection error.
- Mark outlier observations by rack-tracker policy.
- Preserve raw observations so rejected points remain auditable.

Thresholds, weighting formulas, and outlier policies must be chosen from rack-tracker validation data, synthetic fixtures, or separately licensed recordings.

## Quality Requirements
Quality metrics must travel with artifacts and not exist only in console output.

Required quality categories:

- detector confidence and visibility
- sync warnings
- calibration quality
- used camera count
- reprojection error
- dropped or rejected observations
- rack alignment quality
- interpolation spans
- final analysis quality

Every thresholded quality decision should record a policy id. A missing target, a high-error target, and an intentionally interpolated target are different states and must remain distinguishable.

## Rack Analysis Requirements
Initial rack-domain analysis should support:

- bar center path in rack-world coordinates
- left/right endpoint height difference
- bar depth relative to rack support features
- proximity to J-cups and safety pins
- candidate unrack and rerack frame ranges
- candidate safety-pin contact frame ranges
- quality downgrades when rack anchors, bar endpoints, sync, or reconstruction are weak

Events should be candidate events until the policy has enough geometric and temporal evidence to promote them.

## Validation Requirements
Future implementation work should include rack-tracker-owned tests and fixtures:

- synthetic calibrated cameras projecting known 3D points into 2D and reconstructing them within declared tolerance
- low-confidence noisy observations having less effect than high-confidence observations
- too-few-view targets producing stable failure reasons
- high-reprojection observations being retained for audit but excluded by policy when appropriate
- rack-world transform preserving known rack dimensions and support-zone positions
- single-camera outputs being clearly labeled as estimates
- interpolation spans remaining visible in exported artifacts

Do not use external project generated artifacts, tests, or sample datasets as rack-tracker fixtures unless separately cleared and attributed under compatible terms.

## Open Decisions
- Target rack-tracker license and distribution model.
- First supported camera setup: single-camera preview, two-camera reconstruction, or both.
- Canonical rack-world origin, axes, and unit.
- Calibration target and capture procedure.
- Rack anchor input method: manual measurement, detector output, calibration target, or imported config.
- Barbell endpoint detector strategy and identity tracking policy.
- Minimum camera count and reprojection thresholds for each analysis metric.
- Which lifter keypoints are required for squat, bench, deadlift, overhead press, and rack-only checks.
- Which diagnostics should be user-facing in the first MVP.
