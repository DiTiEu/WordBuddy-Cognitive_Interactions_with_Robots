import random

def select_word(words: list, min_len: int = 3, max_len: int = 6) -> str:
    """
    Sceglie casualmente una parola dal dataset, double check sui limiti di lunghezza.
    """
    valid_words = [w for w in words if min_len <= len(w) <= max_len]
    if not valid_words:
        raise ValueError("Nessuna parola valida trovata nel dataset!")
    
    word = random.choice(valid_words)
    print(f"🎯 Parola scelta: {word}")
    return word


def split_letters(word: str) -> tuple:
    """
    Divide la parola in due gruppi:
    - lettere che il robot posizionerà
    - lettere che l'utente dovrà completare
    """
    n = len(word)
    if n <= 3:
        robot_letters = word[:1]
    elif n <= 5:
        robot_letters = word[:2]
    else:
        robot_letters = word[:3]
    
    user_letters = word[len(robot_letters):]
    print(f"🤖 Robot posizionerà: {robot_letters}")
    print(f"🧍‍♂️ Utente completerà: {user_letters}")
    return robot_letters, user_letters
