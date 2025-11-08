import os
import pyttsx3
from utils import load_config, load_words, ensure_folders
from game_logic import select_word
from robot_control import Robot

def say(text):
    """Sintesi vocale semplice con pyttsx3."""
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def main():
    print("WordBuddy - Avvio del sistema...")

    # Carichiamo la configurazione principale
    config_path = os.path.join("data", "config.yaml")
    config = load_config(config_path)
    print("Configurazione caricata con successo:")
    print(config)
    # Carichiamo la lista di parole
    words_path = os.path.join("data", "words.json")
    words = load_words(words_path)
    print(f"{len(words)} parole caricate.")
    # Caricamento dati di calibrazione
    calib_dir = os.path.join("data", "calibration")
    if os.path.exists(calib_dir):
        print(f"Cartella calibrazione trovata: {calib_dir}")
    else:
        print("Nessun dato di calibrazione trovato.")

    # Mostriamo i dati principali
    print("\n--- Riepilogo ---")
    print(f"Robot IP: {config.get('robot_ip', 'non specificato')}")
    print(f"Camera ID: {config.get('camera_id', 'default')}")
    print(f"Numero parole disponibili: {len(words)}")

    print("\nSetup completato ✅")

    # --- 1. Inizializzazione robot ---
    robot = Robot(config.get("robot_ip"))

    # --- 2. Selezione parola ---
    word = select_word(words)
    say(f"La parola è {word}")

    # --- 3. Simulazione posizionamento lettere ---
    grid = {
        "0": (0.1, 0.1),
        "1": (0.2, 0.1),
        "2": (0.3, 0.1),
        "3": (0.4, 0.1),
        "4": (0.5, 0.1),
        "5": (0.6, 0.1),
    }
    robot.place_initial_letters(word, grid)

    print("🧩 Setup e posizionamento completati ✅")

if __name__ == "__main__":
    main()
