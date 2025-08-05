import pandas as pd, numpy as np

df = pd.read_csv("experiments/low_latency_pipeline/p0/e2e-latencies.csv")

offset_us = df.loc[df["lat_ms"] < 0, "lat_ms"].mean() * 1000
print(f"Estimated clock offset: {offset_us:.1f} µs")

df["lat_ms_adj"] = df["lat_ms"] + offset_us/1000.0

df["lat_ms_adj"] = df["lat_ms_adj"].clip(lower=0)

df.to_csv("adjusted-e2e-latencies.csv")

print(df["lat_ms_adj"].quantile([0.50, 0.95, 0.99]))
