import os
import time
import yaml
import sys
import csv
import pyttsx3
from datetime import datetime

sys.path.append(os.getcwd())

from src.utils import load_config, load_words
from src.game_logic import select_word, split_letters, create_word_with_error
from src.new_robot_control import Robot 
from src.board_vision import build_board_vision_from_config_dict

# TTS Init (Compatible with pyttsx3 2.71)
engine = pyttsx3.init()
engine.setProperty('rate', 145)
engine.setProperty('volume', 1.0)

def speak(text):
    print(f"🔊 Robot: {text}")
    engine.say(text)
    engine.runAndWait()

def log_session_metrics(mode, target_word, cycle_time, status):
    log_file = "data/robot_performance_metrics.csv"
    headers = ["timestamp", "game_mode", "target_word", "cycle_time_sec", "result"]
    file_exists = os.path.isfile(log_file)
    with open(log_file, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists: writer.writerow(headers)
        writer.writerow([datetime.now(), mode, target_word, round(cycle_time, 2), status])

def read_board_real(vision, target_len):
    frame = vision.capture_frame()
    detected_str = vision.read_from_frame(frame, save_debug=True) 
    detected = [('_' if c == ' ' else c) for c in detected_str]
    return detected[:target_len]

def analyze_board(target_word, detected_letters):
    target_chars = list(target_word.upper())
    if '_' in detected_letters: return 'INCOMPLETE', []
    wrong_indices = [i for i, (t, d) in enumerate(zip(target_chars, detected_letters)) if t != d]
    return ('CORRECT' if not wrong_indices else 'WRONG'), wrong_indices

def main():
    print("\n🤖 --- WORDBUDDY ENGLISH LEARNING SYSTEM --- 🤖\n")

    config_path = os.path.join("data", "config.yaml")
    config = load_config(config_path)
    words_data = load_words(os.path.join("data", "words.json"))
    robot = Robot(robot_ip=config.get("robot", {}).get("ip"), config=config)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            vision_cfg = yaml.safe_load(f)
        vision = build_board_vision_from_config_dict(vision_cfg)
        use_camera = True
        print("📷 Vision System: ONLINE")
    except Exception as e:
        print(f"⚠️ Vision System: OFFLINE ({e})")
        use_camera = False

    while True:
        print("\n" + "="*45 + "\nMAIN MENU - SELECT GAME MODE\n" + "="*45)
        print("1: SPELLING BEE   (Listen & write from scratch)")
        print("2: RIDDLE MASTER  (Hint & incomplete word)")
        print("3: ERROR HUNTER   (Find and fix robot's typo)")
        print("Q: QUIT SESSION")
        
        mode_choice = input("\nEnter choice (1/2/3/Q): ").strip().upper()
        if mode_choice == 'Q': break
        if mode_choice not in ['1', '2', '3']: continue

        try:
            word_obj = select_word(words_data)
            target = word_obj['word'].upper()
            hint = word_obj['hint']
        except Exception as e:
            print(f"❌ Selection error: {e}"); break

        start_time = time.time()
        game_status = "PENDING"

        if mode_choice == '1':
            speak(f"Listen to the word: {target}. Can you spell it for me?")
        elif mode_choice == '2':
            speak("Here is your hint."); speak(hint)
            diff = input("Select difficulty (easy/normal/hard): ").lower()
            display_str = split_letters(target, diff)
            print(f"Robot placement guide: {display_str}")
            for i, char in enumerate(display_str):
                if char != '_': robot.place_letter_in_calculated_slot(char, i)
        elif mode_choice == '3':
            wrong_word, _ = create_word_with_error(target)
            speak("I will place a word with one mistake. Find it and fix it!")
            for i, char in enumerate(wrong_word):
                robot.place_letter_in_calculated_slot(char, i)

        game_active = True
        while game_active:
            input("\n👉 Press ENTER once you have placed the letters...")
            if use_camera:
                try:
                    detected = read_board_real(vision, len(target))
                    print(f"🔍 System detected: {' '.join(detected)}")
                    status, wrongs = analyze_board(target, detected)
                    
                    if status == 'CORRECT':
                        speak("Excellent! You found the right word.")
                        game_status = "SUCCESS"; game_active = False
                    elif status == 'INCOMPLETE':
                        speak("The word is not finished. Keep going!")
                    else:
                        speak(f"I see {len(wrongs)} mistakes. Take another look.")
                        if input("Need help? Robot can remove errors (y/n): ").lower() == 'y':
                            for idx in wrongs: robot.remove_letter_from_slot(idx, detected[idx])
                except Exception as e: print(f"⚠️ Vision Error: {e}")
            else:
                print(f"DEBUG: Target word was {target}"); game_status = "SUCCESS_MOCK"; game_active = False

        cycle_time = time.time() - start_time
        log_session_metrics(mode_choice, target, cycle_time, game_status)
        print(f"⏱️ Round completed in {cycle_time:.1f} seconds.")

        if input("\nPlay again? (y/n): ").lower() != 'y': break
        if input("Clear the board? (y/n): ").lower() == 'y': robot.clear_board(list(target))

    robot.close()
    speak("Goodbye!")

if __name__ == "__main__":
    main()