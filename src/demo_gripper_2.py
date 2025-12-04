# src/test_gripper_down.py

from utils import load_config
from robot_control import Robot
import time

if __name__ == "__main__":
    # 1) Carica config
    config = load_config("data/config.yaml")

    # 2) Inizializza il robot
    robot = Robot(
        robot_ip=config.get("robot_ip"),
        poses=config.get("poses", {}),
        safety=config.get("safety", {})
    )

    print(">>> TEST: APRI → SCENDI → CHIUDI <<<")

    # 4) APRI pinza (usa i tuoi script pinza_open/close)
    robot.grip(False)
    time.sleep(2.0)

    # 5) SCENDI un po' in Z (es. 3 cm)
    robot.move_relative_z(-0.03)   # -0.03 m = giù di 3 cm
    time.sleep(1.0)

    # 6) CHIUDI pinza
    robot.grip(True)
    time.sleep(2.0)

    # 7) Torna su alla quota iniziale
    robot.move_relative_z(+0.03)
    time.sleep(1.0)

    robot.close()
    print("✅ Test completato.")
