from __future__ import annotations

import colorsys
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from PIL import Image, ImageOps


FaceBox = tuple[int, int, int, int]
FaceDetector = Callable[[Image.Image], Sequence[FaceBox]]
FACE_MATCH_THRESHOLD = 0.75


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(float(value), 0.99))


def _iter_rgb_pixels(image: Image.Image) -> Iterable[tuple[int, int, int]]:
    data = image.convert("RGB").tobytes()
    for index in range(0, len(data), 3):
        yield data[index], data[index + 1], data[index + 2]


def _fire_pixel_flags(red: int, green: int, blue: int) -> tuple[bool, bool, bool]:
    h, s, v = colorsys.rgb_to_hsv(red / 255.0, green / 255.0, blue / 255.0)
    hue = h * 360.0
    warm_hue = hue <= 60.0 or hue >= 345.0
    strict_fire = (
        warm_hue
        and s >= 0.50
        and v >= 0.40
        and red >= 145
        and green >= 45
        and blue <= 110
        and red >= blue * 1.55
        and green >= blue * 0.85
    )
    hot_fire = (
        warm_hue
        and s >= 0.58
        and v >= 0.50
        and red >= 170
        and green >= 60
        and blue <= 95
        and red >= blue * 1.80
    )
    yellow_core = (
        18.0 <= hue <= 55.0
        and s >= 0.55
        and v >= 0.55
        and red >= 170
        and green >= 100
        and blue <= 95
    )
    red_core = (
        (hue <= 18.0 or hue >= 345.0)
        and s >= 0.55
        and v >= 0.45
        and red >= 160
        and blue <= 120
        and red >= green * 1.05
    )
    return strict_fire, hot_fire, yellow_core or red_core


