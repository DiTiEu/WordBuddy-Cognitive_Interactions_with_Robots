# scripts/collect_dataset_slots.py
import os, sys, time
import cv2
import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.board_vision import build_board_vision_from_config_dict


def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)


def normalize_label_string(s: str) -> str:
    s = s.strip().upper().replace(" ", "")
    # accetta '_' o '.' o '-' come vuoto
    s = s.replace(".", "_").replace("-", "_")
    if len(s) != 5:
        raise ValueError("Label must be 5 chars, e.g. A__B_")
    out = []
    for c in s:
        if c == "_" or c == " ":
            out.append("_")
        elif "A" <= c <= "Z":
            out.append(c)
        else:
            out.append("_")
    return "".join(out)


def main():
    cfg = yaml.safe_load(open("data/config.yaml", "r", encoding="utf-8"))
    vision = build_board_vision_from_config_dict(cfg)

    if len(vision.cfg.slots_roi_px) != 5:
        raise RuntimeError("Run scripts/calibrate_slots.py first and paste slots_roi_px into config.yaml")

    out_root = "data/dataset_slots"
    ensure_dir(out_root)

    print("\nDataset collection")
    print("Per ogni scatto, inserisci 5 char tipo: A__B_  (underscore = vuoto)")
    print("Invio vuoto per uscire.\n")

    idx = 0
    while True:
        input("Metti i blocchi e premi INVIO per scattare...")

        frame = vision.capture_frame()
        topdown, _ = vision.warper.warp(frame)
        slots = vision._extract_slots(topdown)

        label = input("Label 5-char (es A__B_): ").strip()
        if not label:
            break

        label = normalize_label_string(label)

        # salva topdown debug opzionale
        ensure_dir("data/dataset_slots/_debug")
        cv2.imwrite(f"data/dataset_slots/_debug/topdown_{idx:05d}.png", topdown)

        for i in range(5):
            c = label[i]
            cls_dir = os.path.join(out_root, c)  # '_' oppure 'A'..'Z'
            ensure_dir(cls_dir)
            fn = os.path.join(cls_dir, f"{idx:05d}_slot{i}.png")
            cv2.imwrite(fn, slots[i])

        print(f"✅ salvato sample #{idx}: {label}")
        idx += 1

    print("Fatto.")


if __name__ == "__main__":
    main()
