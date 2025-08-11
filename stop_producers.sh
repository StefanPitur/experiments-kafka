# stop_producers.sh
PGID=$(cat /tmp/producer.pgid)
sudo kill -- -"$PGID"
