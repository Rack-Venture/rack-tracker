import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8080"))
BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "tmp"
UPLOAD_DIR = TEMP_DIR / "uploads"
EXTRACTED_FRAME_DIR = TEMP_DIR / "frames"
BENCHMARK_DIR = TEMP_DIR / "benchmarks"
SKELETON_DIR = TEMP_DIR / "skeletons"
SYNTHESIS_DIR = TEMP_DIR / "synthesis"
PRESET_ESTIMATION_DIR = BASE_DIR / "src" / "preset_estimations"
DEFAULT_MODEL_DIR = BASE_DIR / "models" / "mediapipe"
MODEL_DIR = Path(os.getenv("POSE_MODEL_DIR", "").strip() or DEFAULT_MODEL_DIR)
MODEL_ASSET_PATHS = {
    "lite": MODEL_DIR / "pose_landmarker_lite.task",
    "full": MODEL_DIR / "pose_landmarker_full.task",
    "heavy": MODEL_DIR / "pose_landmarker_heavy.task",
}
DEFAULT_MODEL_VARIANT = "full"
DEFAULT_MODEL_ASSET_PATH = MODEL_ASSET_PATHS[DEFAULT_MODEL_VARIANT]
MOCK_VIDEO_PATH = BASE_DIR / "src" / "video" / "backSquat.mp4"
# Skeleton synthesis experiment mode: general motion (exercise-agnostic)
# Squat-specific defaults preserved below for reference when squat pipeline is restored
MOCK_VIDEO_EXERCISE_TYPE = None  # None → resolves to "general_motion" in pipeline
MOCK_VIDEO_BODYWEIGHT_KG = None  # not used in general motion mode
MOCK_VIDEO_EXTERNAL_LOAD_KG = None  # not used in general motion mode
# MOCK_VIDEO_EXERCISE_TYPE = "squat"  # squat pipeline reference
# MOCK_VIDEO_BODYWEIGHT_KG = 73.0
# MOCK_VIDEO_EXTERNAL_LOAD_KG = 260.0
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "").strip()
LLM_FEEDBACK_MODEL: str = os.environ.get("LLM_FEEDBACK_MODEL", "claude-sonnet-4-6").strip()
LLM_FEEDBACK_ENABLED: bool = bool(ANTHROPIC_API_KEY)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTED_FRAME_DIR.mkdir(parents=True, exist_ok=True)
BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
SKELETON_DIR.mkdir(parents=True, exist_ok=True)
SYNTHESIS_DIR.mkdir(parents=True, exist_ok=True)
PRESET_ESTIMATION_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
