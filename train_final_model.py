import pandas as pd
import numpy as np
import pickle
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import os

try:
    df = pd.read_csv("workload_scheduling.csv")
except FileNotFoundError:
    print("Generating dataset...")
    import subprocess
    subprocess.run(["python", "logic.py"])
    df = pd.read_csv("workload_scheduling.csv")

numerical_features = [
    "num_processes",
    "mean_burst",
    "std_burst",
    "max_burst",
    "min_burst",
    "arrival_spread",
    "mean_priority",
    "priority_var",
    "pct_io_bound",
    "pct_cpu_bound"
]

X = df[numerical_features]

le = LabelEncoder()
y = le.fit_transform(df["best_algorithm"])

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), numerical_features)
    ]
)

rf_model = RandomForestClassifier(n_estimators=100, random_state=42)

pipeline = Pipeline(steps=[
    ("preprocessing", preprocessor),
    ("model", rf_model)
])

print("Training workload model...")
pipeline.fit(X, y)
print("Model trained.")

model_data = {
    "pipeline": pipeline,
    "label_encoder": le,
    "features": numerical_features
}

with open("scheduler_model.pkl", "wb") as f:
    pickle.dump(model_data, f)

print("✅ Model and metadata saved to scheduler_model.pkl")
