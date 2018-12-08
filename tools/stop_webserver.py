"""
This script will find the flask process running the application and kill the process.
The purpose is to allow an offline dump of the database for backup purposes
"""

import logging
import psutil
from lib import my_env

cfg = my_env.init_env("wolse", __file__)
cmd = cfg["Process"]["cmd"]
script = cfg["Process"]["script"]
for process in psutil.process_iter():
    cmdlist = process.cmdline()
    if (len(cmdlist) > 1) and (cmd in cmdlist[0]) and (script in cmdlist[1]):
        process.terminate()
        logging.info("Found and stopped process {script} in command {cmdlist}".format(script=script, cmdlist=cmdlist))
logging.info("End Application")
