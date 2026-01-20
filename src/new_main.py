import os
import time
import yaml
import sys
import csv
import pyttsx3
from datetime import datetime

# Path per i moduli src nella repository
sys.path.append(os.getcwd())

from src.utils import load_config, load_words
from src.game_logic import select_word, split_letters, create_word_with_error
from src.new_robot_control import Robot 
from src.board_vision import build_board_vision_from_config_dict

# --- TTS INITIALIZATION ---
engine = pyttsx3.init()
engine.setProperty('rate', 145) 
engine.setProperty('volume', 1.0)

def speak(text, display_text=None):
    """
    Output vocale e testuale. 
    Se display_text è fornito, stampa quello invece del testo pronunciato.
    """
    to_print = display_text if display_text else text
    print(f"\n🔊 Robot: {to_print}")
    engine.say(text)
    engine.runAndWait()

def log_session_metrics(mode, target_word, cycle_time, status):
    """Registra performance in data/robot_performance_metrics.csv."""
    log_file = "data/robot_performance_metrics.csv"
    headers = ["timestamp", "game_mode", "target_word", "cycle_time_sec", "result"]
    file_exists = os.path.isfile(log_file)
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(headers)
        writer.writerow([datetime.now(), mode, target_word, round(cycle_time, 2), status])

def read_board_real(vision, target_len):
    """Lettura board tramite CNN con euristica di occupazione."""
    frame = vision.capture_frame()
    detected_str = vision.read_from_frame(frame, save_debug=True) 
    detected = [('_' if c == ' ' else c) for c in detected_str]
    return detected[:target_len]

def analyze_board(target_word, detected_letters):
    """Analisi correttezza parola."""
    target_chars = list(target_word.upper())
    if '_' in detected_letters: return 'INCOMPLETE', []
    wrong_indices = [i for i, (t, d) in enumerate(zip(target_chars, detected_letters)) if t != d]
    return ('CORRECT' if not wrong_indices else 'WRONG'), wrong_indices

