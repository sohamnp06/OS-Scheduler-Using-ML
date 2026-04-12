import random
import pandas as pd

# -----------------------------
# CONFIG
# -----------------------------
NUM_ROWS = 5000

# -----------------------------
# DATA GENERATION
# -----------------------------

data = []

for i in range(NUM_ROWS):

    # Generate single process
    process_id = f"P{i+1}"
    arrival_time = random.randint(0, 20)
    burst_time = random.randint(1, 20)
    priority = random.randint(1, 10)
    process_type = random.choice(["CPU-bound", "IO-bound"])

    # -----------------------------
    # DERIVED FEATURES
    # -----------------------------

    short_job = 1 if burst_time <= 5 else 0
    long_job = 1 - short_job

    io_flag = 1 if process_type == "IO-bound" else 0
    cpu_flag = 1 - io_flag

    high_priority = 1 if priority >= 7 else 0
    dynamic_arrival = 1 if arrival_time > 10 else 0

    # -----------------------------
    # PROBABILISTIC LABEL ASSIGNMENT
    # -----------------------------

    # Case 1: High priority
    if priority >= 8:
        best_algorithm = random.choices(
            ["Priority", "Round Robin", "SJF"],
            weights=[0.7, 0.2, 0.1]
        )[0]

    # Case 2: Short jobs
    elif short_job == 1:
        if dynamic_arrival == 1:
            best_algorithm = random.choices(
                ["SRTF", "SJF", "Round Robin"],
                weights=[0.6, 0.3, 0.1]
            )[0]
        else:
            best_algorithm = random.choices(
                ["SJF", "FCFS", "Round Robin"],
                weights=[0.6, 0.3, 0.1]
            )[0]

    # Case 3: IO-heavy
    elif io_flag == 1:
        best_algorithm = random.choices(
            ["Round Robin", "FCFS", "Priority"],
            weights=[0.6, 0.3, 0.1]
        )[0]

    # Case 4: Default
    else:
        best_algorithm = random.choices(
            ["FCFS", "Round Robin", "SJF"],
            weights=[0.6, 0.3, 0.1]
        )[0]

    # -----------------------------
    # STORE ROW
    # -----------------------------

    row = {
        "process_id": process_id,
        "arrival_time": arrival_time,
        "burst_time": burst_time,
        "priority": priority,
        "process_type": process_type,

        # derived features
        "short_job": short_job,
        "long_job": long_job,
        "io_flag": io_flag,
        "cpu_flag": cpu_flag,
        "high_priority": high_priority,
        "dynamic_arrival": dynamic_arrival,

        # target
        "best_algorithm": best_algorithm
    }

    data.append(row)

# -----------------------------
# SAVE TO CSV
# -----------------------------

df = pd.DataFrame(data)

df.to_csv("cpu_scheduling_process_v2.csv", index=False)

print("✅ Improved dataset generated: cpu_scheduling_process_v2.csv")