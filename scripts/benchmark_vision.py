import sys
import os

# --- PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.append(project_root)
# ----------------

import cv2
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
from src.cnn_classifier import SlotClassifierCNN, CNNConfig

def run_vision_benchmark():
    cfg = CNNConfig(model_dir="data/models/cnn_savedmodel")
    classifier = SlotClassifierCNN(cfg)
    if not classifier.load():
        print("❌ Model not found!")
        return

    dataset_path = "data/dataset_augmented"
    classes = ["_"] + [chr(ord("A") + i) for i in range(26)]
    y_true, y_pred = [], []

    print(f"📊 Benchmarking Vision System (Dataset: {dataset_path})...")

    for label in classes:
        folder_name = label 
        folder_path = os.path.join(dataset_path, folder_name)
        if not os.path.exists(folder_path): continue
        
        # DEBUG: Count images
        images = os.listdir(folder_path)
        if label == "_": print(f"👀 FOUND {len(images)} images in EMPTY folder")

        for img_name in images:
            img_path = os.path.join(folder_path, img_name)
            img = cv2.imread(img_path)
            if img is None: continue
            
            pred_char, conf, _ = classifier.predict(img)
            
            # Normalize predictions for Empty class
            if pred_char == " " or pred_char == "?": pred_char = "_"
            
            y_true.append(label)
            y_pred.append(pred_char)

    print("\n" + "="*40 + "\nVISION PERFORMANCE REPORT\n" + "="*40)
    print(classification_report(y_true, y_pred, labels=classes, zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=classes)
    plt.figure(figsize=(14, 11))
    sns.heatmap(cm, annot=True, fmt='d', xticklabels=classes, yticklabels=classes, cmap='Blues')
    plt.xlabel('Predicted'); plt.ylabel('Actual'); plt.title('CNN Vision Confusion Matrix')
    
    output_path = 'data/test_logs/vision_confusion_matrix.png'
    os.makedirs('data/test_logs', exist_ok=True)
    plt.savefig(output_path)
    print(f"\n✅ Graph saved to: {output_path}")
    plt.show()

if __name__ == "__main__":
    run_vision_benchmark()