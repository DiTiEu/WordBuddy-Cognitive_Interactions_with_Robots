import time

class Robot:
    def __init__(self, robot_ip: str = None):
        """
        In futuro qui potremo inizializzare la connessione reale (urx o rtde).
        Per ora simula il comportamento.
        """
        self.robot_ip = robot_ip
        print(f"🤖 Robot inizializzato (IP: {self.robot_ip})")

    def move_to(self, position_name: str):
        """Simula uno spostamento a una posizione predefinita."""
        print(f"➡️  Muovo robot verso: {position_name}")
        time.sleep(0.5)

    def grip(self, state: bool):
        """Simula apertura/chiusura gripper."""
        if state:
            print("✊ Gripper chiuso (presa)")
        else:
            print("🖐️ Gripper aperto (rilascio)")
        time.sleep(0.3)

    def place_letter(self, letter: str, grid_position: tuple):
        """Simula il posizionamento di una singola lettera."""
        x, y = grid_position
        print(f"📦 Posiziono lettera '{letter}' alla cella ({x}, {y})")
        self.move_to("above_cell")
        self.grip(True)
        self.move_to("down_to_place")
        self.grip(False)
        self.move_to("safe_height")

    def place_initial_letters(self, word: str, grid: dict):
        """
        Posiziona alcune lettere iniziali della parola sul tavolo.
        'grid' è un dizionario con coordinate delle celle.
        """
        from game_logic import split_letters
        robot_letters, user_letters = split_letters(word)

        for i, letter in enumerate(robot_letters):
            if str(i) in grid:
                self.place_letter(letter, grid[str(i)])
            else:
                print(f"⚠️ Nessuna cella definita per indice {i}")

        print("✅ Lettere iniziali posizionate con successo.")
        return robot_letters, user_letters
