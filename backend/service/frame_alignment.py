from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class FrameAlignmentError(Exception):
    pass


@dataclass(slots=True)
class AlignedFramePair:
    primary_frame: dict[str, Any]
    secondary_frame: dict[str, Any]
    timestamp_delta_ms: float
    primary_position: int
    secondary_position: int


class FrameAlignmentService:
    def align(
        self,
        primary_frames: list[dict[str, Any]],
        secondary_frames: list[dict[str, Any]],
        *,
        max_delta_ms: float,
    ) -> tuple[list[AlignedFramePair], dict[str, Any]]:
        if max_delta_ms <= 0:
            raise FrameAlignmentError("max_delta_ms must be > 0.")

        pairs: list[AlignedFramePair] = []
        unmatched_primary = 0
        unmatched_secondary = 0
        i = 0
        j = 0

        while i < len(primary_frames) and j < len(secondary_frames):
            primary_ts = self._timestamp(primary_frames[i], fallback_index=i)
            secondary_ts = self._timestamp(secondary_frames[j], fallback_index=j)
            delta = primary_ts - secondary_ts

            if abs(delta) <= max_delta_ms:
                pairs.append(
                    AlignedFramePair(
                        primary_frame=primary_frames[i],
                        secondary_frame=secondary_frames[j],
                        timestamp_delta_ms=abs(delta),
                        primary_position=i,
                        secondary_position=j,
                    )
                )
                i += 1
                j += 1
                continue

            if primary_ts < secondary_ts:
                unmatched_primary += 1
                i += 1
            else:
                unmatched_secondary += 1
                j += 1

        unmatched_primary += len(primary_frames) - i
        unmatched_secondary += len(secondary_frames) - j
        summary = {
            "pairedFrameCount": len(pairs),
            "unmatchedPrimaryFrameCount": unmatched_primary,
            "unmatchedSecondaryFrameCount": unmatched_secondary,
            "maxTimestampDeltaMs": max_delta_ms,
            "meanTimestampDeltaMs": self._mean([pair.timestamp_delta_ms for pair in pairs]),
        }
        return pairs, summary

    def resolve_max_delta_ms(
        self,
        requested_max_delta_ms: float | None,
        *,
        fps_a: float | None,
        fps_b: float | None,
    ) -> float:
        if requested_max_delta_ms is not None:
            return float(requested_max_delta_ms)
        fps_candidates = [fps for fps in (fps_a, fps_b) if fps is not None and fps > 0]
        fps = min(fps_candidates) if fps_candidates else 30.0
        return 1000.0 / fps / 2.0

    def _timestamp(self, frame: dict[str, Any], *, fallback_index: int) -> float:
        value = frame.get("timestampMs")
        if isinstance(value, int | float):
            return float(value)
        frame_index = frame.get("frameIndex")
        if isinstance(frame_index, int | float):
            return float(frame_index)
        return float(fallback_index)

    def _mean(self, values: list[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 3)
