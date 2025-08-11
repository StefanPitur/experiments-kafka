# stop_consumers.sh
PGID=$(cat /tmp/consumer.pgid)
sudo kill -- -"$PGID"
