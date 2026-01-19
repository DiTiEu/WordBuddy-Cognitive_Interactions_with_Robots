import os
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
from src.cnn_classifier import SlotClassifierCNN, CNNConfig

def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)

def order_points_quad(pts: np.ndarray) -> np.ndarray:
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

@dataclass
class WarpConfig:
    aruco_dict: str
    aruco_ids: List[int]
    warp_size_px: Tuple[int, int]
    rotate: str = "NONE"

@dataclass
class VisionConfig:
    camera_id: int
    warp: WarpConfig
    slots_roi_px: List[Tuple[int, int, int, int]]
    classifier_model_path: str = "data/models/cnn_savedmodel"
    classifier_min_conf: float = 0.40
    calibration_dir: str = "data/calibration"
    logs_dir: str = "data/test_logs"

class BoardWarper:
    def __init__(self, cfg: WarpConfig):
        if not hasattr(cv2, "aruco"):
            raise RuntimeError("cv2.aruco not found.")
        self.cfg = cfg
        self.aruco_dict = get_aruco_dict(cfg.aruco_dict)
        self.params = cv2.aruco.DetectorParameters_create()
        self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        try:
            self.params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
            self.params.minMarkerPerimeterRate = 0.02
        except Exception: pass

    def _preprocess_variants(self, frame_bgr: np.ndarray) -> List[np.ndarray]:
        gray0 = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        v1 = self._clahe.apply(gray0)
        v2 = cv2.GaussianBlur(v1, (3, 3), 0)
        return [gray0, v1, v2]

    def _best_detection(self, frame_bgr: np.ndarray):
        required = set(self.cfg.aruco_ids)
        scales = [1.0, 1.25, 1.5]
        best = None
        for s in scales:
            frame_s = cv2.resize(frame_bgr, None, fx=s, fy=s) if s != 1.0 else frame_bgr
            for gray in self._preprocess_variants(frame_s):
                corners, ids, rejected = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.params)
                found_req = len(set(ids.flatten().tolist()).intersection(required)) if ids is not None else 0
                if best is None or found_req > best[0]:
                    best = (found_req, corners, ids, s)
                if found_req >= 4: return corners, ids, rejected, s
        return best[1], best[2], None, best[3]

    def warp(self, frame_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        W_out, H_out = self.cfg.warp_size_px
        rot = (self.cfg.rotate or "NONE").upper()
        
        corners, ids, _, scale_used = self._best_detection(frame_bgr)
        if ids is None: raise RuntimeError("No markers detected.")
        
        required = set(self.cfg.aruco_ids)
        marker_data = []
        for i, mid in enumerate(ids.flatten().tolist()):
            if mid in required:
                pts = corners[i].reshape(4, 2).astype(np.float32)
                marker_data.append((mid, pts, pts.mean(axis=0)))

        if len(marker_data) != 4: raise RuntimeError("Not all markers found.")

        if scale_used != 1.0:
            inv_s = 1.0 / scale_used
            marker_data = [(mid, pts * inv_s, c * inv_s) for (mid, pts, c) in marker_data]

        global_center = np.mean([m[2] for m in marker_data], axis=0)
        board_pts = [pts[np.argmax(np.linalg.norm(pts - global_center, axis=1))] for (_, pts, _) in marker_data]
        src_quad = order_points_quad(np.array(board_pts, dtype=np.float32))

        W_warp, H_warp = (H_out, W_out) if rot in ("CW90", "CCW90") else (W_out, H_out)
        dst_quad = np.array([[0, 0], [W_warp-1, 0], [W_warp-1, H_warp-1], [0, H_warp-1]], dtype=np.float32)
        M = cv2.getPerspectiveTransform(src_quad, dst_quad)
        topdown = cv2.warpPerspective(frame_bgr, M, (W_warp, H_warp))
        
        if rot == "CW90": topdown = cv2.rotate(topdown, cv2.ROTATE_90_CLOCKWISE)
        elif rot == "CCW90": topdown = cv2.rotate(topdown, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif rot == "180": topdown = cv2.rotate(topdown, cv2.ROTATE_180)

        return topdown, {}

class BoardVision:
    def __init__(self, cfg: VisionConfig):
        self.cfg = cfg
        self.warper = BoardWarper(cfg.warp)
        self.classifier = SlotClassifierCNN(CNNConfig(model_dir=cfg.classifier_model_path))

    def capture_frame(self) -> np.ndarray:
        cap = cv2.VideoCapture(self.cfg.camera_id)
        if not cap.isOpened(): raise RuntimeError(f"Cannot open camera {self.cfg.camera_id}")
        frame = None
        for _ in range(6): 
            ok, f = cap.read()
            if ok: frame = f
        cap.release()
        return frame

    def read_from_frame(self, frame_bgr: np.ndarray, save_debug: bool = True) -> str:
        topdown, _ = self.warper.warp(frame_bgr)
        slots = [topdown[y:y+h, x:x+w].copy() for (x, y, w, h) in self.cfg.slots_roi_px]
        chars = []
        for slot in slots:
            ch, _, _ = self.classifier.predict(slot)
            chars.append(ch)
        
        if save_debug:
            ensure_dir(self.cfg.logs_dir)
            cv2.imwrite(os.path.join(self.cfg.logs_dir, "last_topdown.png"), topdown)
        return "".join(chars)

def build_board_vision_from_config_dict(cfg: dict) -> BoardVision:
    v = cfg.get("vision", {})
    px_mm = float(v.get("px_per_mm", 4))
    warp_size = (int(v["board_size_mm"][0] * px_mm), int(v["board_size_mm"][1] * px_mm))
    vc = VisionConfig(
        camera_id=v.get("camera_id", 0),
        warp=WarpConfig(aruco_dict=v.get("aruco_dict", "DICT_4X4_50"), aruco_ids=v.get("aruco_ids", [0,1,2,3]), warp_size_px=warp_size, rotate=v.get("rotate_topdown", "NONE")),
        slots_roi_px=[tuple(r) for r in v.get("slots_roi_px", [])]
    )
    return BoardVision(vc)