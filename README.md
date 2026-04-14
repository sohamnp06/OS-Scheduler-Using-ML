# Intelligent OS Workload Scheduler & Simulator

## Overview
This project is an advanced Operating Systems simulation environment that leverages Machine Learning to solve the classic CPU scheduling problem. While traditional schedulers use static, hard-coded rules, this system treats the process queue as a dynamic workload, using a trained model to analyze the statistical characteristics of the entire queue and predict the optimal scheduling algorithm.

The system is split into a robust **FastAPI backend** for ML-driven intelligence and a high-performance **Pygame simulation engine** for visual verification of scheduling logic.

---

## Core Components

### 1. ML Prediction Engine (`app.py`)
A FastAPI-powered server that analyzes incoming process workloads. It performs real-time feature engineering to extract macro-level statistics from the process queue, including:
- **Mean Burst Time**: Represents the average computational load per process.
- **Burst Standard Deviation**: Measures the variance in task sizes to detect potential "convoy effects."
- **Arrival Spread**: Evaluates the temporal distribution of incoming tasks.
- **Priority Variance**: Determines the critical nature of the workload based on task importance levels.

### 2. Interactive Dashboard (`frontend/`)
A premium, dark-themed management interface designed for high clarity and data density.
- **Dynamic Queue Management**: Add, remove, and manage processes in real-time.
- **Live ML Diagnostics**: View predicted algorithms with logical reasoning provided by the model.
- **Queue Characteristic Popups**: Click on any workload metric to see a detailed explanation of its calculation and impact on scheduling.
- **Clean Aesthetic**: A professional, emoji-free interface focused on data visualization.

### 3. Simulation Engine (`main.py`)
A specialized Pygame-based visualizer that brings the predicted algorithm to life.
- **Smooth Animations**: Watch processes migrate from the Ready Queue to the CPU with frame-independent movement.
- **Real-Time Gantt Data**: See turnaround times and waiting times calculated live during the simulation.
- **Multiple Algorithm Support**: Fully implemented logic for FCFS, SJF, SRTF, Round Robin, and Priority Scheduling.

---

## Supported Scheduling Algorithms

- **FCFS (First-Come, First-Served)**: Optimal for workloads with similar burst times and low arrival density.
- **SJF (Shortest Job First)**: Minimizes average waiting time by prioritizing shorter tasks in non-preemptive scenarios.
- **SRTF (Shortest Remaining Time First)**: The preemptive version of SJF, ideal for environments with frequent new task arrivals.
- **Round Robin (RR)**: Ensures fairness and responsiveness in time-sharing environments.
- **Priority Scheduling**: Guarantees that critical system tasks obtain the CPU before lower-priority processes.

---

## Getting Started

### Prerequisites
- Python 3.9 or higher
- `pip` package manager

### Installation
1. Navigate to the project directory:
   ```bash
   cd OS-Scheduler-Using-ML
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application
To start the integrated environment:
1. Launch the backend server:
   ```bash
   python app.py
   ```
2. Open your web browser and navigate to:
   **`http://127.0.0.1:5051`**
3. Add your desired processes to the queue and click **"Predict Workload Algorithm"**.
4. Click **"Run Simulation"** to launch the Pygame visualizer and watch the algorithm in action.

---

## Project Structure
- `app.py`: FastAPI server and ML inference logic.
- `main.py`: Pygame simulation and scheduling implementation.
- `frontend/`: HTML, CSS, and Vanilla JS for the web dashboard.
- `artifacts/`: Contains the trained `scheduler_model.pkl` and feature scaling data.
- `notebooks/`: Exploratory Data Analysis (EDA) and model training experiments.
- `logic.py`: Core logic for feature extraction and data generation.

---

## License
MIT License - Developed for OS Scheduling education and ML integration research.
