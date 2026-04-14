import json
import numpy as np
import subprocess
import sys
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import uvicorn
import os

# ─────────────────────────────────────────────
# Load Model
# ─────────────────────────────────────────────
import joblib
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "artifacts", "scheduler_model.pkl")
FEAT_PATH = os.path.join(os.path.dirname(__file__), "artifacts", "feature_columns.pkl")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run train_final_model.py first.")

model = joblib.load(MODEL_PATH)
feature_columns = joblib.load(FEAT_PATH)

app = FastAPI(title="OS Scheduler Predictor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────
class Process(BaseModel):
    id: str
    arrival_time: float
    burst_time: float
    priority: int
    process_type: str

class QueueStats(BaseModel):
    num_processes: int
    mean_burst: float
    std_burst: float
    max_burst: float
    min_burst: float
    arrival_spread: float
    mean_priority: float
    priority_var: float


class QueuePredictionResult(BaseModel):
    predicted_algorithm: str
    reason: str
    stats: QueueStats

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def get_queue_reason(stats: QueueStats, algo: str) -> str:
    """Human-readable reasoning for the entire queue."""
    if algo == "FCFS":
        return "Selected because processes follow arrival order and burst times are similar, so simple execution avoids unnecessary overhead."
    if algo == "SJF":
        return "Selected because burst times vary significantly, so executing shorter jobs first minimizes average waiting time."
    if algo == "SRTF" or algo == "SRTN":
        return "Selected because new short processes arrive frequently, so preempting longer jobs improves response time."
    if algo == "RR" or algo == "Round Robin":
        return "Selected because all processes need fair CPU sharing and responsiveness in a time-sharing environment."
    if algo == "PRIORITY" or algo == "Priority":
        return "Selected because processes have different importance levels, so higher priority tasks must execute first."
    
    return f"Selected {algo} based on optimal feature combination for this workload."


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────
@app.post("/predict", response_model=QueuePredictionResult)
async def predict_queue(processes: List[Process]):
    if not processes:
        return QueuePredictionResult(
            predicted_algorithm="N/A",
            reason="Empty queue.",
            stats=QueueStats(**{k:0 for k in QueueStats.model_fields.keys()})
        )
        
    num_processes = len(processes)
    burst_times = [p.burst_time for p in processes]
    arrival_times = [p.arrival_time for p in processes]
    priorities = [p.priority for p in processes]
    
    io_count = sum(1 for p in processes if p.process_type == "IO-bound")
    pct_io = io_count / num_processes
    
    # Calculate features
    stats = QueueStats(
        num_processes=num_processes,
        mean_burst=float(np.mean(burst_times)),
        std_burst=float(np.std(burst_times)),
        max_burst=float(np.max(burst_times)),
        min_burst=float(np.min(burst_times)),
        arrival_spread=float(np.max(arrival_times) - np.min(arrival_times)),
        mean_priority=float(np.mean(priorities)),
        priority_var=float(np.var(priorities))
    )

    
    from scipy.stats import skew
    def safe_skew(arr):
        if np.std(arr) < 1e-6:
            return 0.0
        return float(skew(arr))
    
    avg_bt = float(np.mean(burst_times))
    total = num_processes
    short_jobs = np.sum(np.array(burst_times) < avg_bt)
    long_jobs = np.sum(np.array(burst_times) >= avg_bt)

    features = {
        "num_processes": total,
        "avg_burst_time": avg_bt,
        "burst_time_variance": float(np.var(burst_times)),
        "short_job_ratio": float(short_jobs / total),
        "long_job_ratio": float(long_jobs / total),
        "priority_variance": float(np.var(priorities)),
        "arrival_irregularity": float(np.var(arrival_times)),
        "burst_time_skewness": safe_skew(burst_times),
        "arrival_range": float(np.max(arrival_times) - np.min(arrival_times)),
        "max_min_burst_ratio": float(np.max(burst_times) / np.min(burst_times)) if np.min(burst_times) > 0 else 1.0
    }
    
    input_vector = [features[col] for col in feature_columns]
    algo = model.predict([input_vector])[0]
    
    reason = get_queue_reason(stats, algo)
    
    return QueuePredictionResult(
        predicted_algorithm=algo,
        reason=reason,
        stats=stats
    )


@app.get("/")
async def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    return FileResponse(html_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"})


@app.post("/run-simulation")
async def run_simulation(processes: List[Process]):
    if not processes:
        raise HTTPException(status_code=400, detail="No processes provided for simulation.")

    result = await predict_queue(processes)

    state = {
        "processes": [p.model_dump() for p in processes],
        "algorithm": result.predicted_algorithm,
        "reason": result.reason,
    }

    state_path = os.path.join(os.path.dirname(__file__), "simulation_state.json")
    with open(state_path, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file, indent=2)

    main_py = os.path.join(os.path.dirname(__file__), "main.py")
    launch_args = [sys.executable, main_py, "--state", state_path]
    popen_args = {
        "cwd": os.path.dirname(__file__),
        "shell": False,
        "close_fds": True,
    }

    if sys.platform == "win32":
        popen_args["creationflags"] = subprocess.CREATE_NEW_CONSOLE

    subprocess.Popen(launch_args, **popen_args)

    return {"started": True, "message": "Simulation launched locally.", "state_file": state_path}

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR, html=False), name="static")

if __name__ == "__main__":
    print("\nRunning server at: http://127.0.0.1:5050\n")
    uvicorn.run("app:app", host="127.0.0.1", port=5050, reload=False)

