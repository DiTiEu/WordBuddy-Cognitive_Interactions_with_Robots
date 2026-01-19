import random
import string

def has_no_duplicates(word: str) -> bool:
    """Returns True if the word contains no repeating letters."""
    word = word.upper()
    return len(set(word)) == len(word)

def select_word(words_data: list, min_len: int = 3, max_len: int = 5) -> dict:
    """
    Selects a word object that has NO repeating letters (isogram).
    """
    valid_entries = [
        w for w in words_data 
        if min_len <= len(w['word']) <= max_len and has_no_duplicates(w['word'])
    ]
    
    if not valid_entries:
        raise ValueError("No valid words without duplicate letters found!")
    
    return random.choice(valid_entries)

def split_letters(word: str, difficulty: str = "normal") -> str:
    """
    Determines which letters the robot provides.
    Returns a string like 'S_N' where underscores are for the user.
    """
    n = len(word)
    difficulty = difficulty.lower()
    
    if difficulty == "easy":
        num_robot_letters = max(1, int(n * 0.7))
    elif difficulty == "hard":
        num_robot_letters = max(1, int(n * 0.3))
    else:
        num_robot_letters = max(1, int(n * 0.5))

    robot_part = word[:num_robot_letters]
    return robot_part.ljust(n, "_")

def create_word_with_error(word: str) -> tuple:
    """
    Creates a version of the word with exactly one incorrect letter.
    Returns (wrong_word, error_index)
    """
    word_list = list(word.upper())
    idx = random.randint(0, len(word_list) - 1)
    original_char = word_list[idx]
    
    possible_letters = list(string.ascii_uppercase)
    possible_letters.remove(original_char)
    new_char = random.choice(possible_letters)
    
    word_list[idx] = new_char
    return "".join(word_list), idx