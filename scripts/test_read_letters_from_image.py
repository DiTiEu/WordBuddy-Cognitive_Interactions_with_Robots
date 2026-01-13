# scripts/test_read_letters_from_image.py
# legge una JPEG e stampa la stringa

import os
import argparse
import yaml

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.board_vision import build_board_vision_from_config_dict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to a jpeg/png to test")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(os.path.join("data", "config.yaml"), "r", encoding="utf-8"))
    vision = build_board_vision_from_config_dict(cfg)

    s = vision.read_from_image(args.image, save_debug=True)
    print("READ STRING:", repr(s))
    print("Saved debug to data/test_logs/: topdown.png, debug.png, topdown_debug.png, slot*_pre.png")


if __name__ == "__main__":
    main()
