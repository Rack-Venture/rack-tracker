"""
trim_hd_videos.py
-----------------
hdVideos/ 내 6개 HD 영상(hd_00_00 ~ hd_00_05)을 시작부터 2분 00초 지점까지
무손실 트리밍하여 hdVideos_2min/ 폴더에 저장한다.

Usage:
    python trim_hd_videos.py

Output:
    171204_pose1/hdVideos_2min/hd_00_00_2min.mp4  ~ hd_00_05_2min.mp4
    171204_pose1/hdVideos_2min/metadata.json
"""

import json
import os
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
TRIM_DURATION = 120  # 2분 = 120초

SRC_DIR = Path(__file__).parent / "hdVideos"
OUT_DIR = Path(__file__).parent / "hdVideos_2min"

VIDEO_NAMES = [
    "hd_00_00",
    "hd_00_01",
    "hd_00_02",
    "hd_00_03",
    "hd_00_04",
    "hd_00_05",
]


def get_video_duration(path: Path) -> float:
    """ffmpeg stderr 파싱으로 영상 길이(초) 추출."""
    cmd = [FFMPEG, "-i", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # "Duration: HH:MM:SS.ms" 형식에서 파싱
    for line in result.stderr.splitlines():
        if "Duration" in line:
            parts = line.strip().split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def trim_video(src: Path, dst: Path, duration: int) -> None:
    """ffmpeg copy 코덱으로 무손실 트리밍."""
    cmd = [
        FFMPEG,
        "-y",
        "-i", str(src),
        "-t", str(duration),
        "-c", "copy",
        str(dst),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main():
    OUT_DIR.mkdir(exist_ok=True)

    metadata = {
        "description": "CMU Panoptic Studio 171204_pose1 HD 영상 2분 트리밍 클립",
        "source_dir": "hdVideos",
        "output_dir": "hdVideos_2min",
        "trim_duration_sec": TRIM_DURATION,
        "trim_duration_hms": "00:02:00",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ffmpeg_version": imageio_ffmpeg.get_ffmpeg_version(),
        "clips": [],
    }

    for name in VIDEO_NAMES:
        src = SRC_DIR / f"{name}.mp4"
        dst = OUT_DIR / f"{name}_2min.mp4"

        if not src.exists():
            print(f"[SKIP] {src.name} not found")
            continue

        src_duration = get_video_duration(src)
        print(f"[TRIM] {src.name} (원본 {src_duration:.1f}s) -> {dst.name} ...", end=" ", flush=True)
        t0 = time.time()
        trim_video(src, dst, TRIM_DURATION)
        elapsed = time.time() - t0
        print(f"done ({elapsed:.1f}s)")

        # 출력 파일 정보
        clip_entry = {
            "name": dst.name,
            "source": src.name,
            "source_duration_sec": round(src_duration, 2),
            "trimmed_duration_sec": TRIM_DURATION,
            "size_bytes": dst.stat().st_size,
            "size_mb": round(dst.stat().st_size / (1024 ** 2), 1),
        }
        metadata["clips"].append(clip_entry)

    # metadata.json 저장
    meta_path = OUT_DIR / "metadata.json"
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DONE] metadata.json saved -> {meta_path}")
    print(f"[DONE] {len(metadata['clips'])} clips created in {OUT_DIR}")


if __name__ == "__main__":
    main()
