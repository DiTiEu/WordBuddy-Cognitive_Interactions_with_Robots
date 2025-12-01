from robot_control import Robot
from utils import load_config

config = load_config("data/config.yaml")
robot = Robot(config["robot_ip"], config["poses"], config["safety"])

robot.grip(False)   # apri
robot.grip(True)    # chiudi

robot.close()
