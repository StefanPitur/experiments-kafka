# stop_producers.sh
PGID=$(cat /tmp/producer.pgid)
sudo kill -- -"$PGID"
sudo rm prod-"$PGID"*
sudo rm /tmp/prod-"$PGID"*
