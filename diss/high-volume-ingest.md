# Scenario Definition – Sustained High-Volume Continuous Ingest

Apache Kafka is widely adopted as the “commit-log” of modern data platforms, but the first stress point for any deployment is a steady, high-throughput ingest workload in which multiple producers push small messages as fast as hardware allows.

Several field studies show that producer/broker tuning can swing throughput by an order of magnitude and strongly affect tail-latency:

- [**Confluent’s public benchmark**](https://developer.confluent.io/learn/kafka-performance/) reaches 1 GB/s per broker only after raising `batch.size`, `linger.ms` and switching to `acks=all`.
- [**Google’s 2024 managed-Kafka benchmark**](https://cloud.google.com/blog/products/data-analytics/managed-service-for-kafka-benchmarking-and-scaling-guidance) ranks acks, batching and compression as the four most impactful knobs for high-volume ingest.
- **Academic workloads** (e.g. [Digazu’s hybrid batch/stream trace](https://dl.acm.org/doi/10.1145/3701717.3734462)) confirm that sustained ingest dominates cluster resource consumption in production lakes.
- **Numerous tuning guides and experiments** agree that producer batching (`batch.size`, `linger.ms`) and CPU-parallelism on brokers (`num.io.threads`, `num.network.threads`) form the critical path for both throughput and tail latency ([redpanda](https://www.redpanda.com/guides/kafka-performance-kafka-performance-tuning); [Confluent](https://developer.confluent.io/confluent-tutorials/optimize-producer-throughput/kafka/)).

---

## Experiment Matrix

To characterise these factors systematically we run six incremental stages (P0 – P5); each stage is **ten minutes of soak** at **maximum send rate**, with three producers and three brokers on identical `c6620` nodes. Only one dimension changes per step to preserve attribution.

| Stage            | Producer Settings                                             | Broker Settings / Topology                                      | Rationale                                                                     |
|------------------|---------------------------------------------------------------|------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **P0 (baseline)** | `acks=1`, `batch.size=16 KB`, `linger.ms=0`, no compression  | 3 brokers · RF = 2 · default threads (IO = 8 / NET = 3)          | Establish CPU-bound reference (see Section 5.2).                              |
| **P1 – Big Batch**| `batch.size=512 KB`, `linger.ms=10 ms`                       | unchanged                                                        | Measure batching effect on throughput vs. latency spikes.                     |
| **P2 – Stronger Durability** | `acks=all`, `min.insync.replicas=2`              | RF = 2 (unchanged)                                               | Observe cost of synchronous replication and URP behaviour.                    |
| **P3 – More Broker Threads** | (P2 settings)                                     | `num.io.threads=16`, `num.network.threads=8`                     | Test whether extra CPU parallelism removes handler-idle dips.                 |
| **P4 – Compression** | add `compression.type=lz4`                               | unchanged                                                        | Examine network & disk relief vs. CPU overhead.                               |
| **P5 – High Safety** | (P4 settings)                                             | RF = 3, `unclean.leader.election.enable=false`                   | Worst-case durability; quantifies replication ceiling.                        |

Each run exports:

- **Producer metrics**: `send-rate`, `request_latency_{avg,p95,p99}`, `batch size`, `compression ratio`, `error rate`.
- **Broker metrics**: `BytesInPerSec`, `ProduceTotalTimeMs_{p95,p99}`, request-handler idle %, URP & ISR churn, GC pause.
- **Host metrics (node-exporter)**: CPU %, NVMe util %, NIC Tx Gb/s, FS free %.

---

This matrix lets us isolate:

1. **Batch-size effects**
2. **Synchronous replication cost**
3. **CPU scaling**
4. **Compression trade-offs**
5. **Durability overhead**

…providing a smooth narrative from the baseline (P0) to the fully tuned configuration (P5).

The next sections present results for each stage, beginning with the P0 baseline analysed in **Section 5.2**.


## P0 - Baseline
Grafana Snapshot url: https://snapshots.raintank.io/dashboard/snapshot/e5GzwJ9nIVZbpm7hk0aLTNY0Gf8ZRABo?orgId=0

The baseline Kafka deployment—three brokers and three producers on CloudLab c6620 nodes—revealed significant performance constraints under sustained 1KB message ingestion. Key observations demonstrate a latency increase from 25 ms to 200 ms (P95) and a 14% throughput degradation (350 MB/s to 300 MB/s) within 30 minutes. These issues stemmed directly from configuration-induced resource bottlenecks, not hardware limitations.

CPU saturation (99% utilization across brokers and producers) created thread contention queues, as evidenced by near-zero idle time in request handlers. This occurred despite brokers utilizing only 8 of 28 available cores (71% idle), indicating severe thread starvation. Disk I/O imbalances exacerbated the problem, with one NVMe drive at 100% utilization while its paired drive operated below 20% capacity—a consequence of Kafka’s single log directory configuration. Network resources remained underutilized (11% of 25GbE bandwidth), confirming the bottlenecks were internal to Kafka’s processing logic.

Producer inefficiencies further constrained performance. With batch.size=64KB (≈64 messages) and linger.ms=0, excessive per-request overhead consumed CPU cycles that could otherwise sustain higher throughput. The 50-partition topic provided adequate parallelism but could not compensate for these fundamental constraints. Durability risks also emerged from min.insync.replicas=1 (RF=2), leaving the system vulnerable to data loss during broker failures.

In summary, the baseline exposes critical mismatches between Kafka’s default configuration and high-volume workloads: thread starvation wasted CPU resources, disk misconfiguration halved I/O capacity, and small batches maximized per-request overhead. These limitations establish an imperative for targeted tuning in subsequent experiments.

