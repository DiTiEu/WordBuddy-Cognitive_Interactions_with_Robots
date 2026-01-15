# src/slot_classifier_hog_svm.py
import os
from dataclasses import dataclass
from typing import Tuple, Optional, List

import cv2
import numpy as np

try:
    import joblib
except Exception:
    joblib = None


@dataclass
class HOGSVMConfig:
    model_path: str = "data/models/hog_svm.joblib"

    # Preprocess / features
    input_size: int = 96

    # Maschera circolare (opzionale)
    use_circular_mask: bool = False
    mask_radius_frac: float = 0.42  # usata solo se use_circular_mask=True

    # Confidence gating (0..1)
    min_confidence: float = 0.55

    # Output behavior
    return_unknown_as_empty: bool = True  # per debug metti False e vedi '?'

    # Euristica EMPTY (fortemente consigliata)
    use_empty_heuristic: bool = True
    empty_center_mean_thresh: float = 85.0  # 70-100 da tarare
    empty_center_size: int = 20             # px nel preprocessed (96x96)

    # Debug
    verbose_load: bool = False


class SlotClassifierHOGSVM:
    """
    Classificatore per-slot: 27 classi ('_' + 'A'..'Z') basato su HOG + SVM calibrato (predict_proba).
    """

    def __init__(self, cfg: HOGSVMConfig):
        self.cfg = cfg
        self.bundle = None
        self.clf = None
        self.classes: List[str] = []
        self.input_size = int(cfg.input_size)

    def load(self) -> bool:
        if joblib is None:
            raise RuntimeError("joblib not available. Install: pip install joblib")
        if not os.path.exists(self.cfg.model_path):
            return False

        self.bundle = joblib.load(self.cfg.model_path)
        self.clf = self.bundle["clf"]
        self.classes = list(self.bundle["classes"])
        self.input_size = int(self.bundle.get("input_size", self.cfg.input_size))

        if self.cfg.verbose_load:
            print("[HOGSVM] Loaded:", self.cfg.model_path)
            print("[HOGSVM] classes n=", len(self.classes))

        return True

    # ----------------------------
    # Preprocess (leggero, stabile)
    # ----------------------------
    def _preprocess(self, slot_bgr: np.ndarray) -> np.ndarray:
        """
        Pipeline base:
          - grayscale
          - CLAHE leggero
          - resize a input_size
          - opzionale: maschera circolare (se abilitata)
        """
        gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        S = int(self.input_size)
        gray = cv2.resize(gray, (S, S), interpolation=cv2.INTER_AREA)

        if self.cfg.use_circular_mask:
            cx, cy = S // 2, S // 2
            r = int(S * float(self.cfg.mask_radius_frac))
            mask = np.zeros((S, S), dtype=np.uint8)
            cv2.circle(mask, (cx, cy), r, 255, -1)

            inside = gray[mask == 255]
            mean_val = int(np.mean(inside)) if inside.size > 0 else 127
            out = gray.copy()
            out[mask == 0] = mean_val
            return out

        return gray

    def _is_empty_by_center(self, pre_gray: np.ndarray) -> bool:
        if not self.cfg.use_empty_heuristic:
            return False

        S = pre_gray.shape[0]
        half = int(self.cfg.empty_center_size // 2)
        cx = S // 2
        cy = S // 2

        x0 = max(0, cx - half)
        x1 = min(S, cx + half)
        y0 = max(0, cy - half)
        y1 = min(S, cy + half)

        center = pre_gray[y0:y1, x0:x1]
        m = float(np.mean(center))

        return m < float(self.cfg.empty_center_mean_thresh)

    # ----------------------------
    # HOG
    # ----------------------------
    def _hog(self, gray_2d: np.ndarray) -> np.ndarray:
        S = gray_2d.shape[0]
        winSize = (S, S)
        blockSize = (24, 24)
        blockStride = (12, 12)
        cellSize = (12, 12)
        nbins = 9

        hog = cv2.HOGDescriptor(winSize, blockSize, blockStride, cellSize, nbins)
        feat = hog.compute(gray_2d)
        return feat.reshape(-1).astype(np.float32)

    # ----------------------------
    # Predict
    # ----------------------------
    def predict(self, slot_bgr: np.ndarray) -> Tuple[str, float, Optional[np.ndarray]]:
        if self.clf is None:
            ok = self.load()
            if not ok:
                raise RuntimeError("Model not found at {}. Train it first.".format(self.cfg.model_path))

        pre = self._preprocess(slot_bgr)

        # Euristica vuoto: evita disastri sul cerchio nero
        if self._is_empty_by_center(pre):
            return " ", 100.0, pre

        feat = self._hog(pre)

        proba = self.clf.predict_proba([feat])[0]
        j = int(np.argmax(proba))
        conf01 = float(proba[j])
        pred = str(self.classes[j])  # '_' o 'A'..'Z'

        if conf01 < float(self.cfg.min_confidence):
            pred = "?"

        if pred == "_":
            out = " "
        elif pred == "?" and self.cfg.return_unknown_as_empty:
            out = " "
        else:
            out = pred

        return out, conf01 * 100.0, pre
