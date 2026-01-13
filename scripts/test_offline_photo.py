# scripts/test_offline_photo.py
# Test OFFLINE (da una singola immagine), senza camera e senza background "foglio vuoto".
#
# Usage:
#   python scripts/test_offline_photo.py --image data/test_images/photo.jpg --outdir data/test_logs_offline
#
# Funziona così:
#  1) warpa la board con ArUco (usa config.yaml se presente)
#  2) se slots_roi_px non è nel config, ti fa selezionare 5 ROI con il mouse (slot 0..4)
#  3) decide vuoto/pieno con euristica basata su luminosità (cerchio nero vs disco bianco)
#  4) se Tesseract è disponibile, prova OCR sulle ROI occupate
#  5) salva debug immagini in outdir

import os
import argparse
import cv2
import numpy as np

try:
    import yaml
except Exception:
    yaml = None

import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.board_vision import BoardWarper, WarpConfig
from src.letter_recognition import LetterRecognizer, OCRConfig


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def load_yaml_config(path: str) -> dict:
    if yaml is None or not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def draw_overlay(topdown, rois, occ_flags, occ_scores, out_str, ocr_confs):
    img = topdown.copy()
    for i, (x, y, w, h) in enumerate(rois):
        color = (0, 255, 0) if occ_flags[i] else (0, 0, 255)
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
        txt = f"{i}: '{out_str[i]}' occ={occ_scores[i]:.1f} ocr={ocr_confs[i]:.0f}"
        cv2.putText(img, txt, (x + 5, y + 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    return img


def occupancy_heuristic(slot_bgr: np.ndarray) -> float:
    """
    Score semplice basato su luminosità:
    - slot vuoto: cerchio nero -> patch mediamente scura
    - slot pieno: disco bianco -> patch mediamente chiara
    Ritorna uno score (più alto = più "bianco"/pieno).
    """
    g = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)
    g = cv2.GaussianBlur(g, (3, 3), 0)

    mean_val = float(np.mean(g))
    bright_frac = float(np.mean(g > 200))  # frazione pixel molto chiari

    # combina i due segnali: scala bright_frac in "punti" (0..100 circa)
    score = mean_val + 200.0 * bright_frac
    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="Path to photo.jpg (with markers visible)")
    ap.add_argument("--outdir", default="data/test_logs_offline", help="Output dir for debug images")
    ap.add_argument("--config", default="data/config.yaml", help="Path to config.yaml (optional)")
    ap.add_argument("--force_select_rois", action="store_true", help="Force manual ROI selection even if config has them")
    args = ap.parse_args()

    ensure_dir(args.outdir)

    img = cv2.imread(args.image)
    if img is None:
        raise RuntimeError(f"Cannot read image: {args.image}")

    cfg = load_yaml_config(args.config)
    v = cfg.get("vision", {}) if isinstance(cfg, dict) else {}

    # --- warp size coerente con board (default 260x200 mm) ---
    board_mm = v.get("board_size_mm", [260, 200])
    px_per_mm = float(v.get("px_per_mm", 4))
    W_px = int(round(float(board_mm[0]) * px_per_mm))
    H_px = int(round(float(board_mm[1]) * px_per_mm))

    aruco_dict = str(v.get("aruco_dict", "DICT_4X4_50"))
    aruco_ids = list(map(int, v.get("aruco_ids", [0, 1, 2, 3])))

    rot = str(v.get("rotate_topdown", "CW90"))  # oppure "CW90" fisso
    warper = BoardWarper(WarpConfig(
        aruco_dict=aruco_dict,
        aruco_ids=aruco_ids,
        warp_size_px=(W_px, H_px),
        rotate=rot,
    ))


    # --- warp ---
    topdown, dbg = warper.warp(img)
    print("ROT USED:", dbg.get("rotate"))
    print("WARP OUT:", dbg.get("warp_size_px_out"), "INTERNAL:", dbg.get("warp_size_px_internal"))
    cv2.imwrite(os.path.join(args.outdir, "topdown.png"), topdown)
    cv2.imwrite(os.path.join(args.outdir, "debug.png"), warper.draw_debug(img, dbg))

    # --- ROIs: da config se ci sono, altrimenti manuale ---
    rois = v.get("slots_roi_px", [])
    rois = [tuple(map(int, r)) for r in rois] if rois else []

    if args.force_select_rois or len(rois) != 5:
        print("\nSeleziona 5 ROI (slot 0..4 da sinistra a destra) sulla TOPDOWN.")
        tmp = topdown.copy()
        rois = []
        for i in range(5):
            r = cv2.selectROI(f"Select slot ROI {i} (ENTER ok, c cancel)", tmp, fromCenter=False, showCrosshair=True)
            x, y, w, h = map(int, r)
            if w == 0 or h == 0:
                raise RuntimeError("ROI canceled/empty")
            rois.append((x, y, w, h))
        cv2.destroyAllWindows()

        # stampa formato YAML per incollarlo dopo (se vuoi)
        print("\n--- slots_roi_px (per config.yaml) ---")
        print("  slots_roi_px:")
        for (x, y, w, h) in rois:
            print(f"    - [{x}, {y}, {w}, {h}]")

    # --- OCR recognizer (se disponibile) ---
    ocr_cfg = OCRConfig(
        engine=str(v.get("ocr_engine", "tesseract")),
        tesseract_psm=int(v.get("tesseract_psm", 10)),
        whitelist=str(v.get("whitelist", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        min_confidence=float(v.get("min_confidence", 40)),
    )
    recognizer = LetterRecognizer(ocr_cfg)

    # --- leggi 5 slot ---
    occ_flags = []
    occ_scores = []
    chars = []
    ocr_confs = []

    # Soglia occupancy (euristica). Se vuoi, puoi cambiarla:
    # Più alta => meno "falsi pieni". Più bassa => più sensibile.
    OCC_T = 125.0

    for i, (x, y, w, h) in enumerate(rois):
        patch = topdown[y:y+h, x:x+w].copy()
        cv2.imwrite(os.path.join(args.outdir, f"slot{i}.png"), patch)

        score = occupancy_heuristic(patch)
        occ = score > OCC_T

        occ_flags.append(occ)
        occ_scores.append(score)

        if not occ:
            chars.append(" ")
            ocr_confs.append(100.0)
            continue

        ch, conf, pre = recognizer.recognize(patch)
        chars.append(ch)
        ocr_confs.append(conf)

        if pre is not None:
            cv2.imwrite(os.path.join(args.outdir, f"slot{i}_pre.png"), pre)

    out_str = "".join(chars)

    overlay = draw_overlay(topdown, rois, occ_flags, occ_scores, out_str, ocr_confs)
    cv2.imwrite(os.path.join(args.outdir, "topdown_debug.png"), overlay)

    print("\n=== OFFLINE RESULT ===")
    print("STRING:", repr(out_str))
    print(f"Saved debug to: {args.outdir}")
    print(" - topdown.png, debug.png, topdown_debug.png, slot*.png, slot*_pre.png (se OCR)")

    if not recognizer.available() and ocr_cfg.engine.lower() == "tesseract":
        print("\nNOTE: pytesseract/tesseract non disponibile su questa postazione.")
        print("Vedrai '?' al posto delle lettere, ma occupancy + preprocess vengono comunque salvati.")


if __name__ == "__main__":
    main()