def _best_local_ratio(mask: Sequence[int], width: int, height: int) -> float:
    integral = [[0] * (width + 1) for _ in range(height + 1)]
    for y in range(height):
        row_total = 0
        source_offset = y * width
        for x in range(width):
            row_total += mask[source_offset + x]
            integral[y + 1][x + 1] = integral[y][x + 1] + row_total

    best_ratio = 0.0
    for tile_size in (16, 24, 32, 48, 64):
        if tile_size > width or tile_size > height:
            continue
        step = max(1, tile_size // 2)
        for y in range(0, height - tile_size + 1, step):
            y2 = y + tile_size
            for x in range(0, width - tile_size + 1, step):
                x2 = x + tile_size
                count = (
                    integral[y2][x2]
                    - integral[y][x2]
                    - integral[y2][x]
                    + integral[y][x]
                )
                best_ratio = max(best_ratio, count / (tile_size * tile_size))
    return best_ratio


def calculate_fire_confidence(image: Image.Image) -> float:
    """Estimate fire confidence from global and local flame-colored regions."""
    sample = ImageOps.exif_transpose(image).convert("RGB")
    sample.thumbnail((320, 320))

    width, height = sample.size
    strict_mask: list[int] = []
    hot_mask: list[int] = []
    core_mask: list[int] = []
    for red, green, blue in _iter_rgb_pixels(sample):
        strict_fire, hot_fire, core_fire = _fire_pixel_flags(red, green, blue)
        strict_mask.append(int(strict_fire))
        hot_mask.append(int(hot_fire))
        core_mask.append(int(core_fire))

    total = width * height
    if total == 0:
        return 0.0

    strict_ratio = sum(strict_mask) / total
    hot_ratio = sum(hot_mask) / total
    core_ratio = sum(core_mask) / total
    local_strict_ratio = _best_local_ratio(strict_mask, width, height)
    local_hot_ratio = _best_local_ratio(hot_mask, width, height)
    local_core_ratio = _best_local_ratio(core_mask, width, height)

    global_score = (
        min(strict_ratio / 0.12, 1.0) * 0.12
        + min(hot_ratio / 0.08, 1.0) * 0.12
        + min(core_ratio / 0.08, 1.0) * 0.10
    )
    local_score = (
        min(local_strict_ratio / 0.55, 1.0) * 0.28
        + min(local_hot_ratio / 0.35, 1.0) * 0.34
        + min(local_core_ratio / 0.30, 1.0) * 0.28
    )
    confidence = global_score + local_score
    if local_hot_ratio < 0.12 or local_core_ratio < 0.12 or local_strict_ratio < 0.35:
        confidence = min(confidence, 0.45)
    return round(_clamp_confidence(confidence), 4)


def calculate_face_confidence(face_boxes: Sequence[FaceBox], image_size: tuple[int, int]) -> float:
    if not face_boxes:
        return 0.0

    width, height = image_size
    image_area = max(width * height, 1)
    largest_area_ratio = max((box[2] * box[3]) / image_area for box in face_boxes)

    base_score = 0.58
    size_score = min(largest_area_ratio / 0.10, 1.0) * 0.32
    count_score = min(len(face_boxes), 3) * 0.03
    return round(_clamp_confidence(base_score + size_score + count_score), 4)


def _prepare_face_comparison_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    grayscale = ImageOps.exif_transpose(image).convert("L")
    return ImageOps.autocontrast(grayscale).resize(size)


def _average_hash_bits(image: Image.Image, size: int = 16) -> list[bool]:
    sample = _prepare_face_comparison_image(image, (size, size))
    pixels = list(sample.tobytes())
    average = sum(pixels) / len(pixels)
    return [pixel >= average for pixel in pixels]


def _difference_hash_bits(image: Image.Image, width: int = 17, height: int = 16) -> list[bool]:
    sample = _prepare_face_comparison_image(image, (width, height))
    pixels = list(sample.tobytes())
    bits: list[bool] = []
    for y in range(height):
        row = pixels[y * width : (y + 1) * width]
        bits.extend(row[x] > row[x + 1] for x in range(width - 1))
    return bits


def _hash_similarity(left: Sequence[bool], right: Sequence[bool]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    return sum(left_bit == right_bit for left_bit, right_bit in zip(left, right)) / len(left)


def _histogram_similarity(left: Image.Image, right: Image.Image, bins: int = 32) -> float:
    left_sample = _prepare_face_comparison_image(left, (128, 128))
    right_sample = _prepare_face_comparison_image(right, (128, 128))

    def normalized_histogram(image: Image.Image) -> list[float]:
        histogram = [0] * bins
        for value in image.tobytes():
            histogram[min(value * bins // 256, bins - 1)] += 1
        total = max(sum(histogram), 1)
        return [count / total for count in histogram]

    left_histogram = normalized_histogram(left_sample)
    right_histogram = normalized_histogram(right_sample)
    return sum(min(left_value, right_value) for left_value, right_value in zip(left_histogram, right_histogram))


def calculate_face_match_confidence(image: Image.Image, reference_image: Image.Image) -> float:
    left_sample = _prepare_face_comparison_image(image, (96, 96))
    right_sample = _prepare_face_comparison_image(reference_image, (96, 96))

    left_pixels = left_sample.tobytes()
    right_pixels = right_sample.tobytes()
    mean_absolute_error = sum(
        abs(left - right) for left, right in zip(left_pixels, right_pixels)
    ) / (255 * len(left_pixels))
    pixel_similarity = 1.0 - mean_absolute_error

    average_hash_similarity = _hash_similarity(
        _average_hash_bits(image),
        _average_hash_bits(reference_image),
    )
    difference_hash_similarity = _hash_similarity(
        _difference_hash_bits(image),
        _difference_hash_bits(reference_image),
    )
    histogram_similarity = _histogram_similarity(image, reference_image)

    confidence = (
        pixel_similarity * 0.35
        + average_hash_similarity * 0.25
        + difference_hash_similarity * 0.25
        + histogram_similarity * 0.15
    )
    return round(_clamp_confidence(confidence), 4)


def compare_face_whitelist(
    image: Image.Image,
    reference_faces: Sequence[Mapping[str, Any]],
    threshold: float = FACE_MATCH_THRESHOLD,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for reference in reference_faces:
        raw_path = reference.get("image_path") or reference.get("path")
        if not raw_path:
            continue

        face_id = str(reference.get("id") or reference.get("face_id") or Path(raw_path).stem)
        result: dict[str, Any] = {
            "face_id": face_id,
            "name": reference.get("name") or reference.get("label") or face_id,
            "role": reference.get("role"),
            "image_path": str(raw_path),
        }
        try:
            with Image.open(raw_path) as reference_original:
                reference_image = ImageOps.exif_transpose(reference_original).convert("RGB")
            confidence = calculate_face_match_confidence(image, reference_image)
            result.update(
                {
                    "confidence": confidence,
                    "matched": confidence >= threshold,
                    "status": "completed",
                }
            )
        except Exception as exc:
            result.update(
                {
                    "confidence": 0.0,
                    "matched": False,
                    "status": "error",
                    "reason": str(exc),
                }
            )
        results.append(result)

    completed_results = [
        result for result in results if result.get("status") == "completed"
    ]
    best_match = max(
        completed_results,
        key=lambda result: float(result.get("confidence") or 0.0),
        default=None,
    )
    matched_results = [
        result for result in completed_results if bool(result.get("matched"))
    ]
    return {
        "checked": bool(completed_results),
        "matched": bool(matched_results),
        "matched_face_ids": [str(result["face_id"]) for result in matched_results],
        "best_match": best_match,
        "matches": results,
        "threshold": threshold,
    }


def detect_face_boxes(image: Image.Image) -> list[FaceBox]:
    try:
        import cv2
    except ImportError:
        return []

    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(str(cascade_path))
    if cascade.empty():
        return []

    rgb_image = image.convert("RGB")
    gray = cv2.cvtColor(__import__("numpy").array(rgb_image), cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    faces, _, weights = cascade.detectMultiScale3(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(32, 32),
        outputRejectLevels=True,
    )
    return [
        (int(x), int(y), int(w), int(h))
        for (x, y, w, h), weight in zip(faces, weights)
        if float(weight) >= 3.5
    ]


def analyze_image_confidence(
    image_path: str | Path,
    face_detector: FaceDetector | None = None,
    reference_face_path: str | Path | None = None,
    reference_faces: Sequence[Mapping[str, Any]] | None = None,
    face_match_threshold: float = FACE_MATCH_THRESHOLD,
) -> dict[str, Any]:
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"image not found: {path}")
    if not path.is_file():
        raise ValueError(f"image path is not a file: {path}")

    with Image.open(path) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")

    detector = face_detector or detect_face_boxes
    face_boxes = list(detector(image))
    fire_confidence = calculate_fire_confidence(image)
    face_reference_path = str(reference_face_path) if reference_face_path else None
    if reference_face_path:
        with Image.open(reference_face_path) as reference_original:
            reference_image = ImageOps.exif_transpose(reference_original).convert("RGB")
        face_confidence = calculate_face_match_confidence(image, reference_image)
        face_detected = face_confidence >= FACE_MATCH_THRESHOLD
    else:
        face_confidence = calculate_face_confidence(face_boxes, image.size)
        face_detected = face_confidence > 0

    whitelist_result = compare_face_whitelist(
        image,
        reference_faces or [],
        threshold=face_match_threshold,
    )
    if whitelist_result["checked"]:
        best_match = whitelist_result.get("best_match") or {}
        face_confidence = float(best_match.get("confidence") or 0.0)
        face_detected = bool(face_boxes) or bool(whitelist_result["matched"])

    return {
        "image_path": str(path),
        "fire_confidence": fire_confidence,
        "face_confidence": face_confidence,
        "face_count": len(face_boxes),
        "face_boxes": [
            {"x": x, "y": y, "width": width, "height": height}
            for x, y, width, height in face_boxes
        ],
        "image_features": {
            "fire_score": fire_confidence,
            "flame_detected": fire_confidence >= 0.5,
            "face_score": face_confidence,
            "face_count": len(face_boxes),
            "face_detected": face_detected,
            "face_reference_path": face_reference_path,
            "face_whitelist_checked": whitelist_result["checked"],
            "face_whitelist_matched": whitelist_result["matched"],
            "face_whitelist_threshold": whitelist_result["threshold"],
            "face_whitelist_best_match": whitelist_result["best_match"],
            "face_whitelist_matches": whitelist_result["matches"],
            "face_ids": whitelist_result["matched_face_ids"],
        },
    }
