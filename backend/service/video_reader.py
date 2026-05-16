from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from adapter.opencv_adapter import (
    FrameReadError,
    OpenCvAdapter,
)
from schema.frame import ExtractedFrame, FrameChunk, FrameExtractionOptions, FrameExtractionResult


class InvalidSamplingOptionError(ValueError):
    pass


class VideoReaderService:
    def __init__(self, adapter: OpenCvAdapter | None = None) -> None:
        self._default_adapter = adapter

    def extract_frames(self, options: FrameExtractionOptions) -> FrameExtractionResult:
        last_metadata: dict = {}
        frames = list(self.iter_frames(options, _out_metadata=last_metadata))
        result = FrameExtractionResult(
            source_path=options.video_path,
            backend=str(last_metadata.get("backend", "unknown")),
            source_fps=self._normalize_source_fps(float(last_metadata.get("fps", 0.0))),
            frame_count=int(last_metadata["frame_count"]) if last_metadata.get("frame_count") else None,
            width=int(last_metadata["width"]) if last_metadata.get("width") else None,
            height=int(last_metadata["height"]) if last_metadata.get("height") else None,
            extracted_count=len(frames),
            frames=frames,
        )
        return result

    def iter_frame_chunks(
        self,
        options: FrameExtractionOptions,
        *,
        chunk_size: int = 32,
        _out_metadata: dict | None = None,
    ) -> Iterator[FrameChunk]:
        if chunk_size < 1:
            raise InvalidSamplingOptionError("chunk_size must be >= 1.")

        chunk_frames: list[ExtractedFrame] = []
        metadata: dict = {}
        chunk_index = 0
        for frame in self.iter_frames(options, _out_metadata=metadata):
            chunk_frames.append(frame)
            if len(chunk_frames) < chunk_size:
                continue
            if _out_metadata is not None and metadata:
                _out_metadata.update(metadata)
            yield FrameChunk(
                chunk_index=chunk_index,
                start_frame_index=chunk_frames[0].index,
                end_frame_index=chunk_frames[-1].index,
                video_info=dict(metadata) if metadata else None,
                frames=chunk_frames,
            )
            chunk_index += 1
            chunk_frames = []

        if _out_metadata is not None and metadata:
            _out_metadata.update(metadata)
        if chunk_frames:
            yield FrameChunk(
                chunk_index=chunk_index,
                start_frame_index=chunk_frames[0].index,
                end_frame_index=chunk_frames[-1].index,
                video_info=dict(metadata) if metadata else None,
                frames=chunk_frames,
            )

    def iter_frames(self, options: FrameExtractionOptions, *, _out_metadata: dict | None = None) -> Iterator[ExtractedFrame]:
        adapter = self._default_adapter if self._default_adapter is not None else OpenCvAdapter()
        self._validate_options(options)
        adapter.open_video(str(options.video_path))
        metadata = adapter.get_metadata()
        if _out_metadata is not None:
            _out_metadata.update(metadata)
        source_fps = self._normalize_source_fps(float(metadata["fps"]))
        backend = str(metadata["backend"])
        if options.sampling_mode == "target_fps":
            options.target_fps = self._resolve_target_fps(options.target_fps, source_fps)

        next_target_ms = float(options.start_ms or 0.0)
        frame_index = 0
        emitted_count = 0

        try:
            while True:
                ok, frame = adapter.read_frame()
                if not ok:
                    if frame_index == 0:
                        raise FrameReadError("Failed to read the first frame.")
                    break

                timestamp_ms = (
                    frame_index * 1000.0 / source_fps if source_fps > 0 else float(frame_index)
                )

                if options.end_ms is not None and timestamp_ms > float(options.end_ms):
                    break

                should_emit, next_target_ms = self._should_emit_frame(
                    frame_index=frame_index,
                    timestamp_ms=timestamp_ms,
                    source_fps=source_fps,
                    options=options,
                    next_target_ms=next_target_ms,
                )

                if should_emit:
                    if options.convert_bgr_to_rgb:
                        frame = adapter.convert_bgr_to_rgb(frame)

                    saved_path = None
                    if options.save_images and options.output_dir is not None:
                        output_path = self._build_output_path(
                            output_dir=options.output_dir,
                            frame_index=frame_index,
                            timestamp_ms=timestamp_ms,
                            image_extension=options.image_extension,
                        )
                        saved_path = adapter.write_frame(
                            frame=frame,
                            output_path=output_path,
                            image_extension=options.image_extension,
                            jpeg_quality=options.jpeg_quality,
                        )

                    height, width = frame.shape[:2]
                    yield ExtractedFrame(
                        index=frame_index,
                        timestamp_ms=timestamp_ms,
                        timestamp_sec=timestamp_ms / 1000.0,
                        backend=backend,
                        width=width,
                        height=height,
                        image=frame,
                        saved_path=saved_path,
                    )
                    emitted_count += 1

                frame_index += 1
        finally:
            adapter.close()

    def probe_metadata(self, video_path: Path) -> dict[str, Any]:
        adapter = self._default_adapter if self._default_adapter is not None else OpenCvAdapter()
        adapter.open_video(str(video_path))
        try:
            return adapter.get_metadata()
        finally:
            adapter.close()

    def read_frames(self, video_path: str, target_fps: float) -> list[dict]:
        options = FrameExtractionOptions(
            video_path=Path(video_path),
            sampling_mode="target_fps",
            target_fps=target_fps,
        )
        result = self.extract_frames(options)
        return [
            {
                "index": frame.index,
                "timestampMs": frame.timestamp_ms,
                "timestampSec": frame.timestamp_sec,
                "backend": frame.backend,
                "width": frame.width,
                "height": frame.height,
                "image": frame.image,
                "savedPath": str(frame.saved_path) if frame.saved_path else None,
            }
            for frame in result.frames
        ]

    def _validate_options(self, options: FrameExtractionOptions) -> None:
        if not options.video_path.exists():
            raise FileNotFoundError(f"Video source not found: {options.video_path}")
        if options.sampling_mode == "every_n_frames":
            if options.every_n_frames is None or options.every_n_frames < 1:
                raise InvalidSamplingOptionError("every_n_frames must be >= 1.")
        if options.sampling_mode == "target_fps":
            if options.target_fps is not None and options.target_fps <= 0:
                raise InvalidSamplingOptionError("target_fps must be > 0.")
        if options.start_ms is not None and options.start_ms < 0:
            raise InvalidSamplingOptionError("start_ms must be >= 0.")
        if options.end_ms is not None and options.start_ms is not None:
            if options.end_ms < options.start_ms:
                raise InvalidSamplingOptionError("end_ms must be >= start_ms.")

    def _should_emit_frame(
        self,
        frame_index: int,
        timestamp_ms: float,
        source_fps: float,
        options: FrameExtractionOptions,
        next_target_ms: float,
    ) -> tuple[bool, float]:
        if options.start_ms is not None and timestamp_ms < float(options.start_ms):
            return False, next_target_ms

        if options.sampling_mode == "all":
            return True, next_target_ms

        if options.sampling_mode == "every_n_frames":
            return frame_index % int(options.every_n_frames or 1) == 0, next_target_ms

        if options.sampling_mode == "time_range":
            return True, next_target_ms

        if options.sampling_mode == "target_fps":
            target_fps = float(options.target_fps or source_fps or 1.0)
            interval_ms = 1000.0 / max(target_fps, 0.001)
            if timestamp_ms + 1e-6 >= next_target_ms:
                next_target_ms = max(next_target_ms + interval_ms, timestamp_ms + interval_ms)
                return True, next_target_ms
            return False, next_target_ms

        raise InvalidSamplingOptionError(f"Unsupported sampling mode: {options.sampling_mode}")

    def _build_output_path(
        self,
        output_dir: Path,
        frame_index: int,
        timestamp_ms: float,
        image_extension: str,
    ) -> Path:
        filename = f"frame_{frame_index:06d}_{int(round(timestamp_ms)):010d}.{image_extension}"
        return output_dir / filename

    def _normalize_source_fps(self, source_fps: float) -> float:
        return source_fps if source_fps > 0 else 30.0

    def _resolve_target_fps(self, requested_target_fps: float | None, source_fps: float) -> float:
        if requested_target_fps is None:
            return source_fps
        return min(float(requested_target_fps), source_fps)

