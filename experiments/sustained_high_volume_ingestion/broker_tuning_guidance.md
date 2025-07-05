
# Nuanced Guidance Before Tuning Broker-Side Parameters

Below is the nuance you need before you start sweeping those four broker-side parameters.

**Short version**: the first three knobs let you redistribute your existing CPU, RAM and kernel buffers so the broker can keep its pipelines full; only `min.insync.replicas` changes a durability/availability rule. None of them magically add hardware, but each one can unlock head-room that was there all along.

---

## What Each Setting Really Does

### `num.network.threads`

Number of threads pulling requests off the socket and pushing responses back.  
Bumping it raises the fan-in/out concurrency between the NIC and the request queue.  
As [Cloudera’s tuning guide](https://blog.cloudera.com/kafka-deep-dive-2-networking/) explains, network threads only move bytes; they do almost no disk I/O or log work.

- If you already see `RequestHandlerAvgIdlePercent` near 1.0, more threads won’t help.
- If it’s ≪ 0.3 and your CPU still has head-room, add a couple.

### `num.io.threads`

Threads that actually service Produce/Fetch requests (disk, cache, compression, replica sync).  
They are CPU-bound when messages are small or compressed and disk-bound when segment flushes dominate.  
[Redpanda’s Kafka-tuning playbook](https://docs.redpanda.com/current/deploy/deployment-guides/kafka-tuning/) stresses that boosting I/O threads mostly helps when CPU is the bottleneck, not the disk.

- **Resource story**: You’re reallocating scheduler slices across more runnable threads.
- If the box has 8 cores and you jump from 8→16 I/O threads without head-room, they’ll just context-switch harder—not faster.

### `socket.send.buffer.bytes` & `socket.receive.buffer.bytes`

JVM-side hints for the kernel’s TCP send/recv windows.  
Larger buffers keep the pipe full on high-bandwidth or long-RTT links.  
[Strimzi](https://strimzi.io/blog/2021/06/08/broker-tuning/) and several field notes recommend 256 kB–1 MB when pushing >10 Gbit/s.

- But every extra byte is heap + kernel memory.
- Crank them only if `socket-server-metrics:NetworkProcessorAvgIdlePercent` is low while CPU/disk are idle.

### `min.insync.replicas`

**Safety valve**, not a resource knob.  
It sets the minimum number of replicas that must acknowledge a write when the producer uses `acks=all`.

- If in-sync replicas drop below this number, the partition becomes read-only until they recover.
- [Confluent’s replication docs](https://docs.confluent.io/platform/current/kafka/design/replication.html) spell out that higher MISR protects against data loss but will block writes during a broker outage, cutting throughput.
- **Performance impact** shows up only when a replica lags or dies; steady-state throughput is unchanged, as [users benchmarking have observed](https://www.confluent.io/blog/kafka-fastest-messaging-system/).

---

## How the Knobs Interact

| Symptom in Grafana                                     | Likely Fix                                      |
|--------------------------------------------------------|--------------------------------------------------|
| High `RequestQueueSize`, low CPU                       | ↑ `num.network.threads`                         |
| `RequestHandlerAvgIdlePercent` ≪ 0.3, CPU < 70%        | ↑ `num.io.threads`                              |
| NIC < 50% util but producer throttle time spikes       | ↑ socket buffers                                |
| ISR keeps shrinking on spike → producer freezes        | Lower `min.insync.replicas` or add brokers/disks|

_Remember_: each thread consumes stack memory and GC overhead; each extra socket buffer consumes heap plus kernel pages. Tune gradually and observe.

---

## Practical Starting Points for Your 3-Broker Test Rig

| Parameter               | Baseline      | Stretch Goal (after profiling)           |
|-------------------------|---------------|------------------------------------------|
| `num.network.threads`   | 3 (default)    | 4 – 6 if packets queue up                |
| `num.io.threads`        | 8 (default)    | 12 – 16 if CPU idle % is low             |
| `socket.*.buffer.bytes` | 128 kB         | 512 kB – 1 MB on 10 GbE                  |
| `min.insync.replicas`   | 1 (with RF=2)  | 2 for stricter durability                |

Test one change at a time, chart **p95/p99 latency** alongside **BytesInPerSec**, and you’ll quickly see where “more threads” buys real throughput and where it just shuffles contention around.
