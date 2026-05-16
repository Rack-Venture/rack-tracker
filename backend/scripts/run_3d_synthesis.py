from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from schema.synthesis import SynthesisInput, SynthesisJobCreateRequest
from service.skeleton_3d_evaluator import Skeleton3DEvaluator
from service.skeleton_3d_synthesizer import Skeleton3DSynthesizer
from service.skeleton_artifact_repository import SkeletonArtifactRepository
from service.synthesis_job_manager import DEFAULT_GT_REF


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local skeleton3d synthesis smoke test.")
    parser.add_argument("--input", required=True, help="Path to synthesis request JSON.")
    parser.add_argument("--output", required=True, help="Output directory for generated artifacts.")
    parser.add_argument("--run-evaluation", action="store_true", help="Also write GT evaluation JSON.")
    parser.add_argument("--gt-ref", default=DEFAULT_GT_REF, help="GT skeleton JSON path.")
    args = parser.parse_args()

    request_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    request = SynthesisJobCreateRequest.model_validate_json(
        request_path.read_text(encoding="utf-8")
    )
    synthesis_input = SynthesisInput.from_manifest(request.pairManifest)
    repository = SkeletonArtifactRepository(synthesis_dir=output_dir)
    synthesizer = Skeleton3DSynthesizer(artifact_repository=repository)
    skeleton3d = synthesizer.synthesize(synthesis_input)

    skeleton3d_path = output_dir / "skeleton3d.json"
    skeleton3d_path.write_text(
        json.dumps(skeleton3d, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if args.run_evaluation or request.options.runEvaluation:
        evaluator = Skeleton3DEvaluator()
        evaluation = evaluator.evaluate(
            skeleton3d=skeleton3d,
            gt_ref=request.options.gtRef or args.gt_ref,
        )
        (output_dir / "evaluation.json").write_text(
            json.dumps(evaluation, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(str(skeleton3d_path))


if __name__ == "__main__":
    main()
