import os
import glob
import random
from collections import Counter

import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras import layers

# ----------------------------
# Config
# ----------------------------
DATASET_ROOT = "data/dataset_augmented"
MODEL_DIR = "data/models/cnn_savedmodel"

INPUT_SIZE = 64
GRAYSCALE = True

TEST_FRAC = 0.20
BATCH = 32          # Torniamo a 32 per stabilità
EPOCHS = 40
LR = 0.001          # Learning rate standard
SEED = 42

# --- AUGMENTATION STANDARD (Senza Rumore) ---
ROT_DEG = 15.0      
SHEAR = 0.10
SCALE_MIN = 0.90
SCALE_MAX = 1.10
SHIFT_PX = 6
BRIGHT = 0.20
CONTRAST = 0.20
SHADOW_PROB = 0.30  

CLASSES = ["_"] + [chr(ord("A") + i) for i in range(26)]
CLASS_TO_ID = {c: i for i, c in enumerate(CLASSES)}

random.seed(SEED)
np.random.seed(SEED)
tf.random.set_seed(SEED)


def list_files_for_class(c):
    d = os.path.join(DATASET_ROOT, c)
    if not os.path.isdir(d):
        return []
    fps = glob.glob(os.path.join(d, "*.png")) + glob.glob(os.path.join(d, "*.jpg"))
    return fps


def make_split_stratified():
    train_pairs, test_pairs = [], []
    
    # Bilanciamento: limitiamo i vuoti "_"
    letter_counts = [len(list_files_for_class(c)) for c in CLASSES if c != "_"]
    avg_letters = int(np.mean(letter_counts)) if letter_counts else 20
    max_empty = avg_letters * 4  # Un po' più permissivi sui vuoti

    for c in CLASSES:
        fps = list_files_for_class(c)
        if len(fps) == 0:
            continue
        
        random.shuffle(fps)

        if c == "_" and len(fps) > max_empty:
            fps = fps[:max_empty] 

        if len(fps) < 6:
            train_fps, test_fps = fps, []
        else:
            n_test = max(1, int(round(len(fps) * TEST_FRAC)))
            test_fps = fps[:n_test]
            train_fps = fps[n_test:]

        for fp in train_fps:
            train_pairs.append((fp, c))
        for fp in test_fps:
            test_pairs.append((fp, c))

    random.shuffle(train_pairs)
    random.shuffle(test_pairs)
    return train_pairs, test_pairs


def load_image_np(fp):
    img = cv2.imread(fp)
    if img is None:
        return None
    img = cv2.resize(img, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_AREA)

    if GRAYSCALE:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = img.astype(np.float32) / 255.0
        img = img[:, :, None]
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
    return img


def augment_np(img):
    h, w = img.shape[:2]
    
    # Geometric Augmentation
    angle = random.uniform(-ROT_DEG, ROT_DEG)
    scale = random.uniform(SCALE_MIN, SCALE_MAX)
    sh = random.uniform(-SHEAR, SHEAR)
    tx = random.randint(-SHIFT_PX, SHIFT_PX)
    ty = random.randint(-SHIFT_PX, SHIFT_PX)

    M = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, scale)
    M[0, 1] += sh
    M[0, 2] += tx
    M[1, 2] += ty

    x_uint = (img * 255.0).astype(np.uint8)
    fill = int(np.mean(x_uint))
    x_aug = cv2.warpAffine(x_uint, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=fill)

    x = x_aug.astype(np.float32) / 255.0
    if len(x.shape) == 2: x = x[:,:,None]

    # Pixel Augmentation (Soft)
    if random.random() < SHADOW_PROB:
        gx = np.linspace(random.uniform(0.6, 0.9), 1.0, w).astype(np.float32)
        mask = np.outer(np.ones(h, np.float32), gx)
        if random.random() < 0.5: mask = mask[:, ::-1]
        x = np.clip(x * mask[:,:,None], 0, 1)

    b = random.uniform(-0.10, 0.10)
    c = random.uniform(0.8, 1.2)
    x = x * c + b
    x = np.clip(x, 0.0, 1.0)

    return x.astype(np.float32)


