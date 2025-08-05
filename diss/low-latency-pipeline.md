# Low-Latency Pipeline

Confluent link - https://www.confluent.io/blog/configure-kafka-to-minimize-latency/.


## Baseline

With a single-broker Kafka cluster (RF = 1) and two producers injecting 10 k msg s⁻¹ each, the system sustained 20 k msg s⁻¹ ingress at only 9.8 MB s⁻¹. After a 60-second warm-up the p95 producer latency stabilised at ≤ 2 ms, while the p99 held below 3 ms—well under the 25 ms target that frames the rest of this study. End-to-end latency mirrored the producer curve within +2 ms, and broker-side RequestQueueTimeMs remained at 0 ms, indicating no internal queuing. CPU utilisation on the c6620 nodes averaged 2.3 %, and NVMe busy-time peaked at 2 %, leaving ample resource head-room. Finally, no GC pause exceeded 10 ms, confirming the JVM introduced no hidden tail-latency events.

Across 12 M messages we measured an end-to-end p99 latency of 1.23 ms and a worst-case of 7.13 ms.  Values below zero caused by ≤ 2 µs clock skew were clamped to zero; their removal changed p99 by < 0.01 ms.  These results confirm that with RF = 1 and acks=1, the cluster delivers sub-2 ms tail latency—an order of magnitude beneath the 25 ms budget against which replication and batching costs are compared in subsequent phases.
