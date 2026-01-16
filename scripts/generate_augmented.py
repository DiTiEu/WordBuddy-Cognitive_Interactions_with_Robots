import cv2
import numpy as np
import os
import glob
import random

# CONFIGURAZIONE
INPUT_DIR = "data/dataset_slots"       # Cartella con le foto originali
OUTPUT_DIR = "data/dataset_augmented"  # Nuova cartella dove salvare tutto
TARGET_PER_CLASS = 200                 # Quante immagini vogliamo per ogni lettera
IMG_SIZE = 64

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def augment_image(img):
    """Applica distorsioni casuali all'immagine"""
    h, w = img.shape[:2]
    
    # 1. Rotazione e Scala (Zoom)
    # Ruota tra -20 e +20 gradi
    angle = random.uniform(-20, 20)
    # Zoom tra 0.85 (più lontano) e 1.15 (più vicino)
    scale = random.uniform(0.85, 1.15)
    
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    
    # Shift (Spostamento laterale/verticale)
    tx = random.randint(-5, 5)
    ty = random.randint(-5, 5)
    M[0, 2] += tx
    M[1, 2] += ty

    # Applica trasformazione geometrica
    # borderMode=cv2.BORDER_REPLICATE riempie i bordi con i pixel vicini (non nero)
    aug = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

    # 2. Luminosità e Contrasto
    # Moltiplica (contrasto) e aggiungi (luminosità)
    contrast = random.uniform(0.7, 1.3)
    brightness = random.randint(-30, 30)
    aug = cv2.convertScaleAbs(aug, alpha=contrast, beta=brightness)

    # 3. Rumore (Noise)
    # Aggiunge "grana" per evitare che la rete impari pixel precisi
    if random.random() < 0.5:
        noise = np.random.normal(0, 5, aug.shape).astype(np.uint8)
        # Convertiamo per evitare overflow/underflow
        aug = cv2.add(aug, noise)

    # 4. Blur (Sfocatura leggera)
    if random.random() < 0.3:
        aug = cv2.GaussianBlur(aug, (3, 3), 0)

    return aug

def main():
    print(f"--- Inizio Generazione Augmentation da {INPUT_DIR} ---")
    
    classes = [d for d in os.listdir(INPUT_DIR) if os.path.isdir(os.path.join(INPUT_DIR, d))]
    # Ordiniamo e assicuriamoci che ci siano tutte le classi
    classes.sort()
    
    total_images = 0

    for cls in classes:
        # Percorsi input e output
        src_path = os.path.join(INPUT_DIR, cls)
        dst_path = os.path.join(OUTPUT_DIR, cls)
        ensure_dir(dst_path)
        
        # Trova immagini originali
        originals = glob.glob(os.path.join(src_path, "*.png")) + \
                    glob.glob(os.path.join(src_path, "*.jpg"))
        
        if not originals:
            continue

        print(f"Processando classe '{cls}': {len(originals)} originali trovati.")
        
        # Copia le originali
        count = 0
        loaded_imgs = []
        
        for i, fpath in enumerate(originals):
            img = cv2.imread(fpath)
            if img is None: continue
            
            # Resize standard
            img = cv2.resize(img, (IMG_SIZE, IMG_SIZE))
            loaded_imgs.append(img)
            
            # Salva originale nella nuova cartella
            save_name = os.path.join(dst_path, f"org_{i}.png")
            cv2.imwrite(save_name, img)
            count += 1
        
        # Genera le copie aumentate fino ad arrivare al TARGET
        while count < TARGET_PER_CLASS:
            # Prendi un'immagine originale a caso
            base_img = random.choice(loaded_imgs)
            
            # Crea una variante
            aug_img = augment_image(base_img)
            
            # Salva
            save_name = os.path.join(dst_path, f"aug_{count}.png")
            cv2.imwrite(save_name, aug_img)
            count += 1
            
        print(f" -> Totale immagini per '{cls}': {count}")
        total_images += count

    print("------------------------------------------------")
    print(f"GENERAZIONE COMPLETATA. Dataset salvato in: {OUTPUT_DIR}")
    print(f"Totale immagini generate: {total_images}")
    print("Ora modifica train_cnn.py per puntare a questa nuova cartella!")

if __name__ == "__main__":
    main()