def tf_load_and_aug(path, label, training):
    def _py_fn(p):
        fp = p.decode("utf-8")
        img = load_image_np(fp)
        if img is None:
            img = np.zeros((INPUT_SIZE, INPUT_SIZE, 1), dtype=np.float32)
        if training:
            img = augment_np(img)
        return img.astype(np.float32)

    img = tf.py_function(func=lambda p: _py_fn(p.numpy()), inp=[path], Tout=tf.float32)
    img.set_shape([INPUT_SIZE, INPUT_SIZE, 1])
    return img, label


def build_model(input_shape, num_classes):
    # --- MODELLO SENZA L2 REGULARIZATION ---
    inputs = layers.Input(shape=input_shape)

    x = layers.Conv2D(32, 3, padding="same")(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    x = layers.MaxPool2D()(x)

    x = layers.Conv2D(64, 3, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    x = layers.MaxPool2D()(x)

    x = layers.Conv2D(64, 3, padding="same")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation("relu")(x)
    x = layers.MaxPool2D()(x)
    
    x = layers.GlobalAveragePooling2D()(x)
    
    # Dropout ridotto a 0.25 (meno aggressivo)
    x = layers.Dropout(0.25)(x) 

    outputs = layers.Dense(num_classes, activation="softmax")(x)

    return tf.keras.Model(inputs, outputs)


def compute_class_weight(y_train):
    counts = Counter(y_train.tolist())
    total = float(len(y_train))
    w = {}
    for cls_id in range(len(CLASSES)):
        n = float(counts.get(cls_id, 0))
        if n > 0:
            w[cls_id] = total / (len(CLASSES) * n)
        else:
            w[cls_id] = 1.0
    
    # Clamp meno aggressivo
    vals = list(w.values())
    mean_w = np.mean(vals)
    for k in w:
        w[k] = min(w[k], mean_w * 4.0) 
        
    return w


def main():
    train_pairs, test_pairs = make_split_stratified()

    print(f"Train pairs: {len(train_pairs)}")
    print(f"Test pairs : {len(test_pairs)}")

    tr_paths = np.array([fp for fp, c in train_pairs], dtype=np.str_)
    tr_labels = np.array([CLASS_TO_ID[c] for fp, c in train_pairs], dtype=np.int64)

    te_paths = np.array([fp for fp, c in test_pairs], dtype=np.str_)
    te_labels = np.array([CLASS_TO_ID[c] for fp, c in test_pairs], dtype=np.int64)

    cw = compute_class_weight(tr_labels)

    train_ds = tf.data.Dataset.from_tensor_slices((tr_paths, tr_labels))
    train_ds = train_ds.shuffle(2000, seed=SEED, reshuffle_each_iteration=True)
    train_ds = train_ds.map(lambda p, y: tf_load_and_aug(p, y, True), num_parallel_calls=tf.data.AUTOTUNE)
    train_ds = train_ds.batch(BATCH).prefetch(tf.data.AUTOTUNE)

    test_ds = tf.data.Dataset.from_tensor_slices((te_paths, te_labels))
    test_ds = test_ds.map(lambda p, y: tf_load_and_aug(p, y, False), num_parallel_calls=tf.data.AUTOTUNE)
    test_ds = test_ds.batch(BATCH).prefetch(tf.data.AUTOTUNE)

    model = build_model((INPUT_SIZE, INPUT_SIZE, 1), num_classes=len(CLASSES))
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(LR),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=['accuracy']
    )

    callbacks = [
        # Pazienza aumentata un po'
        tf.keras.callbacks.ReduceLROnPlateau(patience=6, factor=0.5, min_lr=1e-6, verbose=1),
        tf.keras.callbacks.EarlyStopping(patience=12, restore_best_weights=True, monitor='val_loss', verbose=1),
    ]

    print("Inizio Training...")
    model.fit(
        train_ds, 
        validation_data=test_ds if len(test_pairs) > 0 else None,
        epochs=EPOCHS, 
        callbacks=callbacks, 
        class_weight=cw
    )

    os.makedirs(os.path.dirname(MODEL_DIR), exist_ok=True)
    model.save(MODEL_DIR)
    print("✅ Salvato modello CNN:", MODEL_DIR)

    if len(test_pairs) > 0:
        res = model.evaluate(test_ds, verbose=0)
        print(f"Test Loss: {res[0]:.4f}, Test Accuracy: {res[1]:.4f}")

if __name__ == "__main__":
    main()