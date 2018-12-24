#!/bin/sh
# this script is used to boot a Docker container
source zolse/bin/activate
sleep 20
# flask run
exec gunicorn -b :5000 --access-logfile - --error-logfile - fromflask:app