# stop_consumers.sh
PGID=$(cat /tmp/consumer.pgid)
sudo kill -- -"$PGID"
sudo rm cons-"$PGID"*
sudo rm /tmp/cons-"$PGID"*
