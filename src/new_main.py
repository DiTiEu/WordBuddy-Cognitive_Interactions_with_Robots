import os
import time
import yaml

from utils import load_config, load_words
from game_logic import select_word, split_letters
from new_robot_control import Robot

from src.board_vision import build_board_vision_from_config_dict


# --- FUNZIONI HELPER PER IL GIOCO ---

def mock_read_board(target_len):
    """
    SIMULAZIONE VISIONE:
    Invece di usare la telecamera, chiede all'utente cosa c'è sul tavolo.
    """
    print("\n👀 (Simulazione Camera) Il robot sta guardando il tavolo...")
    user_input = input("   [DEBUG] Scrivi le lettere che vedi sul tavolo (usa _ per vuoto): ").strip().upper()

    detected_letters = [c if c.isalnum() else '_' for c in user_input.replace(" ", "")]

    while len(detected_letters) < target_len:
        detected_letters.append('_')

    return detected_letters[:target_len]


def read_board_real(vision, target_len, save_debug=True):
    """
    VISIONE REALE:
    Usa BoardVision (HOG+SVM) e ritorna lista di char 'A'..'Z' oppure '_'.
    """
    if target_len > 5:
        raise RuntimeError(f"Parola lunga {target_len} ma la board ha solo 5 slot.")

    frame = vision.capture_frame()
    detected_str = vision.read_from_frame(frame, save_debug=save_debug)  # 5 char con ' ' per vuoto

    detected = [('_' if c == ' ' else c) for c in detected_str]

    return detected[:target_len]


def analyze_board(target_word, detected_letters):
    """
    Confronta la parola target con ciò che c'è sul tavolo.
    """
    target_chars = list(target_word)

    # 1. Controllo Spazi Vuoti
    if '_' in detected_letters:
        return 'INCOMPLETE', []

    # 2. Controllo Errori
    wrong_indices = []
    for i, (t, d) in enumerate(zip(target_chars, detected_letters)):
        if t != d:
            wrong_indices.append(i)

    if wrong_indices:
        return 'WRONG', wrong_indices

    return 'CORRECT', []


# --- MAIN LOOP ---

def main():
    print("\n🤖 --- WORDBUDDY AVVIATO --- 🤖\n")

    # 1. SETUP
    config = load_config(os.path.join("data", "config.yaml"))
    words = load_words(os.path.join("data", "words.json"))

    # Robot
    robot = Robot(
        robot_ip=config.get("robot", {}).get("ip"),
        config=config
    )

    # Vision (caricata dal config.yaml completo)
    vision_cfg = yaml.safe_load(open(os.path.join("data", "config.yaml"), "r", encoding="utf-8"))
    vision = build_board_vision_from_config_dict(vision_cfg)

    while True:
        # --- NUOVA PARTITA ---
        print("\n" + "=" * 40)
        print("🆕 NUOVO ROUND")
        print("=" * 40)

        # 2. DIFFICOLTÀ
        while True:
            diff = input("🎚️  Scegli difficoltà (easy/normal/hard): ").lower().strip()
            if diff in ["easy", "normal", "hard"]:
                break
            print("❌ Scelta non valida.")

        # 3. SELEZIONE PAROLA E PREPARAZIONE
        # IMPORTANTE: board ha 5 slot -> scegli parola <= 5
        target_word = None
        for _ in range(50):
            w = select_word(words)
            if w and len(w) <= 5:
                target_word = w
                break
        if not target_word:
            print("⚠️ Errore: non trovo parole di lunghezza <= 5 nel database.")
            break

        robot_letters, user_letters = split_letters(target_word, diff)

        print(f"\n🎯 La parola segreta è lunga {len(target_word)} lettere.")
        print(f"🤖 Il robot posizionerà: {robot_letters}")
        print(f"👤 Tu dovrai mettere: {user_letters}")

        # 4. ROBOT POSIZIONA LE SUE LETTERE
        print("\n🦾 Il robot sta lavorando...")
        for i, letter in enumerate(robot_letters):
            if letter != '_':
                robot.place_letter_in_calculated_slot(letter, i)

        # --- GAME LOOP INTERNO (Tentativi Utente) ---
        game_active = True
        detected = []  # stato tavolo

        while game_active:
            print(f"\n⏳ Tocca a te! Completa la parola: {target_word.replace('', ' ').strip()}")
            input("👉 Premi INVIO quando hai posizionato le lettere...")

            # A. VISIONE (Reale, con fallback a mock se fallisce)
            try:
                detected = read_board_real(vision, len(target_word), save_debug=True)
            except Exception as e:
                print(f"⚠️ Vision fallita ({e}). Uso input manuale (mock).")
                detected = mock_read_board(len(target_word))

            print(f"🔍 Il robot vede: {' '.join(detected)}")

            # B. ANALISI
            status, wrong_indices = analyze_board(target_word, detected)

            # C. GESTIONE CASI
            if status == 'CORRECT':
                print("\n🎉 COMPLIMENTI! La parola è corretta! 🎉")
                game_active = False

            elif status == 'INCOMPLETE':
                print("\n⚠️  La parola non è completa.")
                choice = input("Vuoi completarla tu (1) o farla completare al robot (2)? ")
                if choice == '2':
                    print("🦾 Il robot completa la parola...")
                    for i, char in enumerate(target_word):
                        if detected[i] == '_':
                            robot.place_letter_in_calculated_slot(char, i)
                    detected = list(target_word)  # stato fittizio aggiornato
                    game_active = False
                else:
                    print("👍 Riprova, aspetto te.")

            elif status == 'WRONG':
                print(f"\n❌ Ci sono {len(wrong_indices)} lettere sbagliate.")
                print("1. Riprova da solo")
                print("2. Dimmi quali sono sbagliate (il robot le toglie e le rimette a posto)")
                print("3. Arrenditi (il robot corregge tutto)")

                choice = input("Scelta (1/2/3): ")

                if choice == '1':
                    print("💪 Dai, puoi farcela!")

                elif choice == '2':
                    print("🦾 Il robot rimuove le lettere errate...")
                    for idx in wrong_indices:
                        wrong_char = detected[idx]
                        robot.remove_letter_from_slot(idx, wrong_char)
                        detected[idx] = '_'  # aggiorniamo la visione
                    print("Ora riprova a mettere quelle giuste.")

                elif choice == '3':
                    print("🦾 Il robot corregge tutto...")
                    # 1. Toglie le sbagliate
                    for idx in wrong_indices:
                        wrong_char = detected[idx]
                        robot.remove_letter_from_slot(idx, wrong_char)
                    # 2. Mette le giuste
                    for idx in wrong_indices:
                        letter_to_place = target_word[idx]
                        robot.place_letter_in_calculated_slot(letter_to_place, idx)

                    detected = list(target_word)
                    print(f"✅ La parola corretta era: {target_word}")
                    game_active = False

        # --- FINE PARTITA ---
        print("\n🏁 Partita finita.")
        choice = input("Vuoi giocare ancora? (s/n): ").lower()

        # RESET TAVOLO
        reset_choice = input("Il robot deve svuotare il tavolo? (s/n): ").lower()
        if reset_choice == 's':
            letters_on_board = detected if len(detected) > 0 else list(target_word)
            robot.clear_board(letters_on_board)

        if choice != 's':
            print("👋 Grazie per aver giocato a WordBuddy!")
            robot.close()
            break


if __name__ == "__main__":
    main()
