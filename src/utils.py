import os
import yaml
import json

def load_config(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_words(path: str) -> list:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Word file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        words = json.load(f)
    return words

def ensure_folders(folder_list: list):
    for folder in folder_list:
        os.makedirs(folder, exist_ok=True)