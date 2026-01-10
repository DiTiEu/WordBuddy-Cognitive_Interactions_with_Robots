import json
import argparse
import statistics
from collections import defaultdict, Counter
from pathlib import Path

def safe_mean(xs):
    return sum(xs) / len(xs) if xs else None

def safe_stdev(xs):
    return statistics.stdev(xs) if len(xs) >= 2 else None

def load_jsonl(path: Path):
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"⚠️ Skipping invalid JSON at line {line_no}")
    return events

def group_by_trial(events):
    by_trial = defaultdict(list)
    for e in events:
        tid = e.get("trial_id", "UNKNOWN_TRIAL")
        by_trial[tid].append(e)
    for tid in by_trial:
        by_trial[tid].sort(key=lambda x: x.get("ts", 0))
    return by_trial

def extract_trial_metrics(trial_events):
    times = defaultdict(list)
    robot_errors = 0
    human_help = 0
    final_success = None

    for e in trial_events:
        ev = e.get("event")
        meta = e.get("meta", {}) or {}
        ts = e.get("ts")
        if ev and ts is not None:
            times[ev].append(ts)

        if ev == "robot_error":
            robot_errors += 1
        if ev == "human_help":
            human_help += 1
        if ev == "trial_end" and "final_success" in meta:
            final_success = bool(meta["final_success"])

    completion_time = None
    if times["trial_start"] and times["trial_end"]:
        completion_time = times["trial_end"][-1] - times["trial_start"][0]

    pick_times = []
    if len(times["robot_pick_start"]) == len(times["robot_pick_end"]) and times["robot_pick_start"]:
        for s, e in zip(times["robot_pick_start"], times["robot_pick_end"]):
            pick_times.append(e - s)

    place_times = []
    if len(times["robot_place_start"]) == len(times["robot_place_end"]) and times["robot_place_start"]:
        for s, e in zip(times["robot_place_start"], times["robot_place_end"]):
            place_times.append(e - s)

    return {
        "completion_time": completion_time,
        "pick_times": pick_times,
        "place_times": place_times,
        "robot_error_count": robot_errors,
        "human_help_count": human_help,
        "final_success": final_success,
    }

def confusion_from_events(events, task_name):
    labels = set()
    matrix = Counter()

    for e in events:
        if e.get("event") != "vision_pred":
            continue
        meta = e.get("meta", {}) or {}
        if meta.get("task") != task_name:
            continue
        t = meta.get("true")
        p = meta.get("pred")
        if t is None or p is None:
            continue
        labels.add(t); labels.add(p)
        matrix[(t, p)] += 1

    labels = sorted(labels)
    return labels, matrix

def print_confusion(labels, matrix, title):
    if not labels:
        print(f"\n{title}: (no data)")
        return
    print(f"\n{title} (rows=true, cols=pred)")
    header = "true\\pred," + ",".join(labels)
    print(header)
    for t in labels:
        row = [str(matrix.get((t, p), 0)) for p in labels]
        print(t + "," + ",".join(row))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default="Log/events.jsonl", help="Path to JSONL log file")
    parser.add_argument("--out", default="Log/metrics_summary.json", help="Output metrics summary JSON")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {log_path}")

    events = load_jsonl(log_path)
    by_trial = group_by_trial(events)

    completion_times = []
    all_pick_times = []
    all_place_times = []
    successes = []
    robot_errors_total = 0
    human_help_total = 0
    trials_with_success_flag = 0

    per_trial = {}

    for tid, tevents in by_trial.items():
        m = extract_trial_metrics(tevents)
        per_trial[tid] = m

        if m["completion_time"] is not None:
            completion_times.append(m["completion_time"])
        all_pick_times.extend(m["pick_times"])
        all_place_times.extend(m["place_times"])

        if m["final_success"] is not None:
            trials_with_success_flag += 1
            successes.append(1 if m["final_success"] else 0)

        robot_errors_total += m["robot_error_count"]
        human_help_total += m["human_help_count"]

    success_rate = safe_mean(successes) if successes else None
    completion_mean = safe_mean(completion_times)
    completion_std = safe_stdev(completion_times)  # temporal jitter
    pick_mean = safe_mean(all_pick_times)
    pick_std = safe_stdev(all_pick_times)
    place_mean = safe_mean(all_place_times)
    place_std = safe_stdev(all_place_times)

    n_trials = len(by_trial)
    robot_errors_per_trial = robot_errors_total / n_trials if n_trials else None
    human_help_per_trial = human_help_total / n_trials if n_trials else None

    summary = {
        "n_trials": n_trials,
        "n_trials_with_success_flag": trials_with_success_flag,
        "task_success_rate": success_rate,
        "task_completion_time_mean_s": completion_mean,
        "task_completion_time_std_s": completion_std,
        "robot_pick_time_mean_s": pick_mean,
        "robot_pick_time_std_s": pick_std,
        "robot_place_time_mean_s": place_mean,
        "robot_place_time_std_s": place_std,
        "robot_error_total": robot_errors_total,
        "robot_error_per_trial": robot_errors_per_trial,
        "human_help_total": human_help_total,
        "human_help_per_trial": human_help_per_trial,
    }

    print("\n=== WordBuddy Metrics Report ===")
    print(f"Trials: {n_trials}")
    if success_rate is not None:
        print(f"Task Success Rate: {success_rate*100:.1f}%")
    if completion_mean is not None:
        print(f"Task Completion Time: {completion_mean:.2f}s  (std={completion_std:.2f}s)")
    if pick_mean is not None:
        print(f"Pick Time: {pick_mean:.2f}s  (std={pick_std:.2f}s)")
    if place_mean is not None:
        print(f"Place Time: {place_mean:.2f}s  (std={place_std:.2f}s)")
    print(f"Robot Errors: total={robot_errors_total}  per_trial={robot_errors_per_trial:.2f}")
    print(f"Human Help:  total={human_help_total}  per_trial={human_help_per_trial:.2f}")

    labels_slot, mat_slot = confusion_from_events(events, "slot_occupied")
    print_confusion(labels_slot, mat_slot, "Slot Occupancy Confusion Matrix")

    labels_ocr, mat_ocr = confusion_from_events(events, "ocr")
    print_confusion(labels_ocr, mat_ocr, "OCR Confusion Matrix")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "per_trial": per_trial}, f, indent=2)
    print(f"\n✅ Saved summary to: {out_path}")

if __name__ == "__main__":
    main()
