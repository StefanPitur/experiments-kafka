
# Kafka Producer Tuning: What Each Setting Really Does

This is a “what-it-really-does” field-guide to the **producer properties** you’ll vary in the high-volume ingestion test.  
Grouped by the **resource** they touch, so you can see which metric should move when you tweak each knob.

Producer configs reference from Confluent can be found [here](https://docs.confluent.io/platform/current/installation/configuration/producer-configs.html).

---

## Batching: Amortise Per-Message Overhead

| Property     | What it Controls                                              | Typical Sweet-Spot                                      |
|--------------|---------------------------------------------------------------|----------------------------------------------------------|
| `batch.size` | Allocated buffer per partition before the send thread ships it | 64 kB baseline → 256 kB when you want max MB/s. A buffer that large only helps if it fills; pair it with `linger.ms`. |
| `linger.ms`  | How long the sender thread waits for more records to fill the batch | 0 ms = fire-and-forget; 10–20 ms is enough to double batch hit-rate without spiking latency |
| `buffer.memory` | Total heap for all un-sent batches                        | Keep ≥ 4× the biggest `batch.size`; otherwise producers block and you’ll see `bufferpool-wait-time` climb |

**When to change it**: If `batch-size-avg` is ≪ your target size, bigger buffers or longer linger won’t help—look instead at partition count or key distribution.

---

## Compression: Trade CPU for Network / Disk

| Property            | Why it Matters                                           | Thumb-Rules                                                             |
|---------------------|----------------------------------------------------------|-------------------------------------------------------------------------|
| `compression.type`  | Shrinks payload on the wire and on disk                 | `lz4` is the usual “free speed-up”; `zstd` wins on ratio when CPU head-room exists; `gzip` is rarely worth the cost |
| `compression.level` | Tunes the CPU-vs-ratio curve (codec-specific)           | Stick with the codec default; higher levels help only for large messages |

**Watch** the producer’s `compression-rate-avg` and the broker’s `BytesInPerSec`—you should see bytes drop while msg/s stays flat.

---

## Concurrency & Ordering

| Property                           | What it Unlocks                                               | Caution Flags                                                               |
|------------------------------------|----------------------------------------------------------------|------------------------------------------------------------------------------|
| `max.in.flight.requests.per.connection` | Parallel in-flight Produce requests per TCP connection     | Values > 1 can reorder messages on retry unless idempotence is on          |
| `enable.idempotence`              | Guarantees “exactly-once per partition” and preserves order across retries | Implicitly forces `acks=all`, `retries>0`, and caps `max.in.flight` at 5   |

**Tuning tip**: Start at 5 in-flight requests; jump to 10 only if CPU is idle and p99 latency is still low.

---

## Durability & Acknowledgments

| Property              | Latency ↔ Safety Dial                                   | Practical Ranges                                               |
|-----------------------|----------------------------------------------------------|----------------------------------------------------------------|
| `acks`                | 0 = fire-and-forget, 1 = leader-only, all = leader + ISR | Use 1 when benchmarking peak throughput; use all with `min.insync.replicas=1` for safe writes |
| `min.insync.replicas` (broker) | How many replicas must ack when `acks=all`       | With RF = 2, MISR = 1 lets you lose one broker without stalling |

**Latency impact** is visible in the producer’s `request-latency-99th` and the broker’s `ProduceRemoteTimeMs`.

---

## Retry & Timeout Budget

| Property            | Role in Failure Paths                                 | Guideline                                                                 |
|---------------------|--------------------------------------------------------|---------------------------------------------------------------------------|
| `retries`           | How many times to resend on retriable errors          | 5–10 is plenty for perf tests; unlimited (`Integer.MAX_VALUE`) for durability |
| `delivery.timeout.ms` | Wall-clock budget for the whole send, including retries | Keep 30s–120s; shorter shows failures sooner                             |
| `request.timeout.ms`  | Per-attempt broker response timeout                  | Set to `delivery.timeout - 5s` so a batch doesn’t expire while retrying  |

If you see `EXPIRED_REQUEST` errors on the broker, raise `delivery.timeout.ms` or lower traffic.

---

## Memory, Payload Limits & Flow Control

| Property            | What Happens When It’s Too Low                       | Baseline → Stretch                         |
|---------------------|------------------------------------------------------|---------------------------------------------|
| `buffer.memory`     | Producer threads block; `record-queue-time-avg` soars | 128 MB → 512 MB (but watch GC)              |
| `max.request.size`  | Broker rejects large batches with `MessageTooLarge` | Keep ≥ 2× `batch.size`; 2–5 MB is typical   |

---

## Partition Selection

| Property               | Why Touch It                                           | When to Switch                                                           |
|------------------------|--------------------------------------------------------|---------------------------------------------------------------------------|
| `partitioner.class`    | Sticky (default) keeps more order; Round-Robin evens load | Use `roundrobin` if `BytesInPerSec` is hot on a subset of partitions     |
| `partitioner.ignore.keys` | Ignores key for load balancing                      | Handy when keys are skewed yet order isn’t critical                       |

---

## Putting It Together – Two Ready-Made Profiles

| Profile             | Good For                | Key Overrides                                                                                   |
|----------------------|-------------------------|--------------------------------------------------------------------------------------------------|
| **Throughput-first** | Max MB/s, best baseline | `batch.size=256k`, `linger.ms=20`, `compression.type=lz4`, `acks=1`, `enable.idempotence=false`, `max.in.flight=10`, `buffer.memory=256m` |
| **Durable-and-ordered** | Production-grade safety | `compression.type=zstd`, `acks=all`, `enable.idempotence=true`, `retries=2147483647`, `max.in.flight=5`, `batch.size=128k`, `linger.ms=10`, `buffer.memory=512m` |

Run each for 10 min, collect the same metric bundle, and you’ll have a clean narrative showing how batching, compression, concurrency and durability reshape throughput, latency and resource use.

---

## Key Takeaway

Producer configs don’t “add hardware”; they re-allocate CPU, heap, and socket buffers or tighten the guarantees the brokers must meet.  
**Watch how each change moves producer throttle time, broker remote-time, and system CPU/disk.**  
That feedback loop is where the dissertation story lives.
