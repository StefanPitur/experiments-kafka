
# Kafka Firehose Test: Experiment Matrix & Setup Guide

Below is a practical “menu” of producer × broker settings you can mix-and-match for the sustained fire-hose test.  
It’s organised so you can start with a **Baseline** profile and then run five targeted variants that each isolate one performance dimension (**batching, compression, concurrency, durability, broker throughput**).  
After every run, you’ll capture the same metric bundle and later stitch the numbers together in **Grafana** or **Excel**.

---

## 1. How the Experiment Matrix is Structured

| Axis                    | Why it matters                                                                 | Two or three levels to sweep                                                 |
|-------------------------|--------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| **Batching**            | Bigger batches amortise per-message overhead and make compression effective   | `batch.size`: 32 kB → 256 kB ‖ `linger.ms`: 0 → 20 ms                        |
| **Compression**         | Shrinks wire + disk bytes; modern codecs keep CPU cost low                    | `compression.type`: none → lz4 → zstd                                       |
| **Concurrency / ordering** | `max.in.flight` drives parallel requests; `idempotence` guarantees ordering/dedup | `max.in.flight`: 1 vs 5 ‖ `enable.idempotence`: false vs true              |
| **Durability (acks / ISR)** | Trade latency for safety; RF = 2 needs `min.insync.replicas=1` ✔︎         | `acks`: 1 vs all                                                             |
| **Broker throughput knobs** | Threads & socket buffers decide how much traffic each node can drain       | `num.network.threads`: 3 → 6 ‖ `num.io.threads`: 8 → 16 ‖ `socket.send/receive.buffer.bytes`: 128 kB → 1 MB |

You’ll run **six scenarios** (Baseline + 5 deltas). The table below shows only the fields that change; everything else stays at the **Baseline** so causality is obvious.

| Scenario ID | Producer Overrides                                                                 | Broker Overrides                                         | What You’ll Learn                                                        |
|-------------|--------------------------------------------------------------------------------------|----------------------------------------------------------|---------------------------------------------------------------------------|
| **P0 Baseline**   | `batch.size=64k` `linger.ms=0` `compression=none` `acks=1` `max.in.flight=5`      | defaults (`num.network=3`, `num.io=8`)                   | Reference line-rate & p99 latency                                        |
| **P1 Big Batch**  | `batch.size=1MB` `linger.ms=20`                                                | —                                                        | How batching alone lifts MB/s (often ≥2×)                                |
| **P2 Compressed** | `compression=lz4` (`batch.size` back to `64k`)                                  | —                                                        | Wire + disk savings vs CPU cost                                          |
| **P3 High Concurrency** | `max.in.flight=10`                                                      | —                                                        | Throughput ceiling before ordering breaks                                |
| **P4 Durable**    | `acks=all` `enable.idempotence=true` `retries=2147483647`                       | `min.insync.replicas=1`                                  | Latency + broker CPU cost of safe writes                                 |
| **P5 Broker-scaled** | —                                                                         | `num.network=6` `num.io=16` `socket.*=1MB`               | Whether the bottleneck moves from NIC/disk to CPU                        |

*(Optional: Run a 7th scenario combining P2 + P4 for “compressed-and-durable”.)*

---

## 2. Exact Snippets to Drop in Your Property Files

### Producer Template

```properties
# common
bootstrap.servers=broker1:9092,broker2:9092,broker3:9092
buffer.memory=335544320        # 320 MB (keep ≥ 4× largest batch)
key.serializer=org.apache.kafka.common.serialization.StringSerializer
value.serializer=org.apache.kafka.common.serialization.ByteArraySerializer

# per-run overrides inserted below …
```

Reference: [Instaclustr - Kafka Performance Best Practices](https://www.instaclustr.com/education/apache-kafka/kafka-performance-7-critical-best-practices/)

---

### Broker Template Additions

```properties
# already set cluster-wide
default.replication.factor=2
min.insync.replicas=1
queued.max.requests=500        # avoid request pile-ups
replica.fetch.max.bytes=1048576
num.replica.fetchers=4         # keep followers in sync
```

References:
- [Strimzi Blog: Broker Tuning](https://strimzi.io/blog/2021/06/08/broker-tuning/)
- [Instaclustr - Kafka Performance Best Practices](https://www.instaclustr.com/education/apache-kafka/kafka-performance-7-critical-best-practices/)

Then apply the **per-scenario overrides** from the matrix above.

---

## 3. Metrics to Scrape on Every Run

| Layer     | Must-have Time-Series                                                                 |
|-----------|----------------------------------------------------------------------------------------|
| **Producer** | `record-send-rate`, `request-latency-avg/p95/p99`, `batch-size-avg`, `buffer-available-bytes`, `compression-rate-avg`, `produce-throttle-time-avg` |
| **Broker**   | `BytesInPerSec`, `ProduceLocalTimeMs`, `RequestHandlerAvgIdlePercent`, `LogFlushTimeMs`, `UnderReplicatedPartitions`, `FollowerReplicationLag`       |
| **System**   | Disk % busy, NIC Mbps, CPU steal, JVM gc.ms                                         |

Correlate **producer throttle-time spikes** with **broker ISR shrinks** / `LogFlushTime` to pinpoint the first saturated resource.

---

## 4. Run Order & Aggregation Tips

1. **Warm-up**: 5 min at Baseline to page-cache the log.  
2. Execute **P1–P5 in a round-robin loop**, 10 min each, so cluster temps stay comparable.  
3. **Export Prometheus to CSV** and pivot on `scenario_id` → build throughput-vs-latency plots.  
4. Highlight the **knee-point** where extra MB/s no longer improves because **p99 latency or CPU exceeds 80%** — that’s the story for your dissertation.

> 📌 Confluent’s open benchmark hit ~605 MB/s and 5 ms p99 on a 3-broker NVMe cluster using similar `batch`/`linger` settings — gives you a public yard-stick to compare against.

---

With these six runs, you’ll have a **clean, reproducible data set** showing exactly how each knob affects sustained high-volume ingestion — ready to analyse and explain.
