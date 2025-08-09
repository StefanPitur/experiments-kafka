import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# --- 1) Load your data ---
# Change these to match your file & column name
csv_path = "experiments/low_latency_pipeline_new/p0/logs/cons-81147-1.csv"
latency_col = "latency_ms"   # e.g. "latency_ms" or "latency"

df = pd.read_csv(csv_path, skiprows=range(1, 100_001))
s = pd.to_numeric(df[latency_col], errors="coerce").dropna()
s = s[s >= 0]  # keep non-negative latencies

# --- 2) Compute percentiles ---
qs = [0.95, 0.99]
q_vals = s.quantile(qs)
print(q_vals)  # p95/p99 values

# --- 3a) Histogram with percentile markers ---
plt.figure()
plt.hist(s, bins=50)
for q, v in q_vals.items():
    plt.axvline(v, linestyle="--", color="red")
    plt.text(v, plt.ylim()[1]*0.9, f"p{int(q*100)}={v:.2f}", rotation=90, va="top", ha="right", color="red")
plt.xlabel("Latency")
plt.ylabel("Count")
plt.title("Latency Histogram with p95/p99")
plt.tight_layout()
plt.show()

# --- 3b) ECDF (good for seeing the whole distribution) ---
x = np.sort(s.values)
y = np.arange(1, len(x) + 1) / len(x)

plt.figure()
plt.plot(x, y, drawstyle="steps-post")
for q, v in q_vals.items():
    plt.axvline(v, linestyle="--", color="red")
    plt.text(v, 0.02, f"p{int(q*100)}={v:.2f}", rotation=90, va="bottom", ha="right", color="red")
plt.xlabel("Latency")
plt.ylabel("Cumulative probability")
plt.title("Latency ECDF with p95/p99")
plt.tight_layout()
plt.show()

# --- 3c) Bar chart of the three percentiles ---
plt.figure()
labels = [f"p{int(q*100)}" for q in qs]
plt.bar(labels, [q_vals.loc[q] for q in qs])
plt.ylabel("Latency")
plt.title("Latency percentiles")
plt.tight_layout()
plt.show()
