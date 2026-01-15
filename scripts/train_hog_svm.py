# scripts/train_hog_svm.py
import os, sys, glob
import numpy as np
import cv2

from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from src.slot_classifier_hog_svm import SlotClassifierHOGSVM, HOGSVMConfig


CLASSES = ["_"] + [chr(ord("A") + i) for i in range(26)]


def list_images(dataset_root: str):
    items = []
    for c in CLASSES:
        d = os.path.join(dataset_root, c)
        if not os.path.isdir(d):
            continue
        for fp in glob.glob(os.path.join(d, "*.png")) + glob.glob(os.path.join(d, "*.jpg")):
            items.append((fp, c))
    return items


def main():
    dataset_root = "data/dataset_slots"
    model_path = "data/models/hog_svm.joblib"
    os.makedirs("data/models", exist_ok=True)

    items = list_images(dataset_root)
    if len(items) < 200:
        raise RuntimeError(f"Pochi dati: trovati {len(items)} file. Raccogli più campioni con collect_dataset_slots.py")

    cfg = HOGSVMConfig(model_path=model_path, input_size=96)
    extractor = SlotClassifierHOGSVM(cfg)

    X, y = [], []
    for fp, c in items:
        img = cv2.imread(fp)
        if img is None:
            continue
        pre = extractor._preprocess(img)
        feat = extractor._hog(pre)
        X.append(feat)
        y.append(c)

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y)

    # split semplice (poi possiamo fare split "per sessione" se aggiungi group id nel nome)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    base = LinearSVC(C=2.0)
    clf = CalibratedClassifierCV(base, method="sigmoid", cv=3)
    clf.fit(Xtr, ytr)

    pred = clf.predict(Xte)
    print("\n=== REPORT (test split) ===")
    print(classification_report(yte, pred, labels=CLASSES))

    # salva bundle
    bundle = {
        "clf": clf,
        "classes": CLASSES,
        "input_size": cfg.input_size,
    }
    joblib.dump(bundle, model_path)
    print(f"\n✅ Salvato modello: {model_path}")


if __name__ == "__main__":
    main()
