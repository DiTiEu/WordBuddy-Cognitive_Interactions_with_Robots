import os
from dataclasses import dataclass
from typing import Tuple, Optional, List
import cv2
import numpy as np
import tensorflow as tf

CLASSES: List[str] = ["_"] + [chr(ord("A") + i) for i in range(26)]

@dataclass
class CNNConfig:
    model_dir: str = "data/models/cnn_savedmodel"
    input_size: int = 64
    grayscale: bool = True
    min_confidence: float = 0.25
    return_unknown_as_empty: bool = True
    use_empty_heuristic: bool = True
    empty_center_mean_thresh: float = 85.0
    empty_center_size: int = 20
    verbose_load: bool = False

class SlotClassifierCNN:
    def __init__(self, cfg: CNNConfig):
        self.cfg = cfg
        self.model = None

    def load(self) -> bool:
        if not os.path.exists(self.cfg.model_dir): return False
        try:
            self.model = tf.keras.models.load_model(self.cfg.model_dir)
            if self.cfg.verbose_load: print(f"[CNN] Loaded: {self.cfg.model_dir}")
            return True
        except Exception as e:
            print(f"[CNN] Error: {e}")
            return False

    def _preprocess(self, slot_bgr: np.ndarray) -> np.ndarray:
        S = int(self.cfg.input_size)
        img = cv2.resize(slot_bgr, (S, S), interpolation=cv2.INTER_AREA)
        if self.cfg.grayscale:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            img = img.astype(np.float32) / 255.0
            img = img[:, :, None]
        else:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img = img.astype(np.float32) / 255.0
        return img

    def _is_empty(self, pre: np.ndarray) -> bool:
        if not self.cfg.use_empty_heuristic: return False
        S = pre.shape[0]
        half = int(self.cfg.empty_center_size // 2)
        cx, cy = S // 2, S // 2
        center = pre[cy-half:cy+half, cx-half:cx+half, :]
        return float(np.mean(center) * 255.0) < float(self.cfg.empty_center_mean_thresh)

    def predict(self, slot_bgr: np.ndarray) -> Tuple[str, float, Optional[np.ndarray]]:
        if self.model is None:
            if not self.load(): return "?", 0.0, None

        pre = self._preprocess(slot_bgr)
        if self._is_empty(pre): return " ", 100.0, (pre[:,:,0]*255).astype(np.uint8)

        x = np.expand_dims(pre, axis=0)
        probs = self.model.predict(x, verbose=0)[0]
        class_idx = int(np.argmax(probs))
        conf = float(probs[class_idx])
        pred = CLASSES[class_idx]

        if conf < float(self.cfg.min_confidence): pred = "?"
        if pred == "_" or (pred == "?" and self.cfg.return_unknown_as_empty): output = " "
        else: output = pred

        return output, conf * 100.0, (pre[:,:,0]*255).astype(np.uint8)