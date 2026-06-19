from __future__ import annotations

from pathlib import Path

from app.services.image_detection import analyze_image_confidence


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIRE_SAMPLE = PROJECT_ROOT / "火焰.jpg"
FACE_SAMPLE = PROJECT_ROOT / "人脸.jpg"
TEST_PICS = PROJECT_ROOT / "test_pics"


def test_fire_image_outputs_high_fire_confidence() -> None:
    result = analyze_image_confidence(FIRE_SAMPLE, face_detector=lambda _: [])

    assert result["fire_confidence"] >= 0.80
    assert result["face_confidence"] == 0.0
    assert result["image_features"]["flame_detected"] is True


def test_face_image_outputs_reference_match_confidence() -> None:
    result = analyze_image_confidence(
        FACE_SAMPLE,
        reference_face_path=FACE_SAMPLE,
    )

    assert result["face_confidence"] >= 0.95
    assert result["image_features"]["flame_detected"] is False
    assert result["image_features"]["face_detected"] is True
    assert result["image_features"]["face_reference_path"] == str(FACE_SAMPLE)


def test_local_fire_images_output_high_fire_confidence() -> None:
    for image_name in ("fire1.png", "fire2.jpg"):
        result = analyze_image_confidence(
            TEST_PICS / image_name,
            face_detector=lambda _: [],
        )

        assert result["fire_confidence"] >= 0.80
        assert result["image_features"]["flame_detected"] is True


def test_non_matching_face_image_does_not_pass_reference_threshold() -> None:
    result = analyze_image_confidence(
        TEST_PICS / "face1.jpg",
        reference_face_path=FACE_SAMPLE,
    )

    assert result["face_confidence"] < 0.75
    assert result["image_features"]["face_detected"] is False
