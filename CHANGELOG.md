# Changelog

All notable changes to WordBuddy are documented in this file.

## [1.0.0] - 2026-01-21

### Added
- Three interactive game modes: Spelling Bee, Fill the Gap, Find the Error
- Hybrid UR3 motion control combining MoveJ (joint-space) and MoveL (linear)
  for safe and precise letter block manipulation
- CNN-based letter classifier (`src/cnn_classifier.py`) trained on augmented
  dataset; F1-score 0.72 on the test set
- ArUco marker-based board calibration and perspective warp pipeline
  (`src/board_vision.py`)
- Offline data augmentation pipeline (`scripts/generate_augmented.py`)
- Text-to-speech feedback via `pyttsx3` for verbal instructions and hints
- Session performance logging to `data/robot_performance_metrics.csv`
- Configuration-driven architecture via `data/config.yaml`
- Word dictionary with English vocabulary and contextual hints (`data/words.json`)
- Benchmark script for vision system evaluation (`scripts/benchmark_vision.py`)
- Slot ROI calibration helper (`scripts/calibrate_slots.py`)
- Dataset collection tool (`scripts/collect_dataset_slots.py`)
- CNN training script (`scripts/train_cnn.py`)
