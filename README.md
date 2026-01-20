# WordBuddy: Cognitive Interactions with Robots for Educational Purposes

**WordBuddy** is an interactive robotic system designed to assist users in learning English vocabulary through physical interaction with letter blocks. The project integrates a **UR3 collaborative robot**, a custom **CNN-based computer vision pipeline**, and an adaptive **game logic engine**.

> **Project Status:** Complete MVP with Hybrid Motion Control (MoveJ/MoveL), CNN Vision System (F1-Score 0.72), and 3 Game Modes.

---

## 📂 Project Structure

The repository is organized into three main directories separating data, executable scripts, and core source code.

```text
WORDBUDDY-COGNITIVE_INTERACTIONS_WITH_ROBOTS/
│
├── data/                        # Configuration and Resources
│   ├── calibration/             # ArUco calibration files
│   ├── dataset_augmented/       # Training images (augmented)
│   ├── dataset_slots/           # Original raw images
│   ├── models/                  # Saved CNN model (tf.keras)
│   ├── test_logs/               # Session logs and Confusion Matrices
│   ├── config.yaml              # Main system configuration
│   └── words.json               # Dictionary of words and hints
│
├── scripts/                     # Executable Scripts
│   ├── benchmark_vision.py      # Generates Confusion Matrix & Metrics
│   ├── calibrate_slots.py       # Helper to define slot ROIs
│   ├── collect_dataset_slots.py # Tool to capture training images
│   ├── generate_augmented.py    # Offline Data Augmentation pipeline
│   ├── main.py                  # MAIN ENTRY POINT of the application
│   ├── train_cnn.py             # Script to train the Neural Network
│   └── test_*.py                # Various unit tests
│
├── src/                         # Core Library Modules
│   ├── board_vision.py          # Perspective warping & ROI extraction
│   ├── cnn_classifier.py        # CNN prediction & Empty heuristic
│   ├── game_logic.py            # Word selection & Game modes
│   ├── new_robot_control.py     # Hybrid UR3 control (Socket/URScript)
│   ├── new_main.py              # Logic coordinator
│   └── utils.py                 # File I/O and helper functions
│
├── NOTES.ipynb                  # Jupyter Notebook for dev notes
└── README.md                    # Project Documentation