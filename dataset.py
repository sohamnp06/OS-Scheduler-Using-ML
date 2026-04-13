import random
import numpy as np
import pandas as pd
from scipy.stats import skew

# -----------------------------
# CONFIG
# -----------------------------
NUM_ROWS = 12000
MIN_PROCESSES = 3
MAX_PROCESSES = 10

# -----------------------------
# SAFE SKEW FUNCTION
# -----------------------------
def safe_skew(arr):
    if np.std(arr) < 1e-6:
        return 0
    return skew(arr)

# -----------------------------
# PROCESS GENERATION
# -----------------------------
def generate_processes():
    n = random.randint(MIN_PROCESSES, MAX_PROCESSES)
    processes = []

    pattern_type = random.choice([
        "uniform",
        "short_heavy",
        "long_heavy",
        "mixed"
    ])

    for i in range(n):
        if pattern_type == "short_heavy":
            burst = random.randint(1, 8)
        elif pattern_type == "long_heavy":
            burst = random.randint(10, 20)
        elif pattern_type == "mixed":
            burst = random.choice([
                random.randint(1, 6),
                random.randint(10, 20)
            ])
        else:
            burst = random.randint(1, 20)

        process = {
            "pid": i,
            "arrival_time": random.randint(0, 20),
            "burst_time": burst,
            "priority": random.randint(1, 10)
        }

        processes.append(process)

    return processes

# -----------------------------
# FEATURE ENGINEERING
# -----------------------------
def compute_features(processes):
    burst_times = np.array([p["burst_time"] for p in processes])
    arrivals = np.array([p["arrival_time"] for p in processes])
    priorities = np.array([p["priority"] for p in processes])

    avg_bt = np.mean(burst_times)
    total = len(processes)

    short_jobs = np.sum(burst_times < avg_bt)
    long_jobs = np.sum(burst_times >= avg_bt)

    features = {
        "num_processes": total,
        "avg_burst_time": avg_bt,
        "burst_time_variance": np.var(burst_times),
        "short_job_ratio": short_jobs / total,
        "long_job_ratio": long_jobs / total,
        "priority_variance": np.var(priorities),
        "arrival_irregularity": np.var(arrivals),

        # Advanced features
        "burst_time_skewness": safe_skew(burst_times),
        "arrival_range": np.max(arrivals) - np.min(arrivals),
        "max_min_burst_ratio": np.max(burst_times) / np.min(burst_times)
    }

    return features

# -----------------------------
# LABEL LOGIC (BALANCED)
# -----------------------------
def assign_label(f):
    short = f["short_job_ratio"]
    arrival_var = f["arrival_irregularity"]
    priority_var = f["priority_variance"]
    burst_var = f["burst_time_variance"]
    skewness = f["burst_time_skewness"]
    ratio = f["max_min_burst_ratio"]
    n = f["num_processes"]

    # PRIORITY (reduced dominance)
    if priority_var > 9 and n > 5:
        return "Priority"

    # SRTF (boosted slightly)
    if short > 0.6 and (arrival_var > 20 or skewness > 0.8):
        return "SRTF"

    # SJF
    if short > 0.6 and arrival_var <= 20:
        return "SJF"

    # ROUND ROBIN (controlled)
    if (burst_var > 60 and arrival_var > 35) or ratio > 12:
        return "Round Robin"

    # FCFS (boosted)
    if burst_var < 25 and arrival_var < 20 and ratio < 4:
        return "FCFS"

    # fallback (minimal randomness)
    return random.choice(["Round Robin", "SJF", "FCFS"])

# -----------------------------
# SERIALIZATION
# -----------------------------
def serialize(processes):
    return "|".join([
        f"{p['pid']}:{p['arrival_time']}:{p['burst_time']}:{p['priority']}"
        for p in processes
    ])

# -----------------------------
# DATASET GENERATION
# -----------------------------
data = []

for _ in range(NUM_ROWS):
    processes = generate_processes()
    features = compute_features(processes)
    label = assign_label(features)

    row = {
        "processes": serialize(processes),
        **features,
        "best_algorithm": label
    }

    data.append(row)

df = pd.DataFrame(data)

# -----------------------------
# SAVE CSV
# -----------------------------
df.to_csv("os_scheduling_dataset_final.csv", index=False)

# -----------------------------
# CHECK DISTRIBUTION
# -----------------------------
print("✅ Dataset generated successfully!")
print(df["best_algorithm"].value_counts(normalize=True) * 100)