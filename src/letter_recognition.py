# src/letter_recognition.py
# si occupa di: preprocess della patch di slot e OCR (Tesseract) → lettera

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional

import cv2
import numpy as np


@dataclass
class OCRConfig:
    engine: str = "tesseract"  # "tesseract" | "none"
    tesseract_psm: int = 10
    whitelist: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    min_confidence: float = 40.0  # 0..100 (tesseract)


# Scopo: prendere una patch di slot occupato → estrarre la lettera.
class LetterRecognizer:
    """
    Riconosce una lettera (A-Z) da una patch slot (BGR).
    Pipeline:
      1) pre-processing robusto per isolare il "cerchio bianco"
      2) binarizzazione + normalizzazione
      3) OCR single-char con Tesseract (whitelist)
    """

    def __init__(self, cfg: OCRConfig):
        self.cfg = cfg
        self._tesseract = None

        if self.cfg.engine.lower() == "tesseract":
            try:
                import pytesseract  # type: ignore
                self._tesseract = pytesseract
            except Exception:
                self._tesseract = None

    def available(self) -> bool:
        return self.cfg.engine.lower() == "tesseract" and self._tesseract is not None

    # ---------- PREPROCESS ----------
    def _crop_white_disc(self, slot_bgr: np.ndarray) -> np.ndarray:
        """
        Cerca la regione più chiara (disco bianco) e croppa attorno.
        Se fallisce, ritorna la patch originale.
        """
        gray = cv2.cvtColor(slot_bgr, cv2.COLOR_BGR2GRAY)

        # soglia "bianco": robusta con Otsu + bias verso il chiaro
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # ci aspettiamo disco bianco -> th dovrebbe evidenziare area chiara
        # pulizia piccola
        th = cv2.morphologyEx(th, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

        contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return slot_bgr

        # prendo il contorno più grande
        cnt = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(cnt)
        h, w = gray.shape[:2]

        # se è troppo piccolo, meglio non fidarsi
        if area < 0.05 * (w * h):
            return slot_bgr

        x, y, bw, bh = cv2.boundingRect(cnt)

        # aggiungo un margine
        pad = int(0.08 * max(bw, bh))
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + bw + pad)
        y1 = min(h, y + bh + pad)

        return slot_bgr[y0:y1, x0:x1].copy()

    def preprocess(self, slot_bgr: np.ndarray) -> np.ndarray:
        """
        Output: immagine binaria normalizzata (uint8) pronta per Tesseract.
        Convenzione finale: testo scuro su sfondo chiaro.
        """
        crop = self._crop_white_disc(slot_bgr)
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # binarizzazione
        _, bin_img = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Tesseract di solito preferisce testo scuro su sfondo chiaro.
        # Se la binaria risulta "inversa" (molto nero), invertiamo.
        if np.mean(bin_img) < 127:
            bin_img = cv2.bitwise_not(bin_img)

        # chiusura leggera per rendere le stroke più continue
        bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

        # resize a dimensione standard
        bin_img = cv2.resize(bin_img, (128, 128), interpolation=cv2.INTER_AREA)
        return bin_img

    # ---------- OCR ----------
    def recognize(self, slot_bgr: np.ndarray) -> Tuple[str, float, Optional[np.ndarray]]:
        """
        Ritorna:
          - char: 'A'..'Z' oppure '?' se incerto
          - conf: confidence (0..100)
          - preprocessed image (per debug)
        """
        pre = self.preprocess(slot_bgr)

        if not self.available():
            return "?", 0.0, pre

        # Config tesseract: single char + whitelist
        tconf = f'--psm {self.cfg.tesseract_psm} -c tessedit_char_whitelist={self.cfg.whitelist}'

        # Usiamo image_to_data per avere confidence reale
        data = self._tesseract.image_to_data(pre, config=tconf, output_type=self._tesseract.Output.DICT)

        # Estrai il best token (conf più alta)
        best_char = ""
        best_conf = -1.0
        n = len(data.get("text", []))

        for i in range(n):
            txt = (data["text"][i] or "").strip().upper()
            try:
                conf = float(data["conf"][i])
            except Exception:
                conf = -1.0

            if len(txt) == 1 and txt in self.cfg.whitelist and conf > best_conf:
                best_char = txt
                best_conf = conf

        if best_conf < 0:
            return "?", 0.0, pre

        if best_conf < self.cfg.min_confidence:
            return "?", float(best_conf), pre

        return best_char, float(best_conf), pre
