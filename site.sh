#!/bin/bash

prog="DonantesMalagaBot.py"
pid_file="DonantesMalagaBot.pid"

start() {
    echo "Starting $prog"
    python $prog > DonantesMalagaBot.log 2>&1 &
    echo $! > $pid_file
}

stop() {
    echo "Stopping $prog"
    pid=`cat $pid_file`
    kill -9 $pid
}

status() {
    pid=`cat $pid_file`
    pids=`ps aux | grep $prog | awk '{ print $2 }'`
    for p in $pids
    do
        if [ $p == $pid ]; then
            echo "$prog is running"
            exit 0
        fi
    done
    echo "$prog is stopped"
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
       echo "Usage: $0 {start|stop|status|restart}"
esac

exit 0
