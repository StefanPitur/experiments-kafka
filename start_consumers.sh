#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 NUM_CONSUMERS CONSUMER_CONFIG_PATH"
  echo "  NUM_CONSUMERS: positive integer"
  echo "  CONSUMER_CONFIG_PATH: path to producer.properties"
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
  echo "Error: NUM_CONSUMERS must be a positive integer."
  usage
  exit 1
fi

# Optionally validate config path exists
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "Error: Config file not found: $CONFIG_PATH"
  exit 1
fi

export KAFKA_HEAP_OPTS="-Xms1g -Xmx1g"
sudo rm -f /tmp/consumer.pgid
export NUM_CONSUMERS="$NUM"
export CONFIG_PATH="$CONFIG_PATH"

setsid bash -m <<'EOF' &
for i in $(seq 1 "$NUM_CONSUMERS"); do
  # Calculate port for JMX agent
  port=$((8000 + i))
  export KAFKA_OPTS="-javaagent:/users/pitur/kafka/jmx_prometheus_javaagent.jar=${port}:/users/pitur/kafka/kafka-jmx.yml"

  nohup ~/kafka/bin/kafka-consumer-perf-test.sh \
    --bootstrap-server 192.168.0.101:9092 \
    --topic low-latency \
    --timeout 10000 \
    --messages 6000000 \
    --consumer.config "$CONFIG_PATH" \
    --group lat-test \
    --e2e-csv-path "cons-$$-$i.csv" \
    --show-detailed-stats \
    --print-metrics \
    > "/tmp/cons-$$-$i.log" 2>&1 &
done

echo $$ > /tmp/consumer.pgid
EOF

# Set JMX agent for anything started *after* this script finishes
export KAFKA_OPTS="-javaagent:/users/pitur/kafka/jmx_prometheus_javaagent.jar=7071:/users/pitur/kafka/kafka-jmx.yml"
