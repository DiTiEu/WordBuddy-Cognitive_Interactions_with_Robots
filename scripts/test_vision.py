# scripts/test_vision.py
import os, sys, time, traceback, cv2
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.board_vision import build_board_vision_from_config_dict

print("[1] Starting test_vision.py", flush=True)

try:
    print("[2] Loading config...", flush=True)
    cfg = yaml.safe_load(open(os.path.join(ROOT, "data", "config.yaml"), "r", encoding="utf-8"))
    print("[2] OK", flush=True)

    print("[3] Building BoardVision...", flush=True)
    vision = build_board_vision_from_config_dict(cfg)
    print("[3] OK", flush=True)

    print("[4] Capturing frame...", flush=True)
    t0 = time.time()
    frame = vision.capture_frame()
    os.makedirs("data/test_logs", exist_ok=True)
    cv2.imwrite("data/test_logs/raw_frame.png", frame)
    print("[4b] Saved data/test_logs/raw_frame.png", flush=True)
    print("[4] OK shape=", getattr(frame, "shape", None), "t=", round(time.time()-t0, 2), "s", flush=True)

    print("[5] Reading from frame...", flush=True)
    t0 = time.time()
    out = vision.read_from_frame(frame, save_debug=True)
    print("[5] OK t=", round(time.time()-t0, 2), "s", flush=True)

    print("Detected raw:", repr(out), flush=True)
    print("Detected spaced:", " ".join(list(out)), flush=True)
    print("Debug: data/test_logs/topdown_debug.png", flush=True)

except Exception:
    print("\n[ERROR] Exception occurred:", flush=True)
    traceback.print_exc()
