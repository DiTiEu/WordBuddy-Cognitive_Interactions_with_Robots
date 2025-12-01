# src/demo_pick_place.py

import os
from utils import load_config
from robot_control import Robot


def main():
    print("=== DEMO PICK & PLACE WordBuddy ===")

    # 1) Carica configurazione
    config_path = os.path.join("data", "config.yaml")
    config = load_config(config_path)

    safety = config.get("safety", {})
    poses = config.get("poses", {})

    # 2) Inizializza il robot
    robot = Robot(
        robot_ip=config.get("robot_ip"),
        poses=poses,
        safety=safety
    )

    # Se la connessione fallisce, Robot va in modalità simulata.
    # Va comunque bene per far vedere la sequenza di comandi.

    try:
        # --- STEP 1: Vai in HOME ---
        print("\n[STEP 1] Vado in HOME")
        if "home" in poses:
            robot.move_to_pose("home")
        else:
            print("⚠️ Pose 'home' non definita in config.yaml")

        # --- STEP 2: Vai sopra il blocco sorgente (useremo A) ---
        print("\n[STEP 2] Vado sopra la sorgente della lettera A")
        source_A = poses.get("letter_sources", {}).get("A")
        if source_A is None:
            print("⚠️ Nessuna pose per letter_sources.A trovata!")
            return

        robot.move_joints(source_A)

        # --- STEP 3: Scendi per prendere il blocco ---
        print("\n[STEP 3] Scendo per prendere il blocco")
        dz = robot.z_pick_offset  # es. -0.04 → scende di 4 cm
        robot.move_relative_z(dz)

        # --- STEP 4: Chiudi gripper (simulato) ---
        print("\n[STEP 4] Chiudo il gripper (simulato)")
        robot.grip(True)

        # --- STEP 5: Risalgo ---
        print("\n[STEP 5] Risalgo")
        robot.move_relative_z(-dz)

        # --- STEP 6: Torno in HOME con il blocco ---
        print("\n[STEP 6] Torno in HOME con il blocco")
        if "home" in poses:
            robot.move_to_pose("home")

        # --- STEP 7: Vado sopra lo SLOT 1 ---
        print("\n[STEP 7] Vado sopra lo slot 1")
        slot1 = poses.get("slots", {}).get("1")
        if slot1 is None:
            print("⚠️ Nessuna pose per slots.\"1\" trovata!")
            return

        robot.move_joints(slot1)

        # --- STEP 8: Scendo per depositare il blocco ---
        print("\n[STEP 8] Scendo per depositare il blocco")
        robot.move_relative_z(dz)

        # --- STEP 9: Apro il gripper (rilascio) ---
        print("\n[STEP 9] Apro il gripper (simulato)")
        robot.grip(False)

        # --- STEP 10: Risalgo ---
        print("\n[STEP 10] Risalgo")
        robot.move_relative_z(-dz)

        # --- STEP 11: Torno in HOME ---
        print("\n[STEP 11] Torno in HOME")
        if "home" in poses:
            robot.move_to_pose("home")

        print("\n✅ DEMO completata con successo.")

    finally:
        robot.close()


if __name__ == "__main__":
    main()
