#!/usr/bin/env bash
set -euo pipefail

PROM_HOST="localhost"
PROM_PORT="9090"

RESP=$(curl -s -XPOST http://${PROM_HOST}:${PROM_PORT}/api/v1/admin/tsdb/snapshot)
echo $RESP
