# src/board_vision.py
# Compiti:
# - Warp top-down tramite 4 ArUco marker (OpenCV 4.5.5 legacy API)
# - Estrazione delle 5 ROI degli slot
# - Classificazione per slot tramite HOG+SVM (27 classi: '_' + A..Z)
# - Debug logging (topdown + overlay + pre slot preprocess)

import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

import cv2
import numpy as np

from src.cnn_classifier import SlotClassifierCNN, CNNConfig


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
        raise ValueError("Unknown ArUco dict name: {}".format(name))
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))


# ----------------------------
# Config dataclasses
# ----------------------------
@dataclass
class WarpConfig:
    aruco_dict: str
    aruco_ids: List[int]
    warp_size_px: Tuple[int, int]  # (W, H)
    rotate: str = "NONE"           # "NONE" | "CW90" | "CCW90" | "180"


@dataclass
class VisionConfig:
    camera_id: int
    warp: WarpConfig
    slots_roi_px: List[Tuple[int, int, int, int]]  # 5 ROI (x,y,w,h)

    # Classifier CNN
    classifier_model_path: str = "data/models/cnn_savedmodel"
    classifier_min_conf: float = 0.40


    # I/O dirs
    calibration_dir: str = "data/calibration"
    logs_dir: str = "data/test_logs"


