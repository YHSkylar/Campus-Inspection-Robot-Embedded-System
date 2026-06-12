from __future__ import annotations

import argparse

from .ros_support import build_ros_node_from_file, default_ros_config_path


def main() -> int:
    parser = argparse.ArgumentParser(description="ROS bridge for campus inspection embedded subsystem")
    parser.add_argument(
        "--config",
        default=str(default_ros_config_path()),
        help="Path to the ROS-enabled JSON config file.",
    )
    args = parser.parse_args()
    node = build_ros_node_from_file(args.config)
    node.spin()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
