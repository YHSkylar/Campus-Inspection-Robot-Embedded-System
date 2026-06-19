from __future__ import annotations

import argparse
import json
from pathlib import Path


MAP_NAME = "campus_empty_5x7"

# Map size in meters. The world frame origin is placed at the map center.
MAP_WIDTH_M = 5.0
MAP_HEIGHT_M = 7.0
RESOLUTION_M = 0.05
WALL_THICKNESS_M = 0.10

# PGM values used by ROS map_server with negate: 0.
FREE = 254
OCCUPIED = 0

ORIGIN = (-MAP_WIDTH_M / 2.0, -MAP_HEIGHT_M / 2.0, 0.0)

# Keep only a start point and two well-spaced inspection points.
WAYPOINTS = [
    {
        "id": "start",
        "name": "start_charging_area",
        "x": 0.0,
        "y": -3.0,
        "yaw": 1.5708,
    },
    {
        "id": "inspection_1",
        "name": "left_upper_area",
        "x": -1.8,
        "y": 2.4,
        "yaw": 0.0,
    },
    {
        "id": "inspection_2",
        "name": "right_upper_area",
        "x": 1.8,
        "y": 2.4,
        "yaw": 3.1416,
    },
]


def world_to_pixel(x: float, y: float, width_px: int, height_px: int) -> tuple[int, int]:
    px = round((x - ORIGIN[0]) / RESOLUTION_M)
    py_from_bottom = round((y - ORIGIN[1]) / RESOLUTION_M)
    py = height_px - 1 - py_from_bottom
    return px, py


def build_map() -> list[list[int]]:
    width_px = round(MAP_WIDTH_M / RESOLUTION_M)
    height_px = round(MAP_HEIGHT_M / RESOLUTION_M)
    wall_px = max(1, round(WALL_THICKNESS_M / RESOLUTION_M))

    pixels = [[FREE for _ in range(width_px)] for _ in range(height_px)]

    for y in range(height_px):
        for x in range(width_px):
            in_wall = (
                x < wall_px
                or x >= width_px - wall_px
                or y < wall_px
                or y >= height_px - wall_px
            )
            if in_wall:
                pixels[y][x] = OCCUPIED

    return pixels


def write_pgm(path: Path, pixels: list[list[int]]) -> None:
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    with path.open("wb") as handle:
        handle.write(f"P5\n# {MAP_NAME}\n{width} {height}\n255\n".encode("ascii"))
        for row in pixels:
            handle.write(bytes(row))


def write_map_yaml(path: Path, image_name: str) -> None:
    path.write_text(
        "\n".join(
            [
                f"image: {image_name}",
                f"resolution: {RESOLUTION_M}",
                f"origin: [{ORIGIN[0]}, {ORIGIN[1]}, {ORIGIN[2]}]",
                "negate: 0",
                "occupied_thresh: 0.65",
                "free_thresh: 0.196",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_waypoints_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "frame_id": "map",
                "route": [waypoint["id"] for waypoint in WAYPOINTS],
                "waypoints": WAYPOINTS,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_waypoints_yaml(path: Path) -> None:
    lines = ["frame_id: map", "route:"]
    lines.extend(f"  - {waypoint['id']}" for waypoint in WAYPOINTS)
    lines.append("waypoints:")
    for waypoint in WAYPOINTS:
        lines.extend(
            [
                f"  - id: {waypoint['id']}",
                f"    name: {waypoint['name']}",
                f"    x: {waypoint['x']}",
                f"    y: {waypoint['y']}",
                f"    yaw: {waypoint['yaw']}",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(pixels: list[list[int]], output_dir: Path) -> None:
    height = len(pixels)
    width = len(pixels[0]) if height else 0
    print(f"Generated map: {MAP_WIDTH_M}m x {MAP_HEIGHT_M}m")
    print(f"Resolution: {RESOLUTION_M}m/cell")
    print(f"Grid: {width} x {height}")
    print(f"Origin: {ORIGIN}")
    print(f"Output: {output_dir.resolve()}")
    print("Waypoints:")
    for waypoint in WAYPOINTS:
        px, py = world_to_pixel(waypoint["x"], waypoint["y"], width, height)
        print(
            f"  {waypoint['id']}: "
            f"({waypoint['x']}, {waypoint['y']}, yaw={waypoint['yaw']}) "
            f"pixel=({px}, {py})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a simple ROS map for patrol demo.")
    parser.add_argument(
        "--output-dir",
        default="ros_maps",
        help="Directory for generated map and waypoint files.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pixels = build_map()
    pgm_path = output_dir / f"{MAP_NAME}.pgm"
    yaml_path = output_dir / f"{MAP_NAME}.yaml"

    write_pgm(pgm_path, pixels)
    write_map_yaml(yaml_path, pgm_path.name)
    write_waypoints_json(output_dir / "patrol_waypoints.json")
    write_waypoints_yaml(output_dir / "patrol_waypoints.yaml")
    print_summary(pixels, output_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
