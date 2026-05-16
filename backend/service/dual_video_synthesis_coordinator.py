from __future__ import annotations

from collections import defaultdict

from schema.pose import AlignedPoseChunkPair, PoseChunk, PoseChunkStreamItem


class DualVideoSynthesisCoordinatorError(Exception):
    pass


class PendingChunkOverflowError(DualVideoSynthesisCoordinatorError):
    pass


class UnknownStreamError(DualVideoSynthesisCoordinatorError):
    pass


class DualVideoSynthesisCoordinator:
    """Pairs per-video PoseChunk units by chunk_index for later synthesis stages."""

    def __init__(
        self,
        *,
        primary_stream_id: str = "video_a",
        secondary_stream_id: str = "video_b",
        max_pending_chunks: int = 2,
    ) -> None:
        if primary_stream_id == secondary_stream_id:
            raise ValueError("primary_stream_id and secondary_stream_id must differ.")
        if max_pending_chunks < 1:
            raise ValueError("max_pending_chunks must be >= 1.")

        self._primary_stream_id = primary_stream_id
        self._secondary_stream_id = secondary_stream_id
        self._max_pending_chunks = max_pending_chunks
        self._pending: dict[str, dict[int, PoseChunk]] = defaultdict(dict)

    def ingest(self, stream_id: str, chunk: PoseChunk) -> AlignedPoseChunkPair | None:
        self._validate_stream_id(stream_id)

        counterpart_stream_id = self._secondary_stream_id if stream_id == self._primary_stream_id else self._primary_stream_id
        counterpart = self._pending[counterpart_stream_id].pop(chunk.chunk_index, None)
        if counterpart is not None:
            return self._build_pair(
                primary_chunk=chunk if stream_id == self._primary_stream_id else counterpart,
                secondary_chunk=counterpart if stream_id == self._primary_stream_id else chunk,
            )

        pending_for_stream = self._pending[stream_id]
        pending_for_stream[chunk.chunk_index] = chunk
        if len(pending_for_stream) > self._max_pending_chunks:
            oldest_chunk_index = min(pending_for_stream)
            raise PendingChunkOverflowError(
                f"Pending chunk window exceeded for {stream_id}: "
                f"chunk {oldest_chunk_index} is still waiting for its counterpart."
            )
        return None

    def flush_unpaired(self) -> dict[str, list[int]]:
        return {
            self._primary_stream_id: sorted(self._pending[self._primary_stream_id].keys()),
            self._secondary_stream_id: sorted(self._pending[self._secondary_stream_id].keys()),
        }

    def reset(self) -> None:
        self._pending.clear()

    def _build_pair(
        self,
        *,
        primary_chunk: PoseChunk,
        secondary_chunk: PoseChunk,
    ) -> AlignedPoseChunkPair:
        return AlignedPoseChunkPair(
            chunk_index=primary_chunk.chunk_index,
            primary=PoseChunkStreamItem(
                stream_id=self._primary_stream_id,
                chunk=primary_chunk,
            ),
            secondary=PoseChunkStreamItem(
                stream_id=self._secondary_stream_id,
                chunk=secondary_chunk,
            ),
        )

    def _validate_stream_id(self, stream_id: str) -> None:
        if stream_id not in {self._primary_stream_id, self._secondary_stream_id}:
            raise UnknownStreamError(f"Unknown stream_id '{stream_id}'.")