# ----------------------------
# Warper (robusto, OpenCV 4.5.5 legacy)
# ----------------------------
class BoardWarper:
    """
    Warper top-down usando 4 marker ArUco (OpenCV 4.5.5 legacy API).
    Robusto:
      - prova più preprocess (gray, CLAHE, blur)
      - prova più scale (upscale) per marker piccoli
    Strategia corner:
      - per ogni marker prende il corner più lontano dal centro globale (outer corner)
    """

    def __init__(self, cfg: WarpConfig):
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("cv2.aruco not found. Install opencv-contrib-python.")
        self.cfg = cfg
        self.aruco_dict = get_aruco_dict(cfg.aruco_dict)

        # legacy params
        self.params = cv2.aruco.DetectorParameters_create()
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

        # tuning (safe)
        try:
            self.params.adaptiveThreshWinSizeMin = 3
            self.params.adaptiveThreshWinSizeMax = 75
            self.params.adaptiveThreshWinSizeStep = 6
        except Exception:
            pass

        try:
            self.params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self.params.cornerRefinementWinSize = 7
            self.params.cornerRefinementMaxIterations = 50
            self.params.cornerRefinementMinAccuracy = 0.01
        except Exception:
            pass

        try:
            self.params.minMarkerPerimeterRate = 0.02
            self.params.maxMarkerPerimeterRate = 4.0
        except Exception:
            pass

    def _preprocess_variants(self, frame_bgr: np.ndarray) -> List[np.ndarray]:
        gray0 = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        v1 = self._clahe.apply(gray0)
        v2 = cv2.GaussianBlur(v1, (3, 3), 0)
        v3 = cv2.GaussianBlur(gray0, (5, 5), 0)
        return [gray0, v1, v2, v3]

    def _best_detection(self, frame_bgr: np.ndarray):
        required = set(self.cfg.aruco_ids)
        scales = [1.0, 1.25, 1.5, 1.75]

        best = None  # (found_required, corners, ids, rejected, scale)
        for s in scales:
            if s != 1.0:
                frame_s = cv2.resize(frame_bgr, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
            else:
                frame_s = frame_bgr

            for gray in self._preprocess_variants(frame_s):
                corners, ids, rejected = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.params)

                if ids is None:
                    found_required = 0
                else:
                    found_ids = set(ids.flatten().tolist())
                    found_required = len(found_ids.intersection(required))

                cand = (found_required, corners, ids, rejected, s)
                if best is None or cand[0] > best[0]:
                    best = cand

                if found_required >= 4:
                    return corners, ids, rejected, s

        if best is None:
            raise RuntimeError("No markers detected at all.")
        return best[1], best[2], best[3], best[4]

    def warp(self, frame_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        W_out, H_out = self.cfg.warp_size_px
        rot = (self.cfg.rotate or "NONE").upper()
        dbg: Dict[str, Any] = {}

        corners, ids, rejected, scale_used = self._best_detection(frame_bgr)
        if ids is None:
            raise RuntimeError("Detected 0 markers. Check visibility/dict/ids.")

        required = set(self.cfg.aruco_ids)
        ids_list = ids.flatten().tolist()

        marker_data = []
        for i, mid in enumerate(ids_list):
            if mid in required:
                pts = corners[i].reshape(4, 2).astype(np.float32)
                center = pts.mean(axis=0)
                marker_data.append((mid, pts, center))

        if len(marker_data) != 4:
            found = sorted([m[0] for m in marker_data])
            raise RuntimeError(
                "Detected <4 required markers. Found {}, required {}. (scale_used={})"
                .format(found, sorted(required), scale_used)
            )

        # rescale back to original coordinates if needed
        if scale_used != 1.0:
            inv_s = 1.0 / float(scale_used)
            marker_data = [(mid, pts * inv_s, c * inv_s) for (mid, pts, c) in marker_data]

        global_center = np.mean([m[2] for m in marker_data], axis=0)

        board_pts = []
        for (_mid, pts, _c) in marker_data:
            d = np.linalg.norm(pts - global_center[None, :], axis=1)
            outer = pts[np.argmax(d)]
            board_pts.append(outer)

        src_quad = order_points_quad(np.array(board_pts, dtype=np.float32))

        # warp size before rotation
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

        if rot == "CW90":
            topdown = cv2.rotate(topdown, cv2.ROTATE_90_CLOCKWISE)
        elif rot == "CCW90":
            topdown = cv2.rotate(topdown, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rot == "180":
            topdown = cv2.rotate(topdown, cv2.ROTATE_180)

        dbg["corners"] = corners
        dbg["ids"] = ids
        dbg["rejected"] = rejected
        dbg["src_quad"] = src_quad
        dbg["M"] = M
        dbg["rotate"] = rot
        dbg["scale_used"] = scale_used
        dbg["warp_size_px_out"] = (W_out, H_out)
        dbg["warp_size_px_internal"] = (W_warp, H_warp)
        return topdown, dbg

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
# Main Vision API
# ----------------------------
class BoardVision:
    """
    API:
      - capture_frame() -> frame BGR
      - read_from_frame(frame, save_debug=True) -> stringa 5 char (' ' per vuoto)
      - read_from_image(path, save_debug=True) -> idem
    """

    def __init__(self, cfg: VisionConfig):
        if len(cfg.slots_roi_px) not in (0, 5):
            raise ValueError("slots_roi_px must be empty or have exactly 5 ROIs.")
        self.cfg = cfg
        self.warper = BoardWarper(cfg.warp)

        self.classifier = SlotClassifierCNN(
            CNNConfig(
                model_dir=cfg.classifier_model_path,
                input_size=64,
                grayscale=True,
                min_confidence=cfg.classifier_min_conf,
                return_unknown_as_empty=True,
                use_empty_heuristic=True,
                empty_center_mean_thresh=85.0,
                empty_center_size=20,
                verbose_load=False,
            )
        )




    def capture_frame(self) -> np.ndarray:
        cap = cv2.VideoCapture(self.cfg.camera_id)
        if not cap.isOpened():
            raise RuntimeError("Cannot open camera id={}".format(self.cfg.camera_id))

        frame = None
        # prendi qualche frame e usa l'ultimo (aiuta esposizione/autofocus)
        for _ in range(6):
            ok, f = cap.read()
            if ok and f is not None:
                frame = f
        cap.release()

        if frame is None:
            raise RuntimeError("Failed to capture frame")
        return frame

    def _extract_slots(self, topdown_bgr: np.ndarray) -> List[np.ndarray]:
        patches = []
        for (x, y, w, h) in self.cfg.slots_roi_px:
            patches.append(topdown_bgr[y:y + h, x:x + w].copy())
        return patches

    def read_from_frame(self, frame_bgr: np.ndarray, save_debug: bool = True) -> str:
        if len(self.cfg.slots_roi_px) != 5:
            raise RuntimeError("slots_roi_px not set. Run calibration first.")

        topdown = None
        dbg = None
        last_err = None

        for attempt in range(10):
            try:
                topdown, dbg = self.warper.warp(frame_bgr)
                break
            except Exception as e:
                last_err = e
                # ricattura un frame (aiuta molto)
                frame_bgr = self.capture_frame()

        if topdown is None:
            raise RuntimeError("Warp failed after retries: {}".format(last_err))

        slots = self._extract_slots(topdown)

        chars: List[str] = []
        confs: List[float] = []
        pre_imgs: List[Optional[np.ndarray]] = []

        for i in range(5):
            ch, conf, pre = self.classifier.predict(slots[i])
            chars.append(ch)         # ' ' oppure 'A'..'Z'
            confs.append(conf)       # 0..100
            pre_imgs.append(pre)

        out = "".join(chars)

        if save_debug:
            ensure_dir(self.cfg.logs_dir)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "topdown.png"), topdown)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "debug.png"), self.warper.draw_debug(frame_bgr, dbg))
            dbg_top = self._draw_slots_overlay(topdown, out, confs)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "topdown_debug.png"), dbg_top)

            for i, pre in enumerate(pre_imgs):
                if pre is not None:
                    cv2.imwrite(os.path.join(self.cfg.logs_dir, "slot{}_pre.png".format(i)), pre)

        return out

    def read_from_image(self, image_path: str, save_debug: bool = True) -> str:
        img = cv2.imread(image_path)
        if img is None:
            raise RuntimeError("Cannot read image: {}".format(image_path))
        return self.read_from_frame(img, save_debug=save_debug)

    def _draw_slots_overlay(self, topdown_bgr: np.ndarray, out: str, confs: List[float]) -> np.ndarray:
        img = topdown_bgr.copy()
        for i, (x, y, w, h) in enumerate(self.cfg.slots_roi_px):
            occupied = (out[i] != " ")
            color = (0, 255, 0) if occupied else (0, 0, 255)
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            txt = "{}: '{}' conf={:.0f}".format(i, out[i], confs[i])
            cv2.putText(img, txt, (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
        return img


def build_board_vision_from_config_dict(cfg: dict) -> BoardVision:
    """
    Costruisce BoardVision leggendo dal dict YAML.
    Calcola warp_size_px da board_size_mm e px_per_mm.
    """
    v = cfg.get("vision", {})

    board_mm = v.get("board_size_mm", [260, 200])  # [W_mm, H_mm]
    px_per_mm = float(v.get("px_per_mm", 4))
    W_px = int(round(float(board_mm[0]) * px_per_mm))
    H_px = int(round(float(board_mm[1]) * px_per_mm))

    warp = WarpConfig(
        aruco_dict=str(v.get("aruco_dict", "DICT_4X4_50")),
        aruco_ids=list(map(int, v.get("aruco_ids", [0, 1, 2, 3]))),
        warp_size_px=(W_px, H_px),
        rotate=str(v.get("rotate_topdown", "NONE")),
    )

    slots_roi = v.get("slots_roi_px", [])
    slots_roi_px = [tuple(map(int, r)) for r in slots_roi] if slots_roi else []

    vc = VisionConfig(
        camera_id=int(cfg.get("camera_id", v.get("camera_id", 0))),
        warp=warp,
        slots_roi_px=slots_roi_px,
        classifier_model_path=str(v.get("classifier_model_path", "data/models/cnn_savedmodel")),
        classifier_min_conf=float(v.get("classifier_min_conf", 0.40)),
        calibration_dir="data/calibration",
        logs_dir="data/test_logs",
    )
    return BoardVision(vc)