def main():
    print("\n" + "═"*55)
    print("🤖  WORDBUDDY: YOUR INTERACTIVE ENGLISH TUTOR  🤖")
    print("═"*55)

    config_path = os.path.join("data", "config.yaml")
    config = load_config(config_path)
    words_data = load_words(os.path.join("data", "words.json"))
    
    robot = Robot(robot_ip=config.get("robot", {}).get("ip"), config=config)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            vision_cfg = yaml.safe_load(f)
        vision = build_board_vision_from_config_dict(vision_cfg)
        use_camera = True
        print("📷 Vision System: ONLINE (CNN Ready)")
    except Exception as e:
        print(f"⚠️ Vision System: OFFLINE ({e})")
        use_camera = False

    speak("Hello! I am WordBuddy. Please select a game mode by pressing key 1, 2, or 3 on your keyboard.")

    while True:
        print("\n" + "┌───────────────────────────────────────────┐")
        print("│            SELECT YOUR CHALLENGE          │")
        print("└───────────────────────────────────────────┘")
        print("  PLEASE PRESS A NUMBER KEY:")
        print("  [1] SPELLING BEE   🐝  (Listen and spell)")
        print("  [2] FILL THE GAP   🧩  (Complete the word)")
        print("  [3] FIND THE ERROR 🔍  (Fix my mistake)")
        print("  [Q] QUIT SESSION   👋")
        
        mode_choice = input("\n👉 Select (1/2/3/Q): ").strip().upper()
        if mode_choice == 'Q': break
        if mode_choice not in ['1', '2', '3']: continue

        word_obj = select_word(words_data)
        target = word_obj['word'].upper()
        hint = word_obj['hint']
        stars = "*" * len(target)
        start_time = time.time()
        game_status = "PENDING"

        # --- SETUP MODALITÀ ---
        if mode_choice == '1':
            speak("Spelling Bee! I will describe a word, and you must spell it. I will not show the word on the screen!")
            speak(f"The word is {target}. Here is a clue: {hint}.", 
                  display_text=f"The word is {stars}. Clue: {hint}")
            speak("Now, look for the letters and place them in the slots on the board, from left to right.")

        elif mode_choice == '2':
            speak("Mode selected: Fill the Gap.")
            diff = input("First, select difficulty (easy/normal/hard): ").lower()
            speak(f"I have a secret word for you. It has {len(target)} letters. Here is the clue: {hint}.", 
                  display_text=f"Target: {stars} ({len(target)} letters). Clue: {hint}")
            display_str = split_letters(target, diff)
            speak("Watch the robot arm! I am placing some letters to help you start.")
            for i, char in enumerate(display_str):
                if char != '_': robot.place_letter_in_calculated_slot(char, i)
            speak(f"Now it is your turn! Fill the remaining empty slots to complete the word.")

        elif mode_choice == '3':
            # 1. NON SCRIVE LA PAROLA, LA PRONUNCIA E BASTA [Richiesta Utente]
            wrong_word, _ = create_word_with_error(target)
            speak(f"Find the Error! The word is {target}. Clue: {hint}.", 
                  display_text=f"Find the Error! Target: {stars}. Clue: {hint}")
            
            # 2. POSIZIONA LE LETTERE CON ERRORE [Richiesta Utente]
            speak("Watch me! I will write the word with one mistake. Wait for me to finish moving.")
            for i, char in enumerate(wrong_word):
                robot.place_letter_in_calculated_slot(char, i)
            speak("I am done. Find the wrong block and replace it with the correct one.")

        # --- LOOP DI VALIDAZIONE ---
        game_active = True
        while game_active:
            # Nasconde la parola nel terminale per i casi 1, 2 e 3
            if mode_choice in ['1', '2', '3']:
                print(f"\n📝 TARGET: {stars} (Clue: {hint})")
            else:
                print(f"\n📝 TARGET WORD: {target} ({hint})")

            print("👉 INSTRUCTION: Move the blocks into the slots on the board now.")
            user_input = input("   (Press ENTER to check, or type 'R' and Enter to hear the clue again): ").strip().upper()
            
            if user_input == 'R':
                # Ripete senza svelare la parola visivamente
                if mode_choice in ['1', '2', '3']:
                    speak(f"The word is {target}. I repeat, {target}. The clue is: {hint}.",
                          display_text=f"Target: {stars}. Clue: {hint}")
                else:
                    speak(f"The word is {target}. The clue is: {hint}.")
                continue 

            if use_camera:
                speak("Checking the board... stay still!")
                try:
                    detected = read_board_real(vision, len(target))
                    print(f"🔍 I detected: {' '.join(detected)}")
                    status, wrongs = analyze_board(target, detected)
                    
                    if status == 'CORRECT':
                        # Rivela la parola solo alla vittoria
                        speak(f"Excellent! {target} is the correct word. Well done!")
                        game_status = "SUCCESS"; game_active = False
                    elif status == 'INCOMPLETE':
                        speak("I see empty slots. Please fill every space to complete the word.")
                    else:
                        speak(f"I found {len(wrongs)} mistakes. Fix the blocks and try again.")
                        if input("Type 'y' if you want me to remove the errors: ").lower() == 'y':
                            speak("Okay, I am clearing the wrong letters for you.")
                            for idx in wrongs: robot.remove_letter_from_slot(idx, detected[idx])
                except Exception as e:
                    print(f"⚠️ Vision Error: {e}")
            else:
                game_active = False

        cycle_time = time.time() - start_time
        log_session_metrics(mode_choice, target, cycle_time, game_status)
        
        if input("\nPlay again? (y/n): ").lower() != 'y': break
        if input("Clear the board? (y/n): ").lower() == 'y':
            speak("Clearing the board. Please wait for the robot arm.")
            robot.clear_board(list(target))

    robot.close()
    speak("Goodbye! See you next time.")

if __name__ == "__main__":
    main()