#!/usr/bin/env bash
set -e

export KAFKA_HEAP_OPTS="-Xms512m -Xmx512m"

sudo rm /tmp/producer.pgid

# Launch eight producers in a single process group
setsid bash -m <<'EOF' &               # the trailing & returns control to your shell
for i in {1..20}; do
  # For producers 2-20, clear any per-JVM extra options
  if [ "$i" -ne 1 ]; then
      unset KAFKA_OPTS
  fi

  nohup ~/kafka/bin/kafka-producer-perf-test.sh \
        --topic high-volume \
        --num-records 200000000000 \
        --record-size 1000 \
        --throughput -1 \
        --producer.config /experiments/high_volume_ingest/p0/producer.properties \
        --csv-path prod-$$-$i.csv \
        >  /tmp/prod-$$-$i.log 2>&1 &
done

echo $$ > /tmp/producer.pgid          # save the process-group ID
EOF

export KAFKA_OPTS="-javaagent:/users/pitur/kafka/jmx_prometheus_javaagent.jar=7071:/users/pitur/kafka/kafka-jmx.yml"
