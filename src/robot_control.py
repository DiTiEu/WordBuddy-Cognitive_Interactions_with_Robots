# src/robot_control.py

import time
try:
    import urx
except ImportError:
    urx = None
    print("⚠️ 'urx' non trovato, uso modalità simulata.")

class Robot:
    def __init__(self, robot_ip: str, poses: dict, safety: dict):
        self.robot_ip = robot_ip
        self.poses = poses or {}
        self.letter_sources = self.poses.get("letter_sources", {})
        self.slots = self.poses.get("slots", {})
        self.safe_height = safety.get("safe_height", 0.25)
        self.z_pick_offset = safety.get("z_pick_offset", -0.04)
        self.max_speed = safety.get("max_speed", 0.1)
        self.max_acc = safety.get("max_acc", 0.1)

        self._simulated = urx is None or self.robot_ip is None
        if self._simulated:
            print("🤖 Robot in modalità SIMULATA.")
            self.rob = None
        else:
            print(f"🤖 Connessione all'UR3 ({self.robot_ip})...")
            self.rob = urx.Robot(self.robot_ip)
            print("✅ Connesso.")

    def close(self):
        if self.rob is not None and not self._simulated:
            self.rob.close()
            print("🔌 Connessione chiusa.")

    # ---------- MOVIMENTO DI BASE ----------

    def move_joints(self, joints):
        if self._simulated:
            print(f"(SIM) move_joints: {joints}")
            time.sleep(1)
        else:
            self.rob.movej(joints, acc=self.max_acc, vel=self.max_speed)

    def move_relative_z(self, dz: float):
        """Muove il TCP su Z in modo relativo (su/giù)."""
        if self._simulated:
            print(f"(SIM) translate Z di {dz} m")
            time.sleep(0.5)
        else:
            self.rob.translate((0, 0, dz), acc=self.max_acc, vel=self.max_speed, relative=True)

    def move_to_pose(self, pose_name: str):
        if pose_name not in self.poses:
            print(f"⚠️ Pose '{pose_name}' non trovata nel config.")
            return
        joints = self.poses[pose_name]
        print(f"➡️  Vado alla pose '{pose_name}'")
        self.move_joints(joints)

    # ---------- PRENDERE / METTERE LETTERE ----------

    def _go_to_letter_source(self, letter: str):
        letter = letter.upper()
        if letter not in self.letter_sources:
            print(f"⚠️ Nessuna sorgente definita per la lettera '{letter}'")
            return None
        joints = self.letter_sources[letter]
        print(f"➡️  Vado alla sorgente della lettera '{letter}'")
        self.move_joints(joints)
        return joints

    def _go_to_slot(self, slot_index: int):
        key = str(slot_index)
        if key not in self.slots:
            print(f"⚠️ Nessuna slot definita per indice '{slot_index}'")
            return None
        joints = self.slots[key]
        print(f"➡️  Vado sopra la slot {slot_index}")
        self.move_joints(joints)
        return joints

    def grip(self, state: bool):
        """Placeholder: qui poi aggiungerai il comando reale per il gripper."""
        if self._simulated:
            print("(SIM) Gripper", "CHIUSO" if state else "APERTO")
        else:
            print("⚠️ Gripper reale non ancora implementato. Stato richiesto:", state)

    def place_letter_in_slot(self, letter: str, slot_index: int):
        """
        Sequenza completa:
        1. Vai sopra sorgente lettera
        2. Scendi, prendi blocco
        3. Torna su
        4. Vai sopra slot
        5. Scendi, lascia blocco
        6. Torna su
        """

        print(f"📦 Inizio sequenza per lettera '{letter}' nello slot {slot_index}")

        # 1. Vai alla sorgente della lettera
        if self._go_to_letter_source(letter) is None:
            return

        # 2. Scendi e prendi
        self.move_relative_z(self.z_pick_offset)
        self.grip(True)   # CHIUDI
        self.move_relative_z(-self.z_pick_offset)

        # 3. Vai allo slot della parola
        if self._go_to_slot(slot_index) is None:
            return

        # 4. Scendi e lascia
        self.move_relative_z(self.z_pick_offset)
        self.grip(False)  # APRI
        self.move_relative_z(-self.z_pick_offset)

        print("✅ Lettera posizionata.")
