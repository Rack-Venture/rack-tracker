"""
prepare_gt_aligned_clips.py
---------------------------
1. hdVideos_2min/ 의 6개 클립에서 앞 118 프레임(~3.94초)을 제거해 GT 동기화 클립으로 재생성
2. hdPose3d_stage1_coco19.tar 에서 해당 프레임(118~3596) 범위의 GT JSON만 추출

Usage:
    python prepare_gt_aligned_clips.py

Output:
    hdVideos_gt_aligned/hd_00_00_gt.mp4  ~ hd_00_05_gt.mp4   (무손실 트리밍)
    hdPose3d_2min/body3DScene_00000118.json ~ body3DScene_00003596.json
    hdVideos_gt_aligned/metadata.json
"""

import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

import imageio_ffmpeg

# ── 상수 ─────────────────────────────────────────────────────────────
FFMPEG       = imageio_ffmpeg.get_ffmpeg_exe()
FPS          = 29.97
START_FRAME  = 118                        # GT가 시작하는 비디오 프레임
END_FRAME    = int(120.0 * FPS)           # 2분 = 프레임 3596
START_SEC    = START_FRAME / FPS          # ~3.937초
DURATION_SEC = 120.0 - START_SEC          # ~116.063초

BASE_DIR   = Path(__file__).parent
SRC_DIR    = BASE_DIR / "hdVideos_2min"
OUT_DIR    = BASE_DIR / "hdVideos_gt_aligned"
GT_TAR     = BASE_DIR / "hdPose3d_stage1_coco19.tar"
GT_OUT_DIR = BASE_DIR / "hdPose3d_2min"

VIDEO_NAMES = [f"hd_00_0{i}" for i in range(6)]


# ── 1. 비디오 트리밍 ───────────────────────────────────────────────────
def trim_video(src: Path, dst: Path) -> None:
    """ffmpeg copy 코덱으로 START_SEC ~ END 무손실 트리밍."""
    cmd = [
        FFMPEG, "-y",
        "-ss", f"{START_SEC:.6f}",
        "-i", str(src),
        "-t", f"{DURATION_SEC:.6f}",
        "-c", "copy",
        str(dst),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def trim_all_videos() -> list[dict]:
    OUT_DIR.mkdir(exist_ok=True)
    clips = []
    for name in VIDEO_NAMES:
        src = SRC_DIR / f"{name}_2min.mp4"
        dst = OUT_DIR / f"{name}_gt.mp4"
        if not src.exists():
            print(f"[SKIP] {src.name} not found")
            continue
        print(f"[TRIM] {src.name} -> {dst.name} ...", end=" ", flush=True)
        t0 = time.time()
        trim_video(src, dst)
        print(f"done ({time.time()-t0:.1f}s)  {dst.stat().st_size/(1024**2):.1f} MB")
        clips.append({
            "name": dst.name,
            "source": src.name,
            "start_frame": START_FRAME,
            "end_frame": END_FRAME,
            "start_sec": round(START_SEC, 6),
            "duration_sec": round(DURATION_SEC, 6),
            "size_bytes": dst.stat().st_size,
            "size_mb": round(dst.stat().st_size / (1024**2), 1),
        })
    return clips


# ── 2. GT 추출 ─────────────────────────────────────────────────────────
def extract_gt() -> dict:
    GT_OUT_DIR.mkdir(exist_ok=True)
    target_names = {
        f"hdPose3d_stage1_coco19/body3DScene_{n:08d}.json"
        for n in range(START_FRAME, END_FRAME + 1)
    }
    extracted, skipped = 0, 0
    print(f"\n[GT] tar 열기: {GT_TAR.name}")
    with tarfile.open(GT_TAR) as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}
        total = len(target_names)
        for i, tname in enumerate(sorted(target_names), 1):
            if i % 500 == 0 or i == total:
                print(f"  진행: {i}/{total}", end="\r", flush=True)
            if tname not in members:
                skipped += 1
                continue
            member = members[tname]
            fname = Path(tname).name
            dst_path = GT_OUT_DIR / fname
            with tf.extractfile(member) as src_f, open(dst_path, "wb") as dst_f:
                dst_f.write(src_f.read())
            extracted += 1
    print(f"\n[GT] 추출 완료: {extracted}개  누락: {skipped}개")
    return {
        "source_tar": GT_TAR.name,
        "output_dir": str(GT_OUT_DIR.name),
        "frame_range": [START_FRAME, END_FRAME],
        "extracted": extracted,
        "skipped": skipped,
    }


# ── 3. metadata.json ───────────────────────────────────────────────────
def save_metadata(clips: list[dict], gt_info: dict) -> None:
    meta = {
        "description": "GT 동기화 클립 — 앞 118 프레임 제거, GT 범위(118~3596)와 1:1 대응",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ffmpeg_version": imageio_ffmpeg.get_ffmpeg_version(),
        "alignment": {
            "fps": FPS,
            "cut_frames": START_FRAME,
            "cut_sec": round(START_SEC, 6),
            "clip_start_frame": START_FRAME,
            "clip_end_frame": END_FRAME,
            "clip_duration_sec": round(DURATION_SEC, 6),
        },
        "gt": gt_info,
        "clips": clips,
    }
    path = OUT_DIR / "metadata.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[DONE] metadata.json -> {path}")


# ── main ───────────────────────────────────────────────────────────────
def main():
    print("=== 1/2  비디오 트리밍 ===")
    clips = trim_all_videos()

    print("\n=== 2/2  GT 추출 ===")
    gt_info = extract_gt()

    save_metadata(clips, gt_info)
    print("[DONE] 완료")


if __name__ == "__main__":
    main()
