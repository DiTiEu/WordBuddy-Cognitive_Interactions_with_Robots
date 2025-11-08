import os
import yaml
import json

def load_config(path: str) -> dict:
    """Carica il file di configurazione YAML."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File di configurazione non trovato: {path}")

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def load_words(path: str) -> list:
    """Carica la lista delle parole dal file JSON."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"File delle parole non trovato: {path}")

    with open(path, "r", encoding="utf-8") as f:
        words = json.load(f)
    if not isinstance(words, list):
        raise ValueError("Il file delle parole deve contenere una lista di stringhe.")
    return words


def ensure_folders(folder_list: list):
    """Crea le cartelle se non esistono."""
    for folder in folder_list:
        os.makedirs(folder, exist_ok=True)
