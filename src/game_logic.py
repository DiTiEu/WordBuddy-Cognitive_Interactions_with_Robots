import random

def select_word(words: list, min_len: int = 3, max_len: int = 6) -> str:
    """
    Sceglie casualmente una parola dal dataset, double check sui limiti di lunghezza.
    """
    print("Selezionando una parola...")
    valid_words = [w for w in words if min_len <= len(w) <= max_len]
    if not valid_words:
        raise ValueError("Nessuna parola valida trovata nel dataset!")
    
    word = random.choice(valid_words)
    print(f"Parola scelta: {word}")
    return word


def split_letters(word: str, difficulty: str = "normal") -> tuple:
    """
    Divide la parola in due gruppi (robot / utente)
    in base alla difficoltà selezionata.
    """
    n = len(word)

    difficulty = difficulty.lower()
    if difficulty == "easy":
        num_robot_letters = max(1, int(n * 0.7))   # robot aiuta di più
    elif difficulty == "hard":
        num_robot_letters = max(1, int(n * 0.3))   # robot aiuta di meno
    else:
        num_robot_letters = max(1, int(n * 0.5))   # equilibrio

    robot_letters = word[:num_robot_letters]
    user_letters = word[num_robot_letters:]

    print(f"🤖 Robot posizionerà: {robot_letters}")
    print(f"🧍‍♂️ Utente completerà: {user_letters}")
    return robot_letters, user_letters

