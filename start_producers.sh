#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 NUM_PRODUCERS PRODUCER_CONFIG_PATH"
  echo "  NUM_PRODUCERS: positive integer"
  echo "  PRODUCER_CONFIG_PATH: path to producer.properties"
}

# Check we received exactly two args
if [[ $# -ne 2 ]]; then
  usage
  exit 1
fi

NUM="$1"
CONFIG_PATH="$2"

# Validate NUM
if [[ ! "$NUM" =~ ^[1-9][0-9]*$ ]]; then
  echo "Error: NUM_PRODUCERS must be a positive integer."
  usage
  exit 1
fi

# Optionally validate config path exists
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Error: Config file not found: $CONFIG_PATH"
  exit 1
fi

export KAFKA_HEAP_OPTS="-Xms512m -Xmx512m"
sudo rm -f /tmp/producer.pgid
export NUM_PRODUCERS="$NUM"

setsid bash -m <<'EOF' &
for i in $(seq 1 "$NUM_PRODUCERS"); do
  # Calculate port for JMX agent
  port=$((7000 + i))
  export KAFKA_OPTS="-javaagent:/users/pitur/kafka/jmx_prometheus_javaagent.jar=${port}:/users/pitur/kafka/kafka-jmx.yml"

  nohup ~/kafka/bin/kafka-producer-perf-test.sh \
    --topic high-volume \
    --num-records 200000000000 \
    --record-size 1000 \
    --throughput -1 \
    --producer.config "$CONFIG_PATH" \
    --csv-path "prod-$$-$i.csv" \
    > "/tmp/prod-$$-$i.log" 2>&1 &
done

echo $$ > /tmp/producer.pgid
EOF

# Set JMX agent for anything started *after* this script finishes
export KAFKA_OPTS="-javaagent:/users/pitur/kafka/jmx_prometheus_javaagent.jar=7071:/users/pitur/kafka/kafka-jmx.yml"
