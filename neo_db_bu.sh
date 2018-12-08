#!/usr/bin/env bash
HOME=/home/dirk/wolse
source /opt/envs/flrun/bin/activate
python3 $HOME/tools/neo_action.py -a stop
python3 $HOME/tools/stop_webserver.py
python3 $HOME/tools/neo_bu.py
python3 $HOME/tools/neo_action.py -a start
sleep 60
python3 $HOME/wolse.py &