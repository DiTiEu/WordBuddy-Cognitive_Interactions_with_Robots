# WordBuddy: Cognitive Interactions with Robots for Educational Purposes

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Version](https://img.shields.io/badge/version-1.0.0-green)
![Status](https://img.shields.io/badge/status-complete%20MVP-brightgreen)

**WordBuddy** is an interactive robotic system designed to assist users in learning English vocabulary through physical interaction with letter blocks. The project integrates a **UR3 collaborative robot**, a custom **CNN-based computer vision pipeline**, and an adaptive **game logic engine**.

> **Project Status:** Complete MVP — Hybrid Motion Control (MoveJ/MoveL), CNN Vision System (F1-Score 0.72), 3 Game Modes.

---

## Table of Contents

- [Overview](#overview)
- [Game Modes](#game-modes)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Training the CNN](#training-the-cnn)
- [Calibration](#calibration)
- [Project Structure](#project-structure)
- [Results](#results)
- [Contributing](#contributing)
- [Citation](#citation)
- [License](#license)

---

## Overview

WordBuddy combines physical robotics with computer vision and natural language feedback to create an engaging learning experience. A child interacts with a physical board containing letter slots. The UR3 robot arm picks and places letter blocks while a camera-based CNN classifier reads the board state in real time. Text-to-speech provides spoken instructions and feedback throughout each session.

The system was developed as part of the **Cognitive Interactions with Robots** course (Erasmus programme, 2025–2026).

---

## Game Modes

### 1. Spelling Bee 🐝
The robot announces a word via TTS (the word is hidden on screen). The user must find the correct letter blocks and place them in the board slots from left to right. A contextual hint is provided.

### 2. Fill the Gap 🧩
The robot places some letters of a word on the board (configurable difficulty: easy / normal / hard) and the user must complete the remaining slots. In easy mode the robot places ~70% of the letters; in hard mode only ~30%.

### 3. Find the Error 🔍
The robot spells a word on the board with one deliberate mistake. The user must identify the wrong letter block and replace it with the correct one.

All modes share the same validation loop: the CNN reads the board after each interaction, compares the detected letters against the target word, and the robot provides spoken feedback on success or failure.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        WordBuddy System                      │
├───────────────┬──────────────────┬──────────────────────────┤
│  Robot Layer  │   Vision Layer   │       Game Layer         │
│               │                  │                          │
│  UR3 arm      │  Webcam          │  Word selection          │
│  MoveJ / MoveL│  ArUco calibration│  Difficulty control    │
│  Gripper ctrl │  Perspective warp│  3 game modes           │
│  TCP socket   │  CNN classifier  │  TTS feedback           │
│               │  (F1 = 0.72)     │  Session logging        │
└───────────────┴──────────────────┴──────────────────────────┘
```

**Key modules:**

| Module | Purpose |
|--------|---------|
| `src/new_robot_control.py` | UR3 TCP socket control, MoveJ/MoveL, gripper |
| `src/board_vision.py` | ArUco-based perspective warp, slot ROI extraction |
| `src/cnn_classifier.py` | CNN letter prediction with empty-slot heuristic |
| `src/game_logic.py` | Word selection (isograms only), difficulty splitting, error injection |
| `src/new_main.py` | Session orchestrator — ties all layers together |
| `src/utils.py` | Config and word dictionary loading |

---

## Hardware Requirements

| Component | Specification |
|-----------|--------------|
| Robot arm | Universal Robots UR3 (tested) |
| Camera | USB webcam (OpenCV-compatible) |
| Board | Physical letter-slot board with ArUco markers at corners |
| Letter blocks | 26 physical letter blocks (A–Z) |
| Network | Robot and PC on the same local network |
| PC | Windows 10/11 or Linux, Python 3.10+ |

The robot communicates via TCP socket on port `30002`. A physical E-Stop must
be within reach when running any mode that involves robot motion.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/diego-terzi/WordBuddy-Cognitive_Interactions_with_Robots.git
cd WordBuddy-Cognitive_Interactions_with_Robots
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify TTS (Windows)

`pyttsx3` uses the Windows SAPI5 engine by default. No additional setup is
needed on Windows 10/11. On Linux, install `espeak`:

```bash
sudo apt-get install espeak
```

---

## Configuration

All system parameters are in `data/config.yaml`:

```yaml
settings:
  verbose: false          # Set true to print coordinates and debug info

robot:
  ip: "10.10.73.237"      # Replace with your UR3 IP address
  port: 30002
  home_joints: [...]      # Home joint configuration

camera_id: 0              # OpenCV camera index (0 = first USB camera)

safety:
  speed: 0.2              # Robot speed (0–1)
  acc: 0.2                # Robot acceleration (0–1)
  safe_height: 0.25       # Safety clearance height (metres)

vision:
  aruco_dict: "DICT_4X4_50"
  classifier_model_path: "data/models/cnn_savedmodel"
  classifier_min_conf: 0.30
```

**Before first run:**
1. Set `robot.ip` to your UR3's IP address
2. Set `camera_id` to the correct camera index
3. Run the slot calibration script (see [Calibration](#calibration))

---

## Usage

### Run the main application

```bash
python src/new_main.py
```

The system will:
1. Connect to the UR3 robot and move to the home position
2. Initialize the vision pipeline and CNN classifier
3. Present a mode selection menu

```
┌───────────────────────────────────────────┐
│            SELECT YOUR CHALLENGE          │
└───────────────────────────────────────────┘
  [1] SPELLING BEE   🐝  (Listen and spell)
  [2] FILL THE GAP   🧩  (Complete the word)
  [3] FIND THE ERROR 🔍  (Fix my mistake)
  [Q] QUIT SESSION   👋
```

### Offline vision test (no robot required)

```bash
python scripts/test_offline_photo.py
python scripts/test_read_letters_from_image.py
```

### Benchmark the vision system

```bash
python scripts/benchmark_vision.py
```

Generates a confusion matrix and classification report saved to `data/test_logs/`.

---

## Training the CNN

The CNN classifier recognises 27 classes: empty slot (`_`) plus letters A–Z.

```bash
# 1. Collect raw slot images
python scripts/collect_dataset_slots.py

# 2. Generate augmented training data
python scripts/generate_augmented.py

# 3. Train the model (saves to data/models/cnn_savedmodel)
python scripts/train_cnn.py
```

**Training configuration** (top of `scripts/train_cnn.py`):
- Input size: 64×64 px, grayscale
- Dataset split: 80% train / 20% test
- Architecture: lightweight CNN with Conv2D + MaxPooling + Dense layers

---

## Calibration

ArUco markers at the four corners of the board are used to compute a perspective
warp transform. Run the calibration helper before first use or after moving the camera:

```bash
python scripts/calibrate_slots.py
```

Follow the on-screen instructions to define the five slot ROIs. The resulting
coordinates are written to `data/config.yaml` under `vision.slots_roi_px`.

---

## Project Structure

```text
WordBuddy-Cognitive_Interactions_with_Robots/
│
├── data/                        # Configuration and resources
│   ├── calibration/             # ArUco calibration files
│   ├── dataset_augmented/       # Augmented training images
│   ├── dataset_slots/           # Original raw slot images
│   ├── models/                  # Saved CNN model (tf.keras SavedModel)
│   ├── test_logs/               # Session logs and confusion matrices
│   ├── config.yaml              # Main system configuration
│   ├── words.json               # Word dictionary with hints
│   └── robot_performance_metrics.csv  # Session performance log
│
├── scripts/                     # Executable scripts
│   ├── benchmark_vision.py      # Generates confusion matrix and metrics
│   ├── calibrate_slots.py       # Interactive slot ROI calibration
│   ├── collect_dataset_slots.py # Training image collection tool
│   ├── generate_augmented.py    # Offline data augmentation pipeline
│   ├── train_cnn.py             # CNN training script
│   └── test_*.py                # Offline and unit tests
│
├── src/                         # Core library modules
│   ├── board_vision.py          # Perspective warp and ROI extraction
│   ├── cnn_classifier.py        # CNN inference and empty-slot heuristic
│   ├── game_logic.py            # Word selection, difficulty, error injection
│   ├── new_robot_control.py     # UR3 TCP socket control (MoveJ/MoveL)
│   ├── new_main.py              # Session orchestrator (main entry point)
│   └── utils.py                 # Config and word dictionary loading
│
├── CHANGELOG.md
├── CITATION.cff
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── NOTES.ipynb                  # Development notes
├── README.md
├── SECURITY.md
└── requirements.txt
```

---

## Results

| Metric | Value |
|--------|-------|
| CNN F1-Score (test set) | 0.72 |
| Motion control | Hybrid MoveJ / MoveL |
| Game modes | 3 (Spelling Bee, Fill the Gap, Find the Error) |
| Word dictionary | 14 entries (3–5 letter isograms) |
| Session logging | CSV (`data/robot_performance_metrics.csv`) |

---

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) for
setup instructions and contribution guidelines.

---

## Citation

If you use this work in your research, please cite it using the metadata in
[CITATION.cff](CITATION.cff) or the following reference:

```
Diego Terzi. WordBuddy: Cognitive Interactions with Robots for Educational
Purposes. GitHub, 2026. https://github.com/diego-terzi/WordBuddy-Cognitive_Interactions_with_Robots
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
