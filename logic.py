import pandas as pd
import numpy as np
import random

NUM_SETS = 2000
MIN_PROCESSES = 3
MAX_PROCESSES = 20

data = []

for i in range(NUM_SETS):
    num_processes = random.randint(MIN_PROCESSES, MAX_PROCESSES)
    
    burst_times = [random.randint(1, 20) for _ in range(num_processes)]
    arrival_times = [random.randint(0, 20) for _ in range(num_processes)]
    priorities = [random.randint(1, 10) for _ in range(num_processes)]
    types = [random.choice(["CPU-bound", "IO-bound"]) for _ in range(num_processes)]
    
    # -----------------------------
    # FEATURES (Aggregated for Queue)
    # -----------------------------
    mean_burst = np.mean(burst_times)
    std_burst = np.std(burst_times)
    max_burst = np.max(burst_times)
    min_burst = np.min(burst_times)
    
    arrival_spread = np.max(arrival_times) - np.min(arrival_times)
    
    mean_priority = np.mean(priorities)
    priority_var = np.var(priorities)
    
    io_count = sum(1 for t in types if t == "IO-bound")
    pct_io_bound = io_count / num_processes
    pct_cpu_bound = 1.0 - pct_io_bound
    
    # -----------------------------
    # PROBABILISTIC LABEL ASSIGNMENT
    # -----------------------------
    if pct_io_bound >= 0.5:
        # High IO bound processes benefit from Round Robin to keep CPU busy and responsive
        best_algo = random.choices(["Round Robin", "Priority", "FCFS"], weights=[0.8, 0.1, 0.1])[0]
        
    elif priority_var > 4 and mean_priority >= 5:
        # High variance in priority implies some processes desperately need CPU before others
        best_algo = random.choices(["Priority", "SRTF", "Round Robin"], weights=[0.7, 0.2, 0.1])[0]
        
    elif std_burst > 5:
        # High variance in burst time => risk of Convoy Effect -> use SJF or SRTF
        if arrival_spread > 8:
            best_algo = random.choices(["SRTF", "SJF", "Round Robin"], weights=[0.6, 0.3, 0.1])[0]
        else:
            best_algo = random.choices(["SJF", "SRTF", "FCFS"], weights=[0.7, 0.2, 0.1])[0]
            
    else:
        # Similar burst times, mostly CPU bound, low priority variance -> FCFS is fine
        best_algo = random.choices(["FCFS", "Round Robin"], weights=[0.7, 0.3])[0]

    data.append({
        "num_processes": num_processes,
        "mean_burst": mean_burst,
        "std_burst": std_burst,
        "max_burst": max_burst,
        "min_burst": min_burst,
        "arrival_spread": arrival_spread,
        "mean_priority": mean_priority,
        "priority_var": priority_var,
        "pct_io_bound": pct_io_bound,
        "pct_cpu_bound": pct_cpu_bound,
        "best_algorithm": best_algo
    })

df = pd.DataFrame(data)
df.to_csv("workload_scheduling.csv", index=False)
print("✅ Generated workload dataset: workload_scheduling.csv")