from service.frame_alignment import FrameAlignmentService


def test_align_pairs_frames_by_timestamp_with_delta_bound() -> None:
    primary = [
        {"frameIndex": 0, "timestampMs": 0.0},
        {"frameIndex": 1, "timestampMs": 33.3},
        {"frameIndex": 2, "timestampMs": 66.6},
    ]
    secondary = [
        {"frameIndex": 0, "timestampMs": 1.0},
        {"frameIndex": 1, "timestampMs": 34.0},
        {"frameIndex": 2, "timestampMs": 101.0},
    ]

    pairs, summary = FrameAlignmentService().align(primary, secondary, max_delta_ms=5.0)

    assert len(pairs) == 2
    assert pairs[0].primary_frame["frameIndex"] == 0
    assert pairs[1].primary_frame["frameIndex"] == 1
    assert summary["unmatchedPrimaryFrameCount"] == 1
    assert summary["unmatchedSecondaryFrameCount"] == 1
