# src/board_vision.py
# si occupa di: warp top-down, estrazione slot ROI, occupancy, orchestrazione OCR

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import cv2
import numpy as np

from src.letter_recognition import LetterRecognizer, OCRConfig


# ----------------------------
# Helpers
# ----------------------------
def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def order_points_quad(pts: np.ndarray) -> np.ndarray:
    """Ordina 4 punti come [TL, TR, BR, BL]."""
    pts = pts.astype(np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]
    return np.array([tl, tr, br, bl], dtype=np.float32)


def get_aruco_dict(name: str):
    if not hasattr(cv2.aruco, name):
        raise ValueError(f"Unknown ArUco dict name: {name}")
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))


# ----------------------------
# Warper
# ----------------------------

# Input: dizionario ArUco, IDs, dimensione output top-down
# Output: solo un contenitore di parametri
@dataclass
class WarpConfig:
    aruco_dict: str
    aruco_ids: List[int]
    warp_size_px: Tuple[int, int]  # (W, H) output finale desiderato
    rotate: str = "NONE"           # "NONE" | "CW90" | "CCW90" | "180"


# Scopo: trasformare l’immagine originale in una immagine top-down stabile.
# Input: frame_bgr (immagine originale BGR, da camera o file)
# Output: topdown_bgr: immagine raddrizzata, dimensione fissa (W×H), debug_dict: info per disegnare overlay (corner marker, ids, punti usati)
class BoardWarper:
    """
    Trova 4 marker ArUco e fa warpPerspective (vista top-down).
    Strategia robusta: per ogni marker prende il corner più lontano dal centro globale (outer corner).

    Supporta anche rotazione della topdown (es. 90° CW) tramite cfg.rotate_topdown.
    """

    def __init__(self, cfg: WarpConfig):
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("cv2.aruco not found. Install opencv-contrib-python.")
        self.cfg = cfg
        aruco_dict = get_aruco_dict(cfg.aruco_dict)

        params = cv2.aruco.DetectorParameters()
        params.adaptiveThreshWinSizeMin = 3
        params.adaptiveThreshWinSizeMax = 53
        params.adaptiveThreshWinSizeStep = 4
        params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        params.cornerRefinementWinSize = 5
        params.cornerRefinementMaxIterations = 30
        params.cornerRefinementMinAccuracy = 0.1
        params.minMarkerPerimeterRate = 0.02
        params.maxMarkerPerimeterRate = 4.0

        self.detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    def warp(self, frame_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Output finale: topdown con dimensione (W_out, H_out) = cfg.warp_size_px.
        Se rotate_topdown è CW90/CCW90, il warp viene fatto prima su dimensioni scambiate,
        poi ruotato, così l'output finale resta coerente con warp_size_px.
        """
        W_out, H_out = self.cfg.warp_size_px
        rot = (self.cfg.rotate or "NONE").upper()

        debug: Dict[str, Any] = {}

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        corners, ids, _ = self.detector.detectMarkers(gray)
        if ids is None or len(ids) < 4:
            raise RuntimeError("Detected <4 markers. Check visibility/dict/ids.")

        ids_list = ids.flatten().tolist()
        required = set(self.cfg.aruco_ids)

        marker_data = []
        for i, mid in enumerate(ids_list):
            if mid in required:
                pts = corners[i].reshape(4, 2).astype(np.float32)
                center = pts.mean(axis=0)
                marker_data.append((mid, pts, center))

        if len(marker_data) != 4:
            found = sorted([m[0] for m in marker_data])
            raise RuntimeError(
                f"Need exactly 4 required markers. Found {found}, required {sorted(required)}."
            )

        global_center = np.mean([m[2] for m in marker_data], axis=0)

        board_pts = []
        for (_mid, pts, _c) in marker_data:
            d = np.linalg.norm(pts - global_center[None, :], axis=1)
            outer = pts[np.argmax(d)]
            board_pts.append(outer)

        src_quad = order_points_quad(np.array(board_pts, dtype=np.float32))

        # --- Dimensioni del warp PRIMA della rotazione ---
        # Se ruoto di 90° (CW/CCW) devo warpare su (H_out, W_out) così dopo la rotazione torno a (W_out, H_out)
        if rot in ("CW90", "CCW90"):
            W_warp, H_warp = H_out, W_out
        else:
            W_warp, H_warp = W_out, H_out

        dst_quad = np.array(
            [[0, 0], [W_warp - 1, 0], [W_warp - 1, H_warp - 1], [0, H_warp - 1]],
            dtype=np.float32,
        )

        M = cv2.getPerspectiveTransform(src_quad, dst_quad)
        topdown = cv2.warpPerspective(frame_bgr, M, (W_warp, H_warp))

        # --- Rotazione finale (se richiesta) ---
        if rot == "CW90":
            topdown = cv2.rotate(topdown, cv2.ROTATE_90_CLOCKWISE)
        elif rot == "CCW90":
            topdown = cv2.rotate(topdown, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rot == "180":
            topdown = cv2.rotate(topdown, cv2.ROTATE_180)
        # rot == "NONE" -> niente

        debug["corners"] = corners
        debug["ids"] = ids
        debug["src_quad"] = src_quad
        debug["M"] = M
        debug["rotate"] = rot
        debug["warp_size_px_out"] = (W_out, H_out)
        debug["warp_size_px_internal"] = (W_warp, H_warp)
        return topdown, debug

    def draw_debug(self, frame_bgr: np.ndarray, dbg: Dict[str, Any]) -> np.ndarray:
        img = frame_bgr.copy()
        corners = dbg.get("corners", None)
        ids = dbg.get("ids", None)
        src_quad = dbg.get("src_quad", None)

        if corners is not None and ids is not None:
            cv2.aruco.drawDetectedMarkers(img, corners, ids)

        if src_quad is not None:
            for p in src_quad.astype(int):
                cv2.circle(img, tuple(p), 10, (0, 0, 255), -1)
            cv2.polylines(img, [src_quad.astype(int)], True, (0, 0, 255), 3)

        return img



# ----------------------------
# Config + Main Vision
# ----------------------------
@dataclass
class VisionConfig:
    camera_id: int
    warp: WarpConfig
    slots_roi_px: List[Tuple[int, int, int, int]]  # 5 ROI (x,y,w,h)

    # occupancy
    use_bg_subtraction: bool
    occ_threshold: float

    # OCR
    ocr: OCRConfig

    calibration_dir: str = "data/calibration"
    logs_dir: str = "data/test_logs"


# API unica per leggere la board come stringa di 5 char.
class BoardVision:
    """
    API:
      - read_from_image(path) -> stringa 5 char (spazio per vuoto)
      - read_from_frame(frame) -> idem
      - capture_frame() -> frame dalla camera
    """

    def __init__(self, cfg: VisionConfig):
        if len(cfg.slots_roi_px) not in (0, 5):
            raise ValueError("slots_roi_px must be empty (not calibrated yet) or have exactly 5 ROIs.")
        self.cfg = cfg
        self.warper = BoardWarper(cfg.warp)

        self._bg_topdown: Optional[np.ndarray] = None
        self._bg_slots: Optional[List[np.ndarray]] = None

        self.recognizer = LetterRecognizer(cfg.ocr)

    # -------- I/O --------
    def capture_frame(self) -> np.ndarray:
        cap = cv2.VideoCapture(self.cfg.camera_id)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera id={self.cfg.camera_id}")
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            raise RuntimeError("Failed to capture frame")
        return frame

    def load_background(self) -> bool:
        bg_path = os.path.join(self.cfg.calibration_dir, "board_bg.png")
        if not os.path.exists(bg_path):
            return False
        bg = cv2.imread(bg_path)
        if bg is None:
            return False
        self._bg_topdown = bg
        self._bg_slots = self._extract_slots(bg)
        return True

    # -------- core --------
    def _extract_slots(self, topdown_bgr: np.ndarray) -> List[np.ndarray]:
        patches = []
        for (x, y, w, h) in self.cfg.slots_roi_px:
            patches.append(topdown_bgr[y:y + h, x:x + w].copy())
        return patches

    def _occupied_flags(self, slot_patches: List[np.ndarray]) -> Tuple[List[bool], List[float]]:
        flags, scores = [], []

        if self.cfg.use_bg_subtraction and self._bg_slots is None:
            self.load_background()

        for i, patch in enumerate(slot_patches):
            g = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY)

            if self.cfg.use_bg_subtraction and self._bg_slots is not None:
                bg = cv2.cvtColor(self._bg_slots[i], cv2.COLOR_BGR2GRAY)
                diff = cv2.absdiff(g, bg)
                score = float(np.mean(diff))
                occ = score > self.cfg.occ_threshold
            else:
                edges = cv2.Canny(g, 60, 120)
                score = float(np.mean(edges > 0)) * 100.0
                occ = score > 1.5

            flags.append(occ)
            scores.append(score)

        return flags, scores

    def read_from_frame(self, frame_bgr: np.ndarray, save_debug: bool = True) -> str:
        if len(self.cfg.slots_roi_px) != 5:
            raise RuntimeError("slots_roi_px not set. Run calibration script first.")

        topdown, dbg = self.warper.warp(frame_bgr)
        slots = self._extract_slots(topdown)

        flags, occ_scores = self._occupied_flags(slots)

        chars: List[str] = []
        ocr_confs: List[float] = []
        pre_imgs: List[Optional[np.ndarray]] = []

        for i in range(5):
            if not flags[i]:
                chars.append(" ")
                ocr_confs.append(100.0)
                pre_imgs.append(None)
                continue

            if self.cfg.ocr.engine.lower() == "none":
                chars.append("X")  # fallback
                ocr_confs.append(0.0)
                pre_imgs.append(None)
                continue

            ch, conf, pre = self.recognizer.recognize(slots[i])
            chars.append(ch)
            ocr_confs.append(conf)
            pre_imgs.append(pre)

        out = "".join(chars)

        if save_debug:
            ensure_dir(self.cfg.logs_dir)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "topdown.png"), topdown)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "debug.png"), self.warper.draw_debug(frame_bgr, dbg))
            dbg_top = self._draw_slots_and_scores(topdown, flags, occ_scores, out, ocr_confs)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "topdown_debug.png"), dbg_top)

            # salva anche le 5 preprocessed (se OCR)
            for i, pre in enumerate(pre_imgs):
                if pre is not None:
                    cv2.imwrite(os.path.join(self.cfg.logs_dir, f"slot{i}_pre.png"), pre)

        return out

    # Input: path ad una JPEG/PNG
    # Output: stringa di 5 caratteri (es "G A T ", spazi inclusi)
    def read_from_image(self, image_path: str, save_debug: bool = True) -> str:
        img = cv2.imread(image_path)
        if img is None:
            raise RuntimeError(f"Cannot read image: {image_path}")
        return self.read_from_frame(img, save_debug=save_debug)

    def _draw_slots_and_scores(self, topdown_bgr: np.ndarray, flags, occ_scores, out: str, ocr_confs: List[float]) -> np.ndarray:
        img = topdown_bgr.copy()
        for i, (x, y, w, h) in enumerate(self.cfg.slots_roi_px):
            color = (0, 255, 0) if flags[i] else (0, 0, 255)
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)

            # testo: slot, char, occ score, ocr conf
            txt = f"{i}: '{out[i]}' occ={occ_scores[i]:.1f} ocr={ocr_confs[i]:.0f}"
            cv2.putText(img, txt, (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        return img


def build_board_vision_from_config_dict(cfg: dict) -> BoardVision:
    """
    Costruisce BoardVision leggendo dal dict YAML.
    Usa board_size_mm e px_per_mm per calcolare warp_size_px coerente con il foglio reale.
    """
    v = cfg.get("vision", {})

    # ---- warp size coerente col foglio reale ----
    board_mm = v.get("board_size_mm", [260, 200])  # [W_mm, H_mm]
    px_per_mm = float(v.get("px_per_mm", 4))
    W_px = int(round(float(board_mm[0]) * px_per_mm))
    H_px = int(round(float(board_mm[1]) * px_per_mm))

    warp = WarpConfig(
        aruco_dict=v.get("aruco_dict", "DICT_4X4_50"),
        aruco_ids=list(map(int, v.get("aruco_ids", [0, 1, 2, 3]))),
        warp_size_px=(W_px, H_px),
        rotate=str(v.get("rotate_topdown", "NONE")),
    )

    slots_roi = v.get("slots_roi_px", [])
    slots_roi_px = [tuple(map(int, r)) for r in slots_roi] if slots_roi else []

    ocr = OCRConfig(
        engine=str(v.get("ocr_engine", "tesseract")),
        tesseract_psm=int(v.get("tesseract_psm", 10)),
        whitelist=str(v.get("whitelist", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")),
        min_confidence=float(v.get("min_confidence", 40)),
    )

    vc = VisionConfig(
        camera_id=int(cfg.get("camera_id", v.get("camera_id", 0))),
        warp=warp,
        slots_roi_px=slots_roi_px,
        use_bg_subtraction=bool(v.get("use_bg_subtraction", True)),
        occ_threshold=float(v.get("occ_threshold", 18)),
        ocr=ocr,
        calibration_dir="data/calibration",
        logs_dir="data/test_logs",
    )
    return BoardVision(vc)
