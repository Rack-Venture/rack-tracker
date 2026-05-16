from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

paths = [
    REPO_ROOT / "docs" / "mvp-v1" / "features" / "mediapipe" / "core" / "decision-checklist-phase-1-index-01.md",
    REPO_ROOT / "docs" / "mvp-v1" / "features" / "mediapipe" / "core" / "architecture.md",
    REPO_ROOT / "docs" / "mvp-v1" / "features" / "mediapipe" / "core" / "spec.md",
]

for path in paths:
    print(f"===== {path} =====")
    print(path.read_text(encoding="utf-8"))
