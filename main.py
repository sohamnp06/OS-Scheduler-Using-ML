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
    # DERIVED FEATURES (SIMPLE)
    # -----------------------------

    # Short vs long job
    short_job = 1 if burst_time <= 5 else 0
    long_job = 1 - short_job

    # IO / CPU flags
    io_flag = 1 if process_type == "IO-bound" else 0
    cpu_flag = 1 - io_flag

    # Priority importance
    high_priority = 1 if priority >= 7 else 0

    # Arrival type
    dynamic_arrival = 1 if arrival_time > 10 else 0

    # -----------------------------
    # LABEL ASSIGNMENT (LOGICAL)
    # -----------------------------

    # Priority Scheduling
    if priority >= 8:
        best_algorithm = "Priority"

    # SRTF (short + dynamic)
    elif short_job == 1 and dynamic_arrival == 1:
        best_algorithm = "SRTF"

    # SJF (short + stable)
    elif short_job == 1:
        best_algorithm = "SJF"

    # Round Robin (IO or mixed behavior)
    elif io_flag == 1:
        best_algorithm = "Round Robin"

    # FCFS (default simple case)
    else:
        best_algorithm = "FCFS"

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

df.to_csv("cpu_scheduling_process.csv", index=False)

print("✅ Process-level dataset generated: cpu_scheduling_process.csv")