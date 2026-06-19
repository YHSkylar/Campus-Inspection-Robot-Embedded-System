from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.image_detection import analyze_image_confidence


def main() -> None:
    parser = argparse.ArgumentParser(description="Detect fire/face confidence from one image.")
    parser.add_argument("image", help="Path to the image file to inspect.")
    parser.add_argument(
        "--reference-face",
        help="Optional whitelist face image used to calculate face match confidence.",
    )
    args = parser.parse_args()

    result = analyze_image_confidence(args.image, reference_face_path=args.reference_face)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
