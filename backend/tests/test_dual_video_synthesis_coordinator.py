from schema.pose import PoseChunk
from service.dual_video_synthesis_coordinator import (
    DualVideoSynthesisCoordinator,
    PendingChunkOverflowError,
)


def _chunk(chunk_index: int, start_frame_index: int) -> PoseChunk:
    return PoseChunk(
        chunk_index=chunk_index,
        start_frame_index=start_frame_index,
        end_frame_index=start_frame_index + 31,
        frames=[],
    )


def test_ingest_pairs_matching_chunk_indexes() -> None:
    coordinator = DualVideoSynthesisCoordinator()

    assert coordinator.ingest("video_a", _chunk(0, 0)) is None
    pair = coordinator.ingest("video_b", _chunk(0, 0))

    assert pair is not None
    assert pair.chunk_index == 0
    assert pair.primary.stream_id == "video_a"
    assert pair.secondary.stream_id == "video_b"
    assert pair.primary.chunk.start_frame_index == 0
    assert pair.secondary.chunk.start_frame_index == 0


def test_ingest_handles_out_of_order_arrival() -> None:
    coordinator = DualVideoSynthesisCoordinator()

    assert coordinator.ingest("video_b", _chunk(3, 96)) is None
    pair = coordinator.ingest("video_a", _chunk(3, 96))

    assert pair is not None
    assert pair.chunk_index == 3
    assert pair.primary.chunk.start_frame_index == 96
    assert pair.secondary.chunk.start_frame_index == 96


def test_ingest_enforces_pending_chunk_bound() -> None:
    coordinator = DualVideoSynthesisCoordinator(max_pending_chunks=2)

    assert coordinator.ingest("video_a", _chunk(0, 0)) is None
    assert coordinator.ingest("video_a", _chunk(1, 32)) is None

    try:
        coordinator.ingest("video_a", _chunk(2, 64))
    except PendingChunkOverflowError as exc:
        assert "chunk 0" in str(exc)
    else:
        raise AssertionError("Expected PendingChunkOverflowError")


def test_flush_unpaired_reports_remaining_chunk_indexes() -> None:
    coordinator = DualVideoSynthesisCoordinator()

    assert coordinator.ingest("video_a", _chunk(1, 32)) is None
    assert coordinator.ingest("video_b", _chunk(4, 128)) is None

    assert coordinator.flush_unpaired() == {
        "video_a": [1],
        "video_b": [4],
    }
