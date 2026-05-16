---
issue: 49
title: "[FIX] Fix keypointList height causing rack motion viewer to resize per frame"
branch: 49-fix-keypointlist-height
type: fix
status: in-progress
---

# Issue #49 — Fix keypointList height

## Problem

`.keypointList`가 `max-height`를 사용하므로 프레임마다 keypoint 개수가 달라질 때 컨테이너 높이가 변동되고, rack motion viewer 전체 높이가 흔들린다.

## Solution

`max-height: 28rem` → `height: 280px`로 고정하여 viewer 전체 높이를 안정적으로 유지.

## Work Log

## fix: fix keypointList height to 280px to prevent viewer resize per frame (#49)

- `RackMotionStage1Section.module.css` `.keypointList`: `max-height: 28rem` → `height: 280px`

## docs: add MVP v2 pipeline overview document

- `docs/mvp-v2/OVERVIEW.md` 신규 작성 — 이슈 관계도, 시스템 레이어 아키텍처, 합성 파이프라인 흐름, 좌표 공간 정의, API 엔드포인트 등 MVP v2 전체 설계 개요 문서
