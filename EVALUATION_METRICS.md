# WordBuddy – Evaluation Metrics, Logging, and Questionnaires

This document defines the evaluation methodology for the WordBuddy system.
It includes:
- logging specification (JSONL),
- quantitative metrics (robot/task/vision),
- qualitative measures (questionnaires),
- and how each metric is computed.

---

## 1) Logging Specification (JSONL)

**Format:** JSON Lines (JSONL)  
**Location:** `Log/events.jsonl`

Each line is a JSON object.

### Required fields
- `ts` (float): timestamp (seconds)
- `trial_id` (string): trial identifier (e.g., `Test_1`)
- `event` (string): event name
- `meta` (object): additional metadata

### Core events
- `trial_start`
- `robot_pick_start`, `robot_pick_end`
- `robot_place_start`, `robot_place_end`
- `trial_end` with `meta.final_success` (true/false)

### Optional events
- `robot_error` with `meta.type` (e.g., `drop`, `grip_fail`, `misplace`, `protective_stop`)
- `human_help` (human intervention)
- `vision_pred` with `meta.task` and `meta.true/pred`:
  - Slot occupancy:
    ```json
    {"event":"vision_pred","meta":{"task":"slot_occupied","true":"occupied","pred":"empty"}}
    ```
  - OCR:
    ```json
    {"event":"vision_pred","meta":{"task":"ocr","true":"B","pred":"D"}}
    ```

---

## 2) Quantitative Metrics (computed from logs)

The analysis script `src/analyze_logs.py` computes and saves metrics in:
- `Log/metrics_summary.json`

### 2.1 Task Success Rate
**Definition**
SuccessRate = (# successful trials) / (# trials with success flag)

**Source**
- `trial_end.meta.final_success`

**Interpretation**
Higher success rate indicates better usability and system reliability.

---

### 2.2 Task Completion Time
**Definition**
T_task = ts(trial_end) − ts(trial_start)

Computed per trial, then aggregated as:
- mean(T_task)
- std(T_task)

**Interpretation**
Shorter times indicate more efficient interaction.

---

### 2.3 Pick Time
**Definition**
T_pick = ts(robot_pick_end) − ts(robot_pick_start)

Aggregated as mean ± std over all pick actions.

**Interpretation**
Measures robot manipulation efficiency and consistency during the pick phase.

---

### 2.4 Place Time
**Definition**
T_place = ts(robot_place_end) − ts(robot_place_start)

Aggregated as mean ± std over all place actions.

**Interpretation**
Measures robot efficiency and stability during placement.

---

### 2.5 Temporal Jitter (Execution Variability)
**Definition**
Jitter_task = std(T_task)

**Interpretation**
Lower jitter implies predictable and consistent behavior, improving perceived safety and trust.

---

### 2.6 Robot Error Rate
**Definition**
RobotErrorPerTrial = (# robot_error events) / (# trials)

**Interpretation**
Measures robustness. Helps identify failure modes (drops, misplacements, etc.).

---

### 2.7 Human Help Rate
**Definition**
HumanHelpPerTrial = (# human_help events) / (# trials)

**Interpretation**
Proxy for usability breakdowns and need for external assistance.

---

## 3) Vision Metrics (optional, if vision_pred events are available)

### 3.1 Slot Occupancy Confusion Matrix
Binary classification: empty vs occupied

Counts:
- TP: true occupied, predicted occupied
- TN: true empty, predicted empty
- FP: true empty, predicted occupied
- FN: true occupied, predicted empty

**Accuracy**
Accuracy = (TP + TN) / (TP + TN + FP + FN)

**False Negative Rate**
FNR = FN / (FN + TP)

**False Positive Rate**
FPR = FP / (FP + TN)

---

### 3.2 OCR Confusion Matrix
Multi-class classification for letters (A–Z)

**Overall Accuracy**
Acc = (# correct predictions) / (# total predictions)

**Interpretation**
Explains recognition errors (e.g., B↔D confusion).

---

## 4) Questionnaire-based Metrics (USUS + SUS)

Questionnaires capture subjective HRI dimensions.
All Likert items use 1–5 scale (Strongly disagree → Strongly agree).

### 4.1 USUS Short (8 items)
Mapped to USUS dimensions:

**Usability**
- U1: Task was easy to understand
- U2: Steps were clear and predictable

**User Experience**
- UX1: Interaction was engaging
- UX2: Interaction was enjoyable

**Social Acceptance**
- SA1: Felt safe near the robot
- SA2: Trusted the robot actions

**Educational / Social Impact (light)**
- SI1: Physical blocks improved focus vs screen
- SI2: Robot feedback supported completion

**Scoring**
Compute mean score per dimension, e.g.:
UsabilityScore = mean(U1, U2)

---

### 4.2 SUS (10 items)
Standard usability questionnaire producing a score 0–100.

**Interpretation**
Provides a widely known usability benchmark.

(Optional in this course if USUS is the primary framework.)

---

### 4.3 Open-ended Questions
Qualitative insight:
- confusion points,
- what users liked,
- improvement suggestions.

Use thematic grouping (e.g., feedback timing, motion safety, clarity of task).

---

## 5) Peer Evaluation Protocol (15–20 min per participant)

1. Briefing (1 min): explain task and safety.
2. Trials (8–10 min): 3 trials (easy/normal/hard) OR repeated identical trial.
3. Questionnaire (5 min): Google Form (USUS + SUS + open).
4. Debrief (2 min): short verbal feedback, note key points.

---

## 6) Running the analysis

```bash
python src/analyze_logs.py --log Log/events.jsonl --out Log/metrics_summary.json
