# Contributing to WordBuddy

Thank you for your interest in WordBuddy. This is an academic research project;
contributions that improve reproducibility, extend the game logic, or enhance
the vision pipeline are especially welcome.

## Prerequisites

Before contributing, make sure you can run the project locally. See the
[Installation](#installation) section in the README.

**Hardware note:** Full end-to-end testing requires a UR3 robot arm. If you do
not have access to one, the vision pipeline and game logic can be tested
independently using the offline test scripts in `scripts/`.

## Development Setup

```bash
git clone https://github.com/diego-terzi/WordBuddy-Cognitive_Interactions_with_Robots.git
cd WordBuddy-Cognitive_Interactions_with_Robots
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## Running Tests

Unit and offline tests live in `scripts/` and `src/`:

```bash
# Test the vision pipeline with a static image
python scripts/test_offline_photo.py

# Test letter reading from a saved image
python scripts/test_read_letters_from_image.py

# Test camera-based vision (requires webcam)
python scripts/test_vision.py

# Test speech output
python src/test_speech.py

# Test board warp transform
python src/test_board_warp.py
```

## Project Structure

| Directory | Contents |
|-----------|----------|
| `src/` | Core library modules (vision, CNN, robot control, game logic) |
| `scripts/` | Executable scripts for training, calibration, and testing |
| `data/` | Configuration, word dictionary, models, and logs |

## How to Contribute

1. **Fork** the repository and create a branch: `git checkout -b feature/my-feature`
2. **Make your changes** — keep each commit focused on one concern
3. **Test** with the scripts above before submitting
4. **Open a Pull Request** with a clear description of what changed and why

## Areas Where Contributions Are Welcome

- Additional words and hints in `data/words.json`
- New game modes in `src/game_logic.py`
- Improved CNN accuracy (new architectures, better augmentation)
- Support for additional robot platforms beyond UR3
- Offline/simulation mode that does not require physical hardware
- Translations of game prompts and hints

## Code Style

- Follow PEP 8 for Python code
- Keep functions small and single-purpose
- Add type hints to new functions
- Do not commit model weights (`data/models/`) or large datasets

## Reporting Issues

Please use the GitHub issue tracker. For security issues, see [SECURITY.md](SECURITY.md).
