# Low-Latency Experiment Matrix — Replication Latency Scaling

Great point — let’s scale the same experiments as the cluster grows so you can isolate what replication really does to end-to-end latency.

And on your load question: 10 MB/s aggregate produce (500 B × 20k msg/s) on c6620s won’t stress bandwidth, so the latency you’ll see from replication is mostly replica fetch cadence + inter-broker RTT. With “eager” replica settings and low RTT on the same rack, the extra p50 may be small (often sub-ms to a few ms). We’ll make it visible with targeted knobs and one “accentuated” variant.

---

## The ladder (same load, bigger cluster)

Keep load constant unless the step says otherwise:
- **Load**: 500 B records, 10k msg/s per producer (2 producers → ~10 MB/s total).
- **Consumers**: consumer-perf with threads = partitions.
- **Warm-up**: ignore first 30 s; run each variant ≥5 min.

---

### Stage 0 — Control (RF=1, 1 broker)

**Purpose**: baseline with no replication.
- **Topic**: low-latency, 2 partitions, RF=1.
- **Producer (baseline)**: `acks=1`, `linger.ms=1`, `batch.size=32768`, `max.in.flight=5`, `compression=none`.
- **Consumer (baseline)**: `fetch.min.bytes=1`, `fetch.max.wait.ms=3`, `max.poll.records=200`, `enable.auto.commit=true`, `auto.commit.interval.ms=200`, `auto.offset.reset=latest`.
- **Broker**: `group.initial.rebalance.delay.ms=0`, `auto.create.topics.enable=false`.

> This is your “flat ground” for all comparisons.

---

### Stage 1 — First replication step (RF=2, 2 brokers)

**Purpose**: show acks vs replication with a minimal ISR.
- **Topic**: 2 partitions, RF=2, `min.insync.replicas=2`.
- **Exp-1A**: Producers `acks=1` (leader-only).
- **Exp-1B**: Producers `acks=all` (wait for follower fetch).
- **Exp-1C (accentuate)**: brokers raise `replica.fetch.wait.max.ms` to 50 (from a low baseline like 5–10) or raise `replica.fetch.min.bytes=65536`. Keep `acks=all`.

**What to expect**
- **1A** → lowest producer p50.
- **1B** → p50/p95 up by the follower round-trip & fetch cadence.
- **1C** → the effect becomes obvious (extra wait on follower fetch reply).

---

### Stage 2 — Full quorum (RF=3, 3 brokers)

**Purpose**: show ISR size and `min.insync.replicas` effects.
- **Topic**: 3 partitions, RF=3; run two variants:
  - **Exp-2A**: `min.insync.replicas=2`, producers `acks=all`.
  - **Exp-2B**: `min.insync.replicas=3`, producers `acks=all`.

**What to expect**
- **2B** increases sensitivity to any slow follower; p95/p99 move more than p50.
- If things look “too flat” at 10 MB/s, add 5–10 ms RTT to one follower (see Stage 3) or keep 2B and do Exp-1C-style replica fetch waits.

---

### Stage 3 — Network RTT sensitivity (RF=3)

**Purpose**: show that `acks=all` latency ≈ max follower RTT + fetch wait.
- Keep Stage-2A settings (`misr=2`, `acks=all`).
- Inject delay on one follower NIC (CloudLab):

```bash
sudo tc qdisc add dev <iface> root netem delay 5ms 1ms
# remove later with:
sudo tc qdisc del dev <iface> root
```

- Ensure that delayed broker stays in ISR for the test (don’t kill it).
- Run with and without `tc`.

**What to expect**
- Clear p95/p99 shift ≈ injected RTT when ISR includes the delayed follower.

---

### Stage 4 — Consumer fetch cadence under replication (RF=3)

**Purpose**: see consumer fetch interact with replicated produce.
- Fix Stage-2A (`acks=all`, `misr=2`).
- Vary consumers:
  - **4A**: `fetch.max.wait.ms=1`
  - **4B**: baseline `fetch.max.wait.ms=3`
  - **4C**: `fetch.max.wait.ms=10`
- Optional: set `fetch.min.bytes=65536` with `fetch.max.wait.ms=3`.

**What to expect**
- Higher `fetch.max.wait.ms` lifts E2E p50 roughly by that amount.
- Large `fetch.min.bytes` adds a “need bytes to reply” threshold → bigger jumps when per-fetch payload is small.

---

### Stage 5 — Partitions vs latency with replication (RF=3)

**Purpose**: parallelism vs overhead when leaders must wait for followers.
- Hold total load ≈ 20k msg/s constant.
- Run 1 / 3 / 6 partitions; use threads = partitions.
- Keep `acks=all`, `misr=2`.

**What to expect**
- 1 partition: best p50, worse tails (HOL blocking).
- 3: often sweetest spot.
- 6: more fetches/scheduling/GC → tails widen again.

---

## Will ~10 MB/s show replication latency meaningfully?
Yes, but mostly through cadence + RTT, not bandwidth.

At RF=3, the leader sends ~2× your produce rate to followers (≈ 20 MB/s egress) — trivial on 25/100 Gb links. So you won’t see queueing delay from line-rate; you’ll see:
- the extra round-trip before `acks=all`,
- and any waits from follower fetch batching (`replica.fetch.min.bytes`, `replica.fetch.wait.max.ms`).

If p50 looks too close to RF=1, that’s expected on fast fabric. Use Stage-1C (replica fetch waits) or Stage-3 (5–10 ms `tc` delay) to make the replication effect visible and explainable without changing your application load.

---

### One “accentuated but still sane” variant (optional)
Keep records at 500 B; bump to 20k msg/s per producer (≈ 20 MB/s produce, 40 MB/s replication egress at RF=3). Still tiny for c6620, but it:
- raises records per batch, making replica fetch min-bytes effects clearer;
- produces crisper p95/p99 gaps without saturating anything.

---

## What to log each run
- **Producer-perf**: p50/p95/p99, request latency, throttle time.
- **Consumer-perf**: nMsg/s, fetch time; records-lag-max.
- **Broker JMX**: follower fetch request/byte rates, `UnderReplicatedPartitions`, ISR expand/shrink, request queue times.
- Note exact knobs (`acks`, `misr`, `replica.fetch.*`, `tc`).

---

If you want, I’ll package this into small `run_stage{0..5}.sh` scripts plus a parser that merges all logs into a tidy CSV for plotting.
