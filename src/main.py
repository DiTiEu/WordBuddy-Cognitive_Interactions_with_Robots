import os
# import pyttsx3
from utils import load_config, load_words, ensure_folders
from game_logic import select_word
from robot_control import Robot
from game_logic import split_letters

"""

def say(text):
    Sintesi vocale semplice con pyttsx3.
    engine = pyttsx3.init()
    engine.setProperty("rate", 180)  # velocità di parlato
    engine.say(text)
    engine.runAndWait()

"""

def difficulty_feedback(level: str):
    """Messaggio vocale e testuale in base alla difficoltà scelta."""
    level = level.lower()
    if level == "easy":
        message = "Hai scelto la modalità facile! Ti aiuterò di più con le lettere."
    elif level == "hard":
        message = "Hai scelto la modalità difficile! Toccherà a te completare quasi tutta la parola."
    else:
        message = "Hai scelto la modalità normale! Lavoreremo insieme a metà."
    
    print(f"🎙️ {message}")
    # say(message)

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
    # Inizializzo il robot
    robot = Robot(
        robot_ip=config.get("robot_ip"),
        poses=config.get("poses", {}),
        safety=config.get("safety", {})
    )

    # --- 2. Impostazione difficoltà ---
    difficulty = input("Scegli la difficoltà (easy / normal / hard): ").strip().lower()
    if difficulty not in ["easy", "normal", "hard"]:
        print("Difficoltà non valida, imposto 'normal' di default.")
        difficulty = "normal"
    config["difficulty"] = difficulty
    difficulty_feedback(difficulty) # Aggiunto feedback vocale qui

    # --- 3. Selezione parola ---
    word = select_word(words)
    if not word:
        raise RuntimeError("Errore: nessuna parola è stata selezionata.")

    # say(f"La parola è {word}")

    # --- 4. Posizionamento lettere ---
    robot_letters, user_letters = split_letters(word, difficulty)

    # ------------------------------------------------------------------
    # DEMO PICK & PLACE: LETTERA A -> SLOT 0
    # ------------------------------------------------------------------
    print("\n🚀 AVVIO DEMO: Spostamento lettera 'A' nello Slot '0'...")
    
    # Questa funzione esegue la sequenza: 
    # Vai su A -> Apri -> Scendi -> Chiudi -> Sali -> Vai su 0 -> Scendi -> Apri -> Sali
    # easy
    # robot.place_letter_in_slot("A", 0)
    for slot in range(5):
        robot.place_letter_in_calculated_slot("C", slot)
    # Nota: Il ciclo del gioco reale è commentato qui sotto per riferimento futuro
    # for slot_index, letter in enumerate(robot_letters):
    #     robot.place_letter_in_slot(letter, slot_index)

    print("✅ Demo Pick & Place completata.")
    # ------------------------------------------------------------------

    # say("Demo completata. Ora tocca a te!")

    robot.close()

if __name__ == "__main__":
    main()