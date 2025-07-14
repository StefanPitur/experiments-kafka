import pandas as pd
import matplotlib.pyplot as plt

# Define file paths for each producer CSV
files = {
    "producer1": "producer1-perf.csv",
    "producer2": "producer2-perf.csv",
    "producer3": "producer3-perf.csv",
}

# Read and preprocess all data once, then compute a 1-minute rolling average to smooth
data = {}
for name, path in files.items():
    df = pd.read_csv(path)
    df["timestamp_ms"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
    df.set_index("timestamp_ms", inplace=True)
    # 1-minute time-based rolling mean for smoothing
    df["p95_smooth"] = df["p95"].rolling("30s").mean()
    df["p99_smooth"] = df["p99"].rolling("30s").mean()
    data[name] = df

# Generate and save smoothed plots for both p95 and p99
for metric in ["p95", "p99"]:
    smooth_col = f"{metric}_smooth"
    plt.figure(figsize=(12, 6))
    for name, df in data.items():
        plt.plot(df.index, df[smooth_col], label=name)
    plt.xlabel("Timestamp")
    plt.ylabel(f"{metric.upper()} Value (1-min Rolling Avg)")
    plt.title(f"{metric.upper()} Latency Over Time (Smoothed)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{metric}_latency_smoothed.png")
    plt.close()

print(
    "Saved smoothed plots as 'p95_latency_smoothed.png' and 'p99_latency_smoothed.png'."
)
