# src/robot_control.py

import time
import socket
from typing import List


class Robot:
    """
    Controllo UR tramite socket TCP sulla porta 30002.
    Invia comandi URScript come stringhe.

    L'API è compatibile con la versione precedente basata su 'urx':
    - move_joints()
    - move_relative_z()
    - move_to_pose()
    - place_letter_in_slot()
    """

    def __init__(self, robot_ip: str, poses: dict, safety: dict, port: int = 30002):
        self.robot_ip = robot_ip
        self.port = port

        self.poses = poses or {}
        self.letter_sources = self.poses.get("letter_sources", {})
        self.slots = self.poses.get("slots", {})

        self.safe_height = safety.get("safe_height", 0.25)
        self.z_pick_offset = safety.get("z_pick_offset", -0.04)
        self.max_speed = safety.get("max_speed", 0.1)
        self.max_acc = safety.get("max_acc", 0.1)

        self._simulated = False
        self.sock: socket.socket | None = None

        if self.robot_ip is None:
            print("⚠️ Nessun IP robot specificato → modalità SIMULATA.")
            self._simulated = True
            return

        try:
            print(f"🤖 Connessione all'UR3 {self.robot_ip}:{self.port} ...")
            self.sock = socket.create_connection((self.robot_ip, self.port), timeout=2.0)
            self.sock.settimeout(2.0)
            print("✅ Connessione socket riuscita.")
        except OSError as e:
            print(f"⚠️ Impossibile connettersi a {self.robot_ip}:{self.port} → {e}")
            print("➡️ Passo alla modalità SIMULATA.")
            self._simulated = True
            self.sock = None

    # ---------- GESTIONE CONNESSIONE ----------

    def close(self):
        if self.sock is not None and not self._simulated:
            try:
                self.sock.close()
            except OSError:
                pass
            print("🔌 Connessione socket chiusa.")

    def _send_urscript(self, script: str):
        """
        Invia una stringa URScript al robot.
        Se in modalità simulata, stampa solo il comando.
        """
        if self._simulated or self.sock is None:
            print(f"(SIM) URScript:\n{script.strip()}")
            return

        if not script.endswith("\n"):
            script += "\n"

        try:
            self.sock.sendall(script.encode("utf-8"))
        except OSError as e:
            print(f"⚠️ Errore nell'invio di URScript: {e}")

    # ---------- MOVIMENTO DI BASE ----------

    def move_joints(self, joints: List[float]):
        """
        Movimento in spazio giunti con movej().
        'joints' è una lista [q1, q2, q3, q4, q5, q6] in radianti.
        """
        cmd = (
            f"movej([{joints[0]:.5f}, {joints[1]:.5f}, {joints[2]:.5f}, "
            f"{joints[3]:.5f}, {joints[4]:.5f}, {joints[5]:.5f}], "
            f"a={self.max_acc}, v={self.max_speed})"
        )
        print("➡️ move_joints:", joints)
        self._send_urscript(cmd)
        # attesa grossolana per completare il movimento
        time.sleep(2.0)

    def move_relative_z(self, dz: float):
        """
        Muove il TCP lungo Z in modo relativo usando movel().
        """
        script = (
            "p = get_actual_tcp_pose()\n"
            f"p[2] = p[2] + {dz:.5f}\n"
            f"movel(p, a={self.max_acc}, v={self.max_speed})"
        )
        print(f"↕️ move_relative_z: {dz} m")
        self._send_urscript(script)
        time.sleep(1.0)

    def move_to_pose(self, pose_name: str):
        """
        Usa una pose salvata in config.yaml sotto 'poses'.
        Esempio: poses.home, poses.slots.'0', ecc.
        """
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
        """
        Placeholder: qui poi aggiungerai il comando reale per il gripper (IO digitale, URCap ecc.).
        Per ora solo print.
        """
        print("(SIM) Gripper", "CHIUSO" if state else "APERTO")

    def place_letter_in_slot(self, letter: str, slot_index: int):
        """
        Sequenza completa (logica, per ora senza gripper reale):
        1. Vai sopra sorgente lettera
        2. Scendi, prendi blocco (in futuro)
        3. Torna su
        4. Vai sopra slot
        5. Scendi, lascia blocco (in futuro)
        6. Torna su
        """

        print(f"📦 Inizio sequenza per lettera '{letter}' nello slot {slot_index}")

        # 1. Vai alla sorgente della lettera
        if self._go_to_letter_source(letter) is None:
            return

        # Qui poi userai move_relative_z + grip(True)
        # self.move_relative_z(self.z_pick_offset)
        # self.grip(True)
        # self.move_relative_z(-self.z_pick_offset)

        # 3. Vai allo slot della parola
        if self._go_to_slot(slot_index) is None:
            return

        # Qui poi userai move_relative_z + grip(False)
        # self.move_relative_z(self.z_pick_offset)
        # self.grip(False)
        # self.move_relative_z(-self.z_pick_offset)

        print("✅ Lettera (virtualmente) posizionata.")
