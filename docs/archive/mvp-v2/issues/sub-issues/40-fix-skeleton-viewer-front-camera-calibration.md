# [fix] skeleton 3D viewer front camera: use calibration midpoint
Parent: #29
GitHub: #40

## Document Relations
- This document tracks the post-#29 viewer camera direction fix.
- Deferred from PLAN-08 (viewer-floor-fix-plan.md) visual regression scope.
- Keep this file name aligned with the issue branch name.

## Problem

The Front preset in `ThreeJSSkeleton.jsx` is hardcoded to `camera.position.set(0, 0.4, 3.6)`, which looks from the world +Z direction.
In `panoptic_world_cm`, the two capture cameras are not aligned with world +Z, so the skeleton appears rotated ~45° in the front view.

Ground and up axis are correct (`viewHint.upAxis=y`, `upAxisDirection=negative`, `groundPlaneValue=0`). Only the horizontal view direction is wrong.

## Fix Direction

- **Backend** (`skeleton_3d_synthesizer.py`): compute the world-space midpoint of the two camera centers (from `-R^T t`), add `frontView.cameraMidpointXZ` and `frontView.eyeHeightWorld` to `synthesisInfo.viewHint`.
- **Frontend** (`ThreeJSSkeleton.jsx`): when `viewHint.frontView.cameraMidpointXZ` is present, compute the unit direction from camera midpoint toward the subject center (render-space origin), position camera at that direction × viewing distance. Side = front rotated 90° around Y. Fallback to current preset if hint is absent.

## Design Constraints

- Ground and vertical axis continue to come from `viewHint.upAxis` and `groundPlaneValue` only — never estimated from joints.
- Camera midpoint is derived from calibration data, not from joint positions.
- Eye height defaults to `eyeHeightWorld = -150.0` (150 cm above ground in `panoptic_world_cm`).
- Front/side camera distance in render space is kept at current viewing distance (~3.6 render units).

## Work Log

## fix: use calibration midpoint for skeleton 3D viewer front camera (#40)

- Added `_front_view_hint` helper to `Skeleton3DSynthesizer.synthesize`; computes camera center midpoint from `-R^T t` for both cameras and emits `synthesisInfo.viewHint.frontView = { cameraMidpointXZ, eyeHeightWorld: -150.0 }`.
- Added `applyCameraPreset` function in `ThreeJSSkeleton.jsx`; when `viewHint.frontView.cameraMidpointXZ` is present, derives the unit direction from midpoint to subject (render-space origin) and positions camera at that direction × viewing distance. Side view is front rotated 90° around Y.
- Added `metricViewFrameRef` and `frontViewHintRef` to persist calibration hint across effects; first frame with a valid hint auto-orients the front camera.
- Replaced hardcoded `3.6` with `CAMERA_VIEW_DISTANCE` constant.
- Added `frontView` assertions to `test_skeleton_3d_synthesizer.py`; both tests pass.
