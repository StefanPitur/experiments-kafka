# Dissertation - Comprehensive Performance Analysis of Apache Kafka

## Ideally...
This repository should keep track of all the experiment scripts for CloudLab,
all the configurations for the experiments and their results. Additionally,
I should also create READMEs for all the experiments with their graphs and results,
which ideally I should write and interpret as soon as I finish an experiment, such
that the write-up of the dissertation should become a large copy-paste job from
these files.


Of couse, we don't live in an ideal world... let's hope this will actually be done.

---

# Log of events
- I have created an image on CloudLab that is a bare-metal Ubuntu 22 with Java 17
installed and Kafka downloaded under `/opt/kafka`, such that the OS in the profiles
come with these pre-installed - `urn:publicid:IDN+utah.cloudlab.us+image+isolateedinburgh-PG0:kafka-bare-metal`.

---

# Experiments:
| Scenario (Use Case) | Key Configurations Varied (Producer / Consumer / Broker) | Test Conditions & Faults (Workload & Topology) | Metrics Collected (Producer ↔ Consumer ↔ Broker) |
|---------------------|----------------------------------------------------------|------------------------------------------------|--------------------------------------------------|
| _**1. Sustained High-Volume Ingestion**_<br/>(*Continuous heavy load*) | _**Producer:**_ acks (e.g. 1 vs all), linger.ms (0 vs 50ms), batch.size (e.g. 16KB vs 1MB), compression.type (none vs gzip).<br/>_**Consumer:**_ enable.auto.commit (on vs off), max.poll.records (e.g. 100 vs 1000).<br/>_**Broker:**_ replication.factor (1 vs 3), num.io.threads (e.g. 8 vs 16). | - Steady high throughput workload (e.g. multiple producers sending small messages continuously at max rate).<br/>- 3 Kafka brokers, 1 topic with many partitions (e.g. 50–100 partitions).<br/>- _**No fault injection**_ (baseline throughput test). | _**Producer metrics:**_ send throughput (messages/sec, MB/sec), average produce request latency, error/retry count.<br/>_**Consumer metrics:**_ consume throughput (messages/sec), end-to-end latency (produce-to-consume), consumer lag.<br/>_**Broker metrics:**_ CPU utilization, disk I/O throughput, network I/O, GC pauses, broker request latency. |
