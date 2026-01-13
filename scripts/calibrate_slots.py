# scripts/calibrate_slots.py
# Script per calibrare le ROI degli slot sul piano di gioco.
# Salva un'immagine di sfondo warpata (foglio vuoto) e permette
# di selezionare manualmente le ROI degli slot, salvando le coordinate

import os
import cv2
import yaml

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.board_vision import build_board_vision_from_config_dict


def draw_slots_overlay(topdown_bgr, rois):
    """Disegna ROI e indici sopra l'immagine topdown."""
    img = topdown_bgr.copy()
    for i, (x, y, w, h) in enumerate(rois):
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.putText(
            img,
            f"slot {i}",
            (x + 5, y + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )
    return img


def main():
    cfg_path = os.path.join("data", "config.yaml")
    cfg = yaml.safe_load(open(cfg_path, "r", encoding="utf-8"))

    vision = build_board_vision_from_config_dict(cfg)

    os.makedirs("data/calibration", exist_ok=True)

    print("Metti il foglio VUOTO (senza blocchi) e premi INVIO...")
    input()

    # 1) cattura + warp
    frame = vision.capture_frame()
    topdown, _ = vision.warper.warp(frame)

    # 2) salva background warpato (foglio vuoto)
    cv2.imwrite("data/calibration/board_bg.png", topdown)
    cv2.imwrite("data/calibration/board_topdown.png", topdown)
    print("✅ Salvati:")
    print("  - data/calibration/board_bg.png")
    print("  - data/calibration/board_topdown.png")

    # 3) selezione ROI slot
    print("\nOra seleziona le 5 ROI (slot 0→4 da sinistra a destra).")
    rois = []
    show = topdown.copy()

    for i in range(5):
        r = cv2.selectROI(
            f"Select slot ROI {i} (ENTER ok, c cancel)",
            show,
            fromCenter=False,
            showCrosshair=True,
        )
        x, y, w, h = map(int, r)
        if w == 0 or h == 0:
            raise RuntimeError("ROI canceled/empty")
        rois.append([x, y, w, h])

    cv2.destroyAllWindows()

    # 4) salva overlay di verifica
    overlay = draw_slots_overlay(topdown, rois)
    cv2.imwrite("data/calibration/board_slots_overlay.png", overlay)
    print("✅ Salvato: data/calibration/board_slots_overlay.png (verifica ROI)")

    # 5) stampa YAML da incollare
    print("\n--- INCOLLA QUESTO in data/config.yaml sotto vision: ---")
    print("  slots_roi_px:")
    for r in rois:
        print(f"    - [{r[0]}, {r[1]}, {r[2]}, {r[3]}]")


if __name__ == "__main__":
    main()
