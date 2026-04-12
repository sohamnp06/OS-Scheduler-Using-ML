import argparse
import json
import pickle
import pandas as pd
import numpy as np
import subprocess
import sys
from fastapi import FastAPI, HTTPException
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
MODEL_PATH = os.path.join(os.path.dirname(__file__), "scheduler_model.pkl")
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Run train_final_model.py first.")

with open(MODEL_PATH, "rb") as f:
    model_data = pickle.load(f)

pipeline = model_data["pipeline"]
le       = model_data["label_encoder"]

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
    pct_io_bound: float
    pct_cpu_bound: float

class QueuePredictionResult(BaseModel):
    predicted_algorithm: str
    reason: str
    stats: QueueStats

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def get_queue_reason(stats: QueueStats, algo: str) -> str:
    """Human-readable reasoning for the entire queue."""
    if stats.pct_io_bound >= 0.5 and algo == "Round Robin":
        return f"🌍 High I/O composition ({int(stats.pct_io_bound*100)}% I/O-bound). Round Robin is ideal for keeping the CPU busy while processes wait for I/O operations."
    
    if stats.priority_var > 4 and stats.mean_priority >= 5 and algo == "Priority":
        return f"🔴 Very high variance in priority ({stats.priority_var:.1f}). Priority scheduling is vital to ensure critical tasks can pre-empt lower priority ones."
        
    if stats.std_burst > 5 and algo in ["SJF", "SRTF"]:
        return f"⚡ Large variation in burst times. Shortest Job First / SRTF will prevent the 'Convoy Effect' where short jobs wait endlessly for a long job to finish."
        
    return f"📋 Balanced queue characteristics. {algo} offers simple, fair, and low-overhead scheduling for this standard workload mix."

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
        priority_var=float(np.var(priorities)),
        pct_io_bound=float(pct_io),
        pct_cpu_bound=float(1.0 - pct_io)
    )
    
    input_df = pd.DataFrame([stats.model_dump()])
    
    pred_idx = pipeline.predict(input_df)[0]
    algo = le.inverse_transform([pred_idx])[0]
    
    reason = get_queue_reason(stats, algo)
    
    return QueuePredictionResult(
        predicted_algorithm=algo,
        reason=reason,
        stats=stats
    )


@app.get("/")
async def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    return FileResponse(html_path)

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

    main_py = os.path.join(os.path.dirname(__file__), "main2.py")
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
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

if __name__ == "__main__":
    print("\n🚀  Open your browser at:  http://127.0.0.1:5050\n")
    uvicorn.run("app:app", host="127.0.0.1", port=5050, reload=False)
