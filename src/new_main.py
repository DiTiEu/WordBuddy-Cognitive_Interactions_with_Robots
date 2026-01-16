import os
import time
import yaml
import sys

# Aggiungiamo la root del progetto al path per sicurezza
sys.path.append(os.getcwd())

from utils import load_config, load_words
from game_logic import select_word, split_letters
from new_robot_control import Robot 

# Importiamo la factory che legge la config e crea la visione CNN
from src.board_vision import build_board_vision_from_config_dict


# --- FUNZIONI VISIONE ---

def mock_read_board(target_len):
    """Fallback manuale se la camera non va"""
    print("\n👀 [MOCK] Visione simulata.")
    user_input = input("   Inserisci lettere sul tavolo (es. 'C _ R S O'): ").strip().upper()
    detected_letters = [c if c.isalnum() else '_' for c in user_input.replace(" ", "")]
    # Padding se troppo corta
    while len(detected_letters) < target_len:
        detected_letters.append('_')
    return detected_letters[:target_len]


def read_board_real(vision, target_len, save_debug=True):
    """
    Usa la BoardVision (che dentro ha la CNN) per leggere le lettere.
    """
    if target_len > 5:
        print(f"⚠️ Attenzione: Parola lunga {target_len}, ma la board ha max 5 slot.")

    # 1. Cattura frame
    frame = vision.capture_frame()
    
    # 2. Elaborazione (Warp -> Crop -> CNN Predict)
    # Ritorna una stringa di 5 caratteri (es "C RSO")
    detected_str = vision.read_from_frame(frame, save_debug=save_debug) 
    
    # 3. Conversione in lista
    detected = [('_' if c == ' ' else c) for c in detected_str]
    
    return detected[:target_len]


def analyze_board(target_word, detected_letters):
    """Logica di confronto standard"""
    target_chars = list(target_word)

    if '_' in detected_letters:
        return 'INCOMPLETE', []

    wrong_indices = []
    for i, (t, d) in enumerate(zip(target_chars, detected_letters)):
        if t != d:
            wrong_indices.append(i)

    if wrong_indices:
        return 'WRONG', wrong_indices

    return 'CORRECT', []


# --- MAIN ---

def main():
    print("\n🤖 --- WORDBUDDY (CNN VERSION) --- 🤖\n")

    # 1. CARICAMENTO CONFIG
    config_path = os.path.join("data", "config.yaml")
    config = load_config(config_path)
    words = load_words(os.path.join("data", "words.json"))

    # 2. INIT ROBOT
    robot = Robot(
        robot_ip=config.get("robot", {}).get("ip"),
        config=config
    )

    # 3. INIT VISIONE (CNN)
    try:
        # Rileggiamo il yaml raw per passarlo al builder
        with open(config_path, "r", encoding="utf-8") as f:
            vision_cfg = yaml.safe_load(f)
        
        vision = build_board_vision_from_config_dict(vision_cfg)
        use_camera = True
        print("📷 Sistema di Visione CNN caricato correttamente.")
    except Exception as e:
        print(f"⚠️ Errore caricamento Visione: {e}")
        print("   Si userà la modalità MOCK (manuale).")
        vision = None
        use_camera = False

    while True:
        print("\n" + "=" * 40)
        print("🆕 NUOVO ROUND")
        print("=" * 40)

        # Scelta difficoltà
        while True:
            diff = input("🎚️  Difficoltà (easy/normal/hard): ").lower().strip()
            if diff in ["easy", "normal", "hard"]: break

        # Scelta Parola (max 5 lettere)
        target_word = None
        for _ in range(100):
            w = select_word(words)
            if w and len(w) <= 5:
                target_word = w
                break
        
        if not target_word:
            print("❌ Errore: nessuna parola valida trovata.")
            break

        robot_letters, user_letters = split_letters(target_word, diff)

        print(f"\n🎯 Parola Target: {target_word}")
        print(f"🤖 Robot mette: {robot_letters}")
        print(f"👤 Tu metti:    {user_letters}")

        # Robot agisce
        print("\n🦾 Il robot posiziona le sue lettere...")
        for i, letter in enumerate(robot_letters):
            if letter != '_':
                robot.place_letter_in_calculated_slot(letter, i)

        # Loop di gioco
        game_active = True
        detected = []

        while game_active:
            print(f"\n⏳ Completa la parola: {target_word}")
            input("👉 Premi INVIO per analizzare il tavolo...")

            # LETTURA TAVOLO
            if use_camera:
                try:
                    detected = read_board_real(vision, len(target_word), save_debug=True)
                except Exception as e:
                    print(f"⚠️ Errore Visione: {e}")
                    detected = mock_read_board(len(target_word))
            else:
                detected = mock_read_board(len(target_word))

            print(f"🔍 Il robot vede: {' '.join(detected)}")

            # ANALISI
            status, wrong_indices = analyze_board(target_word, detected)

            if status == 'CORRECT':
                print("\n🎉 BRAVO! Parola corretta! 🎉")
                game_active = False

            elif status == 'INCOMPLETE':
                print("\n⚠️  Parola incompleta.")
                print("   Completa gli spazi vuoti e riprova.")

            elif status == 'WRONG':
                print(f"\n❌ Ci sono {len(wrong_indices)} lettere sbagliate.")
                print("1. Riprova tu")
                print("2. Aiuto Robot (Rimuove errate)")
                print("3. Resa (Robot corregge tutto)")
                
                choice = input("Scelta: ")
                
                if choice == '2':
                    print("🦾 Rimuovo lettere errate...")
                    for idx in wrong_indices:
                        if detected[idx] != '_':
                            robot.remove_letter_from_slot(idx, detected[idx])
                elif choice == '3':
                    print("🦾 Correggo tutto...")
                    # Rimuovi errate
                    for idx in wrong_indices:
                        if detected[idx] != '_':
                            robot.remove_letter_from_slot(idx, detected[idx])
                    # Metti giuste
                    for idx in wrong_indices:
                        robot.place_letter_in_calculated_slot(target_word[idx], idx)
                    game_active = False

        # Fine partita
        if input("\nVuoi giocare ancora? (s/n): ").lower() != 's':
            robot.close()
            break
        else:
            if input("Svuotare il tavolo? (s/n): ").lower() == 's':
                robot.clear_board(list(target_word))

if __name__ == "__main__":
    main()