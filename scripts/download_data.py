#!/usr/bin/env python3
"""
Download and place 171204_pose1 dataset files from Google Drive.

Setup (one-time):
  1. Create a folder in Google Drive and upload all dataset files flat (no subfolders).
  2. Share the folder: General access → "Anyone with the link".
  3. Copy the folder ID from the URL:
       https://drive.google.com/drive/folders/<FOLDER_ID>
  4. Paste that ID into DRIVE_FOLDER_ID below and commit.

Usage:
    pip install gdown
    python scripts/download_data.py           # download all missing files
    python scripts/download_data.py --force   # re-download even if file exists
    python scripts/download_data.py --list    # print manifest and exit

Archive preparation (run once on the machine that has the raw data):
    cd 171204_pose1
    tar -czf hdPose3d_stage1_perFrame_coco19.tar.gz hdPose3d_stage1_perFrame_coco19/
    tar -czf hdPose3d_stage1_all_coco19.tar.gz      hdPose3d_stage1_all_coco19/
    tar -czf hdPose3d_2min.tar.gz                   hdPose3d_2min/
    # Then upload those .tar.gz files (plus the other files below) to the Drive folder.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------
# ★ Fill in this single value after creating the shared Drive folder
# ---------------------------------------------------------------------------
DRIVE_FOLDER_ID = "1NI81pbAQcow2z4LR6UDB-n54O00n528D"
# ---------------------------------------------------------------------------

# Maps filename in the Drive folder → repo-relative destination path.
# 'extract': True  → treat the downloaded file as a tar/zip, extract it
#                    into the same directory, then delete the archive.
MANIFEST: list[dict] = [
    # ── Calibration ────────────────────────────────────────────────────────
    {
        "filename": "calibration_171204_pose1.json",
        "dest": "171204_pose1/calibration_171204_pose1.json",
        "description": "Camera calibration parameters (JSON, 252 KB)",
    },
    {
        "filename": "calibration_171204_pose1.toml",
        "dest": "171204_pose1/calibration_171204_pose1.toml",
        "description": "Camera calibration parameters (TOML, 1.2 KB)",
    },

    # ── 2-minute clips ─────────────────────────────────────────────────────
    {
        "filename": "hd_00_11_2min.mp4",
        "dest": "171204_pose1/hdVideos_2min/hd_00_11_2min.mp4",
        "description": "2-min clip -camera hd_00_11 (214 MB)",
    },
    {
        "filename": "hd_00_21_2min.mp4",
        "dest": "171204_pose1/hdVideos_2min/hd_00_21_2min.mp4",
        "description": "2-min clip -camera hd_00_21 (305 MB)",
    },

    # ── GT-aligned clips ───────────────────────────────────────────────────
    {
        "filename": "gt_skeleton_118_3596.json",
        "dest": "171204_pose1/hdVideos_gt_aligned/gt_skeleton_118_3596.json",
        "description": "GT skeleton JSON for aligned clips (2.6 MB)",
    },
    {
        "filename": "hd_00_00_gt.mp4",
        "dest": "171204_pose1/hdVideos_gt_aligned/hd_00_00_gt.mp4",
        "description": "GT-aligned clip -camera hd_00_00 (318 MB)",
    },
    {
        "filename": "hd_00_01_gt.mp4",
        "dest": "171204_pose1/hdVideos_gt_aligned/hd_00_01_gt.mp4",
        "description": "GT-aligned clip -camera hd_00_01 (318 MB)",
    },
    {
        "filename": "hd_00_02_gt.mp4",
        "dest": "171204_pose1/hdVideos_gt_aligned/hd_00_02_gt.mp4",
        "description": "GT-aligned clip -camera hd_00_02 (267 MB)",
    },
    {
        "filename": "hd_00_03_gt.mp4",
        "dest": "171204_pose1/hdVideos_gt_aligned/hd_00_03_gt.mp4",
        "description": "GT-aligned clip -camera hd_00_03 (317 MB)",
    },
    {
        "filename": "hd_00_04_gt.mp4",
        "dest": "171204_pose1/hdVideos_gt_aligned/hd_00_04_gt.mp4",
        "description": "GT-aligned clip -camera hd_00_04 (274 MB)",
    },
    {
        "filename": "hd_00_05_gt.mp4",
        "dest": "171204_pose1/hdVideos_gt_aligned/hd_00_05_gt.mp4",
        "description": "GT-aligned clip -camera hd_00_05 (332 MB)",
    },

    # ── Pose3D archives (extract after download) ───────────────────────────
    {
        "filename": "hdPose3d_stage1_perFrame_coco19.tar.gz",
        "dest": "171204_pose1/hdPose3d_stage1_perFrame_coco19.tar.gz",
        "description": "Per-frame Pose3D GT -27,561 JSON files (118 MB uncompressed)",
        "extract": True,
    },
    {
        "filename": "hdPose3d_stage1_all_coco19.tar.gz",
        "dest": "171204_pose1/hdPose3d_stage1_all_coco19.tar.gz",
        "description": "All-frames Pose3D JSONL (22 MB uncompressed)",
        "extract": True,
    },
    {
        "filename": "hdPose3d_2min.tar.gz",
        "dest": "171204_pose1/hdPose3d_2min.tar.gz",
        "description": "Per-frame Pose3D for 2-min clips (16 MB uncompressed)",
        "extract": True,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for candidate in [here, *here.parents]:
        if (candidate / ".git").exists():
            return candidate
    sys.exit(
        "ERROR: Could not find repository root (.git not found). "
        "Run this script from inside the cloned repository."
    )


def ensure_gdown() -> None:
    try:
        import gdown  # noqa: F401
    except ImportError:
        sys.exit("ERROR: gdown is not installed.\n  pip install gdown")


def extract_archive(path: Path) -> None:
    dest_dir = path.parent
    print(f"  [EXT]  Extracting {path.name} ...")
    if path.name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar")):
        with tarfile.open(path) as tf:
            tf.extractall(dest_dir)
    elif path.name.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            zf.extractall(dest_dir)
    else:
        print(f"  [WARN] Unknown archive type: {path.name}, skipping extraction.")
        return
    path.unlink()
    print(f"  [EXT]  Done -archive removed.")


# ---------------------------------------------------------------------------
# Download logic
# ---------------------------------------------------------------------------

def download_all(repo_root: Path, force: bool) -> None:
    import gdown
    import tempfile

    # Build filename -> (dest, extract) map from MANIFEST
    manifest_map = {
        e["filename"]: (repo_root / e["dest"], e.get("extract", False))
        for e in MANIFEST
    }

    # Check which files already exist
    missing = {f: v for f, v in manifest_map.items() if not v[0].exists()}
    already_have = len(manifest_map) - len(missing)

    if not force and already_have:
        print(f"  {already_have} file(s) already present, skipping.")

    if not missing and not force:
        print("All files already downloaded.")
        return

    targets = manifest_map if force else missing
    print(f"Downloading {len(targets)} file(s) from Drive folder ...\n")

    with tempfile.TemporaryDirectory(prefix="rack-tracker-dl-") as tmp:
        tmp_path = Path(tmp)
        downloaded = gdown.download_folder(
            id=DRIVE_FOLDER_ID,
            output=tmp,
            quiet=False,
        )
        if downloaded is None:
            sys.exit(
                "ERROR: gdown could not access the Drive folder.\n"
                "  Make sure the folder is shared with 'Anyone with the link'."
            )

        downloaded_names = {Path(p).name: Path(p) for p in downloaded}

        errors: list[str] = []
        for fname, (dest, do_extract) in targets.items():
            src = downloaded_names.get(fname)
            if src is None:
                print(f"  [MISS] {fname} not found in Drive folder.")
                errors.append(fname)
                continue

            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            print(f"  [OK]   {fname} -> {dest.relative_to(repo_root)}")

            if do_extract and dest.exists():
                extract_archive(dest)

    print()
    if errors:
        print(f"WARNING: {len(errors)} file(s) missing from Drive folder:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("Done.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--list", action="store_true", help="Print manifest and exit.")
    parser.add_argument("--force", action="store_true", help="Re-download existing files.")
    args = parser.parse_args()

    repo_root = find_repo_root()

    if args.list:
        print(f"Repo root     : {repo_root}")
        print(f"Drive folder  : {DRIVE_FOLDER_ID}\n")
        print(f"{'FILENAME':<50} DESCRIPTION")
        print("-" * 90)
        for entry in MANIFEST:
            print(f"{entry['filename']:<50} {entry['description']}")
        return

    if DRIVE_FOLDER_ID == "REPLACE_WITH_GOOGLE_DRIVE_FOLDER_ID":
        sys.exit(
            "ERROR: DRIVE_FOLDER_ID is not set.\n"
            "  Edit scripts/download_data.py and paste the shared folder ID."
        )

    ensure_gdown()

    print(f"Repo root    : {repo_root}")
    print(f"Drive folder : {DRIVE_FOLDER_ID}")
    print(f"Entries      : {len(MANIFEST)}\n")

    download_all(repo_root, force=args.force)


if __name__ == "__main__":
    main()